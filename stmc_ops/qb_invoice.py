"""
Draw completion → QuickBooks invoice pipeline.

Called from `_mark_draw_complete` (views.py) after a draw is marked paid.
Creates a real QB Invoice against the homeowner (Option A: progress invoicing),
records a `QbInvoiceEvent` row for the owner's notification bell, and returns
that row so the caller can attach its details to the HTMX response header.

Design principles
-----------------
* **Never break the demo.** Every QB API call is wrapped. If we can't reach QB
  (no connection, token expired, network error, sandbox down, unexpected
  response), we still record a `QbInvoiceEvent` with `status=STATUS_FAILED` so
  the manager-side toast and the owner bell still populate — the row just
  won't have a clickable QB link.
* **No duplicate customers.** `QbCustomerMap` caches the QB Customer.Id per
  Job, so draw #2/#3/... on the same contract hit the existing customer
  instead of creating new ones.
* **Idempotency is NOT required.** Each draw completion creates one invoice.
  The ops team won't mark the same draw complete twice in the demo flow; if
  they do, a duplicate invoice is acceptable (easy to void in sandbox).
* **DocNumber is left to QB.** QB auto-increments invoice numbers per company.
  We read `Invoice.DocNumber` from the response and surface that in the UI.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from .models import Job, JobDraw, QbCustomerMap, QbInvoiceEvent
from . import qb_client

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# DRAW → HUMAN-READABLE PHASE LABEL
# ─────────────────────────────────────────────────────────────
# We surface a concise phase name in the toast/bell (e.g. "Concrete
# Completion") rather than the raw `draw.label` ("2nd Home Draw (Concrete
# Completion)"). The transformation is purely text-based — we derive the
# label from draw.label itself, *not* from draw_number. An earlier version
# of this function mapped draw_number → label, which produced wrong text
# whenever the seed data used draw numbers outside the 0-6 range it
# assumed. Parsing draw.label is always correct regardless of numbering.


import re as _re


def _phase_label_for(draw: JobDraw) -> str:
    """Concise phase label for a draw, derived from draw.label.

    Heuristics (tried in order):
      1. If the label has a parenthetical — "3rd Home Draw (Framing
         Completion)" — return the text inside: "Framing Completion".
         This matches how the seeded contracts name draws.
      2. Otherwise strip any ordinal prefix ("1st ", "2nd ", "3rd ", "4th "…)
         and the phrase "Home Draw" from the start — falls back cleanly
         for simpler labels.
      3. If none of the above apply, use the full draw.label as-is.
      4. Last-resort fallback: "Draw #N" using draw_number.
    """
    label = (draw.label or "").strip()
    if not label:
        return f"Draw #{draw.draw_number}"

    # (1) Extract text inside the last pair of parens, if any.
    paren_match = _re.search(r"\(([^()]+)\)\s*$", label)
    if paren_match:
        return paren_match.group(1).strip()

    # (2) Strip ordinal prefix + any leading punctuation/separator. Labels
    # in the wild include en-dashes, em-dashes, colons, hyphens, bullets,
    # and occasionally UTF-8 mojibake where a dash got corrupted — strip
    # everything until we hit an alphanumeric character.
    cleaned = _re.sub(r"^\d+(st|nd|rd|th)\b", "", label, flags=_re.IGNORECASE)
    cleaned = _re.sub(r"^[^\w(]+", "", cleaned)  # drop leading non-word garbage
    cleaned = _re.sub(r"^home\s+draw\b", "", cleaned, flags=_re.IGNORECASE)
    cleaned = _re.sub(r"^[^\w(]+", "", cleaned)  # strip again after "Home Draw"
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned

    # (3) / (4) Fallbacks.
    return label or f"Draw #{draw.draw_number}"


# ─────────────────────────────────────────────────────────────
# CUSTOMER SYNC
# ─────────────────────────────────────────────────────────────


def _ensure_qb_customer(qb, job: Job, connection) -> str:
    """Return the QB Customer.Id for `job`, creating the customer if needed.

    Cache hit: QbCustomerMap row exists and matches the current realm.
    Cache miss or stale realm: create a new QB Customer, update the cache.
    """
    from quickbooks.objects.customer import Customer

    # Cache hit — but verify realm to avoid serving a stale ID if the QB
    # company connection has been changed since the map was written.
    try:
        cached = job.qb_customer_map
    except QbCustomerMap.DoesNotExist:
        cached = None
    if cached and cached.realm_id == connection.realm_id and cached.qb_customer_id:
        return cached.qb_customer_id

    display_name = _customer_display_name(job)

    # Double-check QB side: sandbox reloads / manual deletes can leave our
    # cache pointing at a customer that still exists only in our DB. If a
    # customer with this DisplayName already exists in QB, reuse it.
    existing = Customer.query(
        f"SELECT Id, DisplayName FROM Customer WHERE DisplayName = '{_escape(display_name)}' MAXRESULTS 1",
        qb=qb,
    )
    if existing:
        customer = existing[0]
    else:
        customer = Customer()
        customer.DisplayName = display_name
        customer.CompanyName = job.customer_name or display_name
        # Billing address — only set if we have something useful.
        # python-quickbooks exposes the address class as `Address` (not
        # `PhysicalAddress`) on the base module.
        if job.customer_addr:
            from quickbooks.objects.base import Address
            addr = Address()
            addr.Line1 = job.customer_addr[:500]
            customer.BillAddr = addr
        customer = customer.save(qb=qb)

    # Upsert the cache.
    QbCustomerMap.objects.update_or_create(
        job=job,
        defaults={
            "qb_customer_id": str(customer.Id),
            "realm_id": connection.realm_id,
        },
    )
    return str(customer.Id)


def _customer_display_name(job: Job) -> str:
    """QB DisplayName must be unique per company. Combine customer name +
    order number so two jobs for "John Smith" don't collide."""
    base = (job.customer_name or "Unnamed Customer").strip()
    if job.order_number:
        return f"{base} (#{job.order_number})"
    return f"{base} (Job {job.pk})"


