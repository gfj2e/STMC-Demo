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

from .models import Job, JobDraw, QbCustomerMap, QbInvoiceEvent, QbItemMap
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


def _create_invoice_in_qb(qb, customer_id: str, fallback_item_id: str, draw: JobDraw, job: Job):
    """Build and POST the QB Invoice. Returns the saved Invoice object.

    Strategy:
      * If the Job has trade-budget rows AND every trade has a `QbItemMap`
        cache entry, emit one `SalesItemLine` per trade, pro-rated to the
        draw amount via each trade's share of the total budget. This gives
        QB's P&L by Item a per-trade revenue split.
      * Otherwise (legacy contract, missing seed): fall back to the
        original single-line behavior using `fallback_item_id` so the
        demo never breaks.
    """
    from quickbooks.objects.invoice import Invoice
    from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
    from quickbooks.objects.base import Ref

    invoice = Invoice()

    customer_ref = Ref()
    customer_ref.value = customer_id
    invoice.CustomerRef = customer_ref

    draw_amount = float(draw.amount or 0)
    phase_label = _phase_label_for(draw)
    description_base = f"{phase_label} draw -- {job.customer_name or 'STMC project'}"

    # Try the multi-line path first.
    multi_lines = _build_multiline_sales_items(job, draw_amount, phase_label, description_base)
    if multi_lines:
        for ln in multi_lines:
            invoice.Line.append(ln)
    else:
        # Fallback: original single-line behavior.
        line = SalesItemLine()
        line.Amount = draw_amount
        line.Description = description_base
        line.DetailType = "SalesItemLineDetail"
        detail = SalesItemLineDetail()
        item_ref = Ref()
        item_ref.value = fallback_item_id
        detail.ItemRef = item_ref
        detail.Qty = 1
        detail.UnitPrice = draw_amount
        line.SalesItemLineDetail = detail
        invoice.Line.append(line)

    invoice.PrivateNote = f"STMC job {job.pk}, draw {draw.draw_number} ({draw.label})"

    return invoice.save(qb=qb)


def _build_multiline_sales_items(job: Job, draw_amount: float, phase_label: str, description_base: str):
    """Pro-rate the draw amount across the job's trade budgets, emitting one
    SalesItemLine per trade with the matching ItemRef from QbItemMap.

    Returns a list of SalesItemLine objects, or `[]` if multi-line emission
    isn't possible (no trade rows, or any trade lacks a cached Item map).
    Returning `[]` triggers the single-line fallback in the caller — keeps
    the demo flowing for legacy contracts.
    """
    from quickbooks.objects.detailline import SalesItemLine, SalesItemLineDetail
    from quickbooks.objects.base import Ref

    trade_rows = list(job.demo_trade_budgets.all().order_by("sort_order", "trade_name"))
    if not trade_rows:
        return []

    total_budget = sum(float(tb.budgeted or 0) for tb in trade_rows)
    if total_budget <= 0:
        return []

    # Resolve every trade to a QbItemMap row up front. If any are missing,
    # bail to single-line fallback rather than emit a partial invoice.
    item_map = {m.trade_name: m for m in QbItemMap.objects.filter(
        trade_name__in=[tb.trade_name for tb in trade_rows]
    )}
    if any(tb.trade_name not in item_map for tb in trade_rows):
        logger.warning(
            "QbItemMap missing entries for job=%s trades=%s -- run `python manage.py qb_seed_sandbox` "
            "to seed Items. Falling back to single-line invoice.",
            job.pk, [tb.trade_name for tb in trade_rows if tb.trade_name not in item_map],
        )
        return []

    # Pro-rate via cents to avoid float drift; absorb the rounding remainder
    # into the largest line so the lines sum exactly to draw_amount.
    draw_cents = round(draw_amount * 100)
    raw_cents = []
    for tb in trade_rows:
        share = float(tb.budgeted or 0) / total_budget
        raw_cents.append(round(draw_cents * share))
    diff = draw_cents - sum(raw_cents)
    if diff != 0 and raw_cents:
        # Push the remainder onto the largest line.
        largest_idx = max(range(len(raw_cents)), key=lambda i: raw_cents[i])
        raw_cents[largest_idx] += diff

    lines = []
    for tb, cents in zip(trade_rows, raw_cents):
        if cents <= 0:
            continue
        amt = cents / 100.0
        ln = SalesItemLine()
        ln.Amount = amt
        ln.Description = f"{description_base} -- {tb.trade_name}"
        ln.DetailType = "SalesItemLineDetail"
        detail = SalesItemLineDetail()
        item_ref = Ref()
        item_ref.value = item_map[tb.trade_name].qb_item_id
        item_ref.name = tb.trade_name
        detail.ItemRef = item_ref
        detail.Qty = 1
        detail.UnitPrice = amt
        ln.SalesItemLineDetail = detail
        lines.append(ln)

    return lines


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