def _escape(s: str) -> str:
    """Escape single quotes for QB's SQL-ish query language."""
    return (s or "").replace("'", "\\'")


# ─────────────────────────────────────────────────────────────
# DEFAULT SERVICE ITEM
# ─────────────────────────────────────────────────────────────


def _default_service_item_id(qb) -> str:
    """Every QB invoice line must reference an Item. We don't care which
    one — sandbox companies ship with generic items like "Services". Grab
    the first Service-type item; if none exists, create "STMC Draw"."""
    from quickbooks.objects.item import Item

    items = Item.query("SELECT Id, Name, Type FROM Item WHERE Type = 'Service' MAXRESULTS 1", qb=qb)
    if items:
        return str(items[0].Id)

    # No service items — fall back to creating one.
    # The item needs an IncomeAccount; we grab the first Income-type Account.
    from quickbooks.objects.account import Account
    accounts = Account.query(
        "SELECT Id, Name FROM Account WHERE AccountType = 'Income' MAXRESULTS 1",
        qb=qb,
    )
    if not accounts:
        raise QbInvoiceError("No Income account in QB — cannot create a default service item.")

    new_item = Item()
    new_item.Name = "STMC Draw"
    new_item.Type = "Service"
    from quickbooks.objects.base import Ref
    income_ref = Ref()
    income_ref.value = str(accounts[0].Id)
    income_ref.name = accounts[0].Name
    new_item.IncomeAccountRef = income_ref
    new_item = new_item.save(qb=qb)
    return str(new_item.Id)


# ─────────────────────────────────────────────────────────────
# INVOICE CREATION
# ─────────────────────────────────────────────────────────────


class QbInvoiceError(Exception):
    """Raised for any unexpected state in the invoice-creation pipeline.
    Callers should catch this (plus qb_client.QbNotConnected) to trigger
    the local-fallback path."""


def _create_invoice_in_qb(qb, customer_id: str, item_id: str, draw: JobDraw, job: Job):
    """Build and POST the QB Invoice. Returns the saved Invoice object."""
    from quickbooks.objects.invoice import Invoice
    from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
    from quickbooks.objects.base import Ref

    invoice = Invoice()

    customer_ref = Ref()
    customer_ref.value = customer_id
    invoice.CustomerRef = customer_ref

    line = SalesItemLine()
    line.Amount = float(draw.amount or 0)
    line.Description = f"{_phase_label_for(draw)} draw — {job.customer_name or 'STMC project'}"
    line.DetailType = "SalesItemLineDetail"
    detail = SalesItemLineDetail()
    item_ref = Ref()
    item_ref.value = item_id
    detail.ItemRef = item_ref
    detail.Qty = 1
    detail.UnitPrice = float(draw.amount or 0)
    line.SalesItemLineDetail = detail
    invoice.Line.append(line)

    # Private memo for QB users — surfaces the internal draw ID for support.
    invoice.PrivateNote = f"STMC job {job.pk}, draw {draw.draw_number} ({draw.label})"

    return invoice.save(qb=qb)


# ─────────────────────────────────────────────────────────────
# TOP-LEVEL ORCHESTRATION
# ─────────────────────────────────────────────────────────────


def send_invoice_for_draw(job: Job, draw: JobDraw) -> QbInvoiceEvent:
    """Create a QB invoice for `draw` against `job`'s homeowner, record a
    `QbInvoiceEvent`, and return it.

    Always returns a `QbInvoiceEvent` — never raises. QB failures are caught
    and stored on the event (`status=STATUS_FAILED`, `error_message=...`) so
    the manager-side toast and owner bell keep working even in offline mode.
    """
    phase_label = _phase_label_for(draw)
    amount = Decimal(draw.amount or 0)

    # Fast path: no connection configured at all. Record fallback and bail.
    connection = qb_client.get_connection()
    if connection is None:
        return _record_fallback_event(
            job, draw, phase_label, amount,
            "QuickBooks is not connected. Reconnect via the owner dashboard.",
        )

    try:
        with qb_client.with_qb_client() as qb:
            customer_id = _ensure_qb_customer(qb, job, connection)
            item_id = _default_service_item_id(qb)
            saved_invoice = _create_invoice_in_qb(qb, customer_id, item_id, draw, job)

            # Reload connection in case the context manager rotated tokens and
            # we need a fresh row for invoice_public_url.
            connection = qb_client.get_connection() or connection

            return QbInvoiceEvent.objects.create(
                job=job,
                draw=draw,
                team_name=phase_label,
                amount=amount,
                qb_invoice_id=str(saved_invoice.Id),
                qb_invoice_doc_number=str(getattr(saved_invoice, "DocNumber", "") or ""),
                qb_invoice_url=qb_client.invoice_public_url(connection, str(saved_invoice.Id)),
                status=QbInvoiceEvent.STATUS_SENT,
            )

    except qb_client.QbNotConnected as exc:
        logger.warning("QB not connected during invoice send: %s", exc)
        return _record_fallback_event(job, draw, phase_label, amount, str(exc))

    except Exception as exc:  # noqa: BLE001 — deliberate broad catch
        # This is the safety net. Any API error, network glitch, schema
        # surprise from QB, or sandbox hiccup lands here. We log and record
        # a fallback event so the demo keeps flowing.
        logger.exception("QB invoice creation failed for job=%s draw=%s", job.pk, draw.pk)
        return _record_fallback_event(
            job, draw, phase_label, amount,
            f"{type(exc).__name__}: {exc}",
        )


def _record_fallback_event(
    job: Job,
    draw: JobDraw,
    phase_label: str,
    amount: Decimal,
    error_message: str,
) -> QbInvoiceEvent:
    """Write a QbInvoiceEvent row without any QB-side identifiers."""
    return QbInvoiceEvent.objects.create(
        job=job,
        draw=draw,
        team_name=phase_label,
        amount=amount,
        qb_invoice_id="",
        qb_invoice_doc_number="",
        qb_invoice_url="",
        status=QbInvoiceEvent.STATUS_FAILED,
        error_message=error_message[:500],
    )