# ─────────────────────────────────────────────────────────────
# PHASE 4 — DRAW SCHEDULE LIFECYCLE (3-state)
# ─────────────────────────────────────────────────────────────
#
# Replaces the per-draw-at-mark-complete invoice push with a 3-state
# flow that matches how a construction draw schedule actually works:
#
#   1) push_draw_schedule_for_job(job)
#      Called when the sales rep clicks "Send to DocuSign" or "Send to
#      Interior Contracts" (which closes the loan on the sales-rep side).
#      Bulk-creates ONE QB Invoice per draw with DueDate set far in the
#      future ("not yet due"). For draws that are ALREADY locally PAID
#      at finalize time (deposit + loan close), also POSTs a Payment
#      that closes Balance to 0 -- keeps QB in sync with our state.
#
#   2) mark_invoice_due_for_draw(job, draw)
#      Called when the PM marks a draw complete. Updates the existing
#      QB Invoice's DueDate to today ("now due to be paid"). Stamps
#      QbInvoiceEvent.qb_due_marked_at. JobDraw flips to STATUS_INVOICED
#      (not PAID) -- the PAID transition flows from QB pull, not here.
#
#   3) qb_pull.refresh_draw_invoices_for_job(qb, job)
#      Polls QB for INVOICED draws' invoice Balance. When Balance hits
#      0 (accountant recorded a Payment in QB), flips local JobDraw to
#      PAID + sets paid_date + stamps QbInvoiceEvent.paid_at. This is
#      the only path that sets PAID -- "marked paid on the software"
#      always means "QB confirmed Balance == 0".


def push_draw_schedule_for_job(job: Job) -> dict:
    """Bulk-create QB Invoices for every draw on `job` that doesn't already
    have a successful QbInvoiceEvent.

    - Newly created Invoices get `DueDate = TxnDate + 365 days` so they
      sit as Open-but-not-yet-due in QB.
    - For draws that are already locally PAID at the time of finalize
      (deposit + loan close, set in `sales_finalize_contract_view`), this
      function ALSO posts a QB Payment closing the just-created Invoice's
      Balance to 0. Keeps QB and the local state in sync from day 1.
    - Idempotent: re-runs skip draws that already have a SENT event.

    Returns `{created, skipped, failed, paid_synced}` for callers to log.
    Never raises -- failures land as fallback QbInvoiceEvent rows.
    """
    counts = {"created": 0, "skipped": 0, "failed": 0, "paid_synced": 0}

    connection = qb_client.get_connection()
    if connection is None:
        # Whole-job offline fallback: write FAILED events for unsent draws
        # so the PM-side mark-complete flow has something to find later.
        for draw in job.demo_draws.all().order_by("draw_number"):
            already_sent = QbInvoiceEvent.objects.filter(
                job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT,
            ).exists()
            if already_sent:
                counts["skipped"] += 1
                continue
            _record_fallback_event(
                job, draw, _phase_label_for(draw), Decimal(draw.amount or 0),
                "QuickBooks not connected at finalize.",
            )
            counts["failed"] += 1
        return counts

    try:
        with qb_client.with_qb_client() as qb:
            customer_id = _ensure_qb_customer(qb, job, connection)
            item_id = _default_service_item_id(qb)
            for draw in job.demo_draws.all().order_by("draw_number"):
                already_sent_event = QbInvoiceEvent.objects.filter(
                    job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT,
                ).order_by("-created_at").first()
                if already_sent_event:
                    counts["skipped"] += 1
                    # Even on a re-finalize, if the draw is now locally PAID
                    # but the existing event has no Payment recorded yet,
                    # post one so QB matches our state.
                    if (draw.status == JobDraw.STATUS_PAID
                            and not already_sent_event.paid_at
                            and already_sent_event.qb_invoice_id):
                        try:
                            _record_qb_payment(
                                qb, customer_id, already_sent_event.qb_invoice_id,
                                float(already_sent_event.amount), already_sent_event.team_name,
                            )
                            already_sent_event.paid_at = timezone.now()
                            already_sent_event.save(update_fields=["paid_at"])
                            counts["paid_synced"] += 1
                        except Exception:  # noqa: BLE001
                            logger.exception(
                                "push_draw_schedule_for_job: re-sync Payment failed for event %s",
                                already_sent_event.pk,
                            )
                    continue

                phase_label = _phase_label_for(draw)
                amount = Decimal(draw.amount or 0)
                try:
                    saved = _create_invoice_in_qb(qb, customer_id, item_id, draw, job)
                    # Push the DueDate 365 days out so the invoice reads
                    # "not yet due" in QB until the PM marks the draw
                    # complete (which calls mark_invoice_due_for_draw to
                    # bring DueDate forward to today).
                    try:
                        _set_invoice_due_date_in_qb(qb, saved, days_from_today=365)
                    except Exception:  # noqa: BLE001
                        # If QB rejects the DueDate update, leave whatever
                        # default it picked. The lifecycle still works via
                        # paid_at stamps; DueDate is a UI nicety.
                        logger.warning(
                            "push_draw_schedule_for_job: could not set DueDate "
                            "on invoice %s -- continuing.", getattr(saved, "Id", "?"),
                        )

                    event = QbInvoiceEvent.objects.create(
                        job=job,
                        draw=draw,
                        team_name=phase_label,
                        amount=amount,
                        qb_invoice_id=str(saved.Id),
                        qb_invoice_doc_number=str(getattr(saved, "DocNumber", "") or ""),
                        qb_invoice_url=qb_client.invoice_public_url(connection, str(saved.Id)),
                        status=QbInvoiceEvent.STATUS_SENT,
                    )
                    counts["created"] += 1

                    # If this draw is ALREADY locally PAID at finalize
                    # (deposit + loan close), close out its Invoice in QB
                    # immediately so QB matches our state.
                    if draw.status == JobDraw.STATUS_PAID:
                        try:
                            _record_qb_payment(
                                qb, customer_id, str(saved.Id),
                                float(amount), phase_label,
                            )
                            event.paid_at = timezone.now()
                            event.save(update_fields=["paid_at"])
                            counts["paid_synced"] += 1
                        except Exception:  # noqa: BLE001
                            logger.exception(
                                "push_draw_schedule_for_job: Payment for "
                                "pre-paid draw %s failed", draw.pk,
                            )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "push_draw_schedule_for_job: per-draw failure job=%s draw=%s",
                        job.pk, draw.pk,
                    )
                    _record_fallback_event(
                        job, draw, phase_label, amount,
                        f"{type(exc).__name__}: {exc}",
                    )
                    counts["failed"] += 1
    except qb_client.QbNotConnected as exc:
        logger.warning("push_draw_schedule_for_job: QB not connected: %s", exc)
        # Fallthrough -- caller already has best-effort behavior. Don't
        # double-record events for draws we never reached.

    return counts


def mark_invoice_due_for_draw(job: Job, draw: JobDraw) -> QbInvoiceEvent:
    """Update the QB Invoice's DueDate to today and stamp `qb_due_marked_at`.

    Called from `_mark_draw_complete` when the PM clicks Mark Complete.
    Always returns a QbInvoiceEvent (so the HTMX header logic keeps
    working). Never raises. Falls back to `send_invoice_for_draw` if no
    SENT event exists for this draw -- e.g. PM marks complete after an
    offline finalize.
    """
    phase_label = _phase_label_for(draw)
    amount = Decimal(draw.amount or 0)

    event = (
        QbInvoiceEvent.objects
        .filter(job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT)
        .order_by("-created_at")
        .first()
    )

    # No live invoice in QB for this draw. Most likely the job was finalized
    # before Phase 4 was wired up (no bulk push at sales-finalize time).
    # Self-heal: bulk-push the WHOLE draw schedule for the job so the very
    # next mark-complete click on this job hits the fast path. Then re-look
    # up the event for THIS draw and continue.
    if event is None or not event.qb_invoice_id:
        push_draw_schedule_for_job(job)
        event = (
            QbInvoiceEvent.objects
            .filter(job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT)
            .order_by("-created_at")
            .first()
        )
        if event is None or not event.qb_invoice_id:
            # Bulk push failed (offline, etc.). Fall back to legacy
            # single-shot create for this one draw -- demo never breaks.
            return send_invoice_for_draw(job, draw)

    # Idempotent: already marked due, no-op.
    if event.qb_due_marked_at:
        return event

    connection = qb_client.get_connection()
    if connection is None:
        # Can't reach QB to update DueDate; the local INVOICED status
        # set in _mark_draw_complete is enough for the demo to advance.
        # Next online refresh / retry can stamp this.
        logger.warning(
            "mark_invoice_due_for_draw: QB offline; invoice %s not updated.",
            event.qb_invoice_id,
        )
        return event

    try:
        with qb_client.with_qb_client() as qb:
            invoice = _fetch_invoice(qb, event.qb_invoice_id)
            if invoice is not None:
                _set_invoice_due_date_in_qb(qb, invoice, days_from_today=0)
            event.qb_due_marked_at = timezone.now()
            event.save(update_fields=["qb_due_marked_at"])
            return event
    except qb_client.QbNotConnected as exc:
        logger.warning("mark_invoice_due_for_draw: QB not connected: %s", exc)
        return event
    except Exception as exc:  # noqa: BLE001
        # Never break the PM's mark-complete on a QB hiccup. The local
        # INVOICED status carries the demo forward; next refresh can retry.
        logger.exception(
            "mark_invoice_due_for_draw failed for job=%s draw=%s invoice=%s",
            job.pk, draw.pk, event.qb_invoice_id,
        )
        return event


def _record_qb_payment(qb, customer_id: str, qb_invoice_id: str, amount: float, memo: str):
    """Build and POST a QB Payment that links to one Invoice and zeros its
    Balance. Returns the saved Payment object. Raises on any QB error --
    caller wraps in try/except per the never-raise contract.

    Note on imports: in python-quickbooks, `PaymentLine` lives in
    `quickbooks.objects.payment` (NOT `quickbooks.objects.detailline`),
    and `LinkedTxn` lives in `quickbooks.objects.base`. Don't move them.
    """
    from quickbooks.objects.payment import Payment, PaymentLine
    from quickbooks.objects.base import Ref, LinkedTxn

    payment = Payment()
    customer_ref = Ref()
    customer_ref.value = customer_id
    payment.CustomerRef = customer_ref
    payment.TotalAmt = amount

    line = PaymentLine()
    line.Amount = amount
    linked = LinkedTxn()
    linked.TxnId = qb_invoice_id
    linked.TxnType = "Invoice"
    line.LinkedTxn = [linked]
    payment.Line = [line]

    payment.PrivateNote = f"STMC draw payment -- {memo}"
    return payment.save(qb=qb)


def _fetch_invoice(qb, qb_invoice_id: str):
    """Read-only fetch of one Invoice by Id. Returns None if not found.
    Used by mark_invoice_due_for_draw to mutate-and-save."""
    from quickbooks.objects.invoice import Invoice
    try:
        return Invoice.get(int(qb_invoice_id), qb=qb)
    except Exception:  # noqa: BLE001
        # Some sandboxes return strings; some require ints. If the lookup
        # fails for any reason, skip the DueDate update.
        try:
            results = Invoice.query(
                f"SELECT * FROM Invoice WHERE Id = '{qb_invoice_id}'", qb=qb,
            )
            return results[0] if results else None
        except Exception:  # noqa: BLE001
            return None


def _set_invoice_due_date_in_qb(qb, invoice, days_from_today: int):
    """Mutate an Invoice's DueDate to `today + days_from_today` and save.

    days_from_today=0 means "due now" (PM mark-complete).
    days_from_today=365 means "not yet due" (push at finalize).
    """
    from datetime import timedelta
    target = (timezone.localdate() + timedelta(days=days_from_today)).isoformat()
    invoice.DueDate = target
    invoice.save(qb=qb)


# ─────────────────────────────────────────────────────────────
# EAGER CUSTOMER PUSH (for Phase 2 demo flow)
# ─────────────────────────────────────────────────────────────


def ensure_qb_customer_for_job(job: Job) -> Optional[str]:
    """Ensure a QB Customer exists for `job` -- runs immediately on contract
    save so the accountant can enter Bills against this job in QB before any
    draws have been pushed. Returns the QB Customer.Id on success, or None on
    any failure (matches the never-raise contract of the rest of this module).

    Called from `views.py:save_contract_view` after the Job row is persisted.
    Safe to call repeatedly; the underlying `_ensure_qb_customer` is idempotent
    via the `QbCustomerMap` cache.
    """
    if not job or not job.customer_name:
        return None  # nothing to push yet
    connection = qb_client.get_connection()
    if connection is None:
        return None  # offline -- customer will be created lazily on first draw
    try:
        with qb_client.with_qb_client() as qb:
            return _ensure_qb_customer(qb, job, connection)
    except qb_client.QbNotConnected as exc:
        logger.warning("QB not connected during eager customer push for job %s: %s", job.pk, exc)
        return None
    except Exception as exc:  # noqa: BLE001 -- never break contract save
        logger.exception("Eager QB customer push failed for job %s", job.pk)
        return None
