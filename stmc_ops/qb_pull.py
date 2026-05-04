"""
QuickBooks Online read-back: fetch aggregated data from QB and cache it.

Where `qb_invoice.py` handles the write path (push invoices to QB),
this module handles the read path (pull Payments, Bills, etc. back into
STMC for display on the owner dashboard).

Design principles
-----------------
* **Don't hit QB per page load.** The dashboard reads from `QbSyncSnapshot`
  (a singleton cache row). The snapshot is refreshed only when:
    - the user clicks the "Refresh from QuickBooks" button, or
    - a scheduled job runs (future; not wired yet).
* **Never crash the dashboard.** Any QB failure downgrades the snapshot
  to `status='stale'` with an error message, preserving the last known
  good values. The UI surfaces the staleness with a subtle warning; it
  does not 500.
* **Scope grows one metric at a time.** This file currently pulls only
  the month-to-date Payments total. Bills / actual-cost / matched counts
  are not yet implemented and remain mock data in the dashboard builder.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from .models import (
    Job,
    JobBudgetLineItem,
    JobDraw,
    JobTradeBudget,
    QbCustomerMap,
    QbInvoiceEvent,
    QbSyncSnapshot,
)
from . import qb_client
from .qb_cost_codes import QB_ACCOUNT_TO_TRADES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# INDIVIDUAL METRIC FETCHERS
# ─────────────────────────────────────────────────────────────


def fetch_month_payments(qb) -> Decimal:
    """Sum the `TotalAmt` of every `Payment` in QB whose `TxnDate` falls
    in the current calendar month.

    Implemented as a client-side sum rather than `SELECT SUM(...)` because
    QB's SQL-ish dialect supports aggregates only in limited cases — safer
    to fetch rows and add. For a realistic sandbox (a few hundred payments
    per month) this is one query and ~200ms.

    Raises on any QB error. Caller wraps in try/except.
    """
    from quickbooks.objects.payment import Payment

    today = timezone.localdate()
    month_start = date(today.year, today.month, 1)
    # QB expects YYYY-MM-DD; safe to build via isoformat().
    query = (
        "SELECT Id, TotalAmt, TxnDate FROM Payment "
        f"WHERE TxnDate >= '{month_start.isoformat()}' "
        "MAXRESULTS 1000"
    )
    results = Payment.query(query, qb=qb)
    total = Decimal("0.00")
    for p in results:
        total += Decimal(str(getattr(p, "TotalAmt", 0) or 0))
    return total

def refresh_actuals_for_job(qb, job: Job) -> dict:
    """Pull paid Bills from QB for `job` and reconcile against budget data.

    Two-tier matching:
      1. **Line-level first** — match each paid Bill line to a
         JobBudgetLineItem (the canonical 29-row PM Budget detail). Tiebreak
         within a trade bucket by BT-code substring in the bill description,
         then by largest remaining (budgeted - actual). Multiple bills hitting
         the same line accumulate via `qb_bill_refs` keyed on (bill_id, line_id).
      2. **Trade fallback** — when no JobBudgetLineItem exists for the job
         (legacy demo data) OR the line resolves to no bucket, credit the
         JobTradeBudget row directly using the original lock-on-first-payment
         behavior.

    After processing, recomputes JobTradeBudget.actual per bucket as the sum
    of JobBudgetLineItem.actual for that bucket so dashboards stay consistent.

    Returns `{matched, skipped, ambiguous}` for logging.

    Raises on any QB error -- caller in `refresh_snapshot` wraps in try/except
    and downgrades the snapshot to STALE on failure.
    """
    from quickbooks.objects.bill import Bill

    counts = {"matched": 0, "skipped": 0, "ambiguous": 0}

    try:
        cust_map = job.qb_customer_map
    except QbCustomerMap.DoesNotExist:
        return counts  # no QB customer for this job yet

    customer_id = cust_map.qb_customer_id
    if not customer_id:
        return counts

    bills = Bill.query("SELECT * FROM Bill MAXRESULTS 500", qb=qb)

    line_rows = list(job.demo_budget_lines.all())
    trade_rows = {tb.trade_name: tb for tb in job.demo_trade_budgets.all()}
    if not line_rows and not trade_rows:
        return counts

    # Group line items by trade bucket and by qb account name once for fast
    # candidate lookup inside the per-bill loop.
    lines_by_bucket = {}
    lines_by_account = {}
    for ln in line_rows:
        if ln.trade_bucket:
            lines_by_bucket.setdefault(ln.trade_bucket, []).append(ln)
        if ln.qb_account_name:
            lines_by_account.setdefault(ln.qb_account_name, []).append(ln)

    for bill in bills:
        if Decimal(str(getattr(bill, "Balance", 0) or 0)) != Decimal("0"):
            continue

        bill_id = str(getattr(bill, "Id", "") or "")
        doc_number = str(getattr(bill, "DocNumber", "") or "")
        vendor_ref = getattr(bill, "VendorRef", None)
        vendor_name = (getattr(vendor_ref, "name", "") or "") if vendor_ref else ""
        txn_date_raw = getattr(bill, "TxnDate", None)
        try:
            txn_date = (
                datetime.strptime(txn_date_raw, "%Y-%m-%d").date()
                if txn_date_raw else None
            )
        except (TypeError, ValueError):
            txn_date = None
        txn_date_iso = txn_date.isoformat() if txn_date else ""

        for line in (bill.Line or []):
            target = _extract_line_target(line)
            line_customer_id = target["customer_id"]
            if line_customer_id is None:
                logger.warning(
                    "QB Bill %s (paid, $%s, item=%s) has no CustomerRef -- "
                    "edit the bill in QB to set Customer = the job.",
                    bill_id or "?",
                    getattr(line, "Amount", "?"),
                    target["item_name"] or "(unknown)",
                )
                continue
            if line_customer_id != customer_id:
                continue

            line_id = str(getattr(line, "Id", "") or "")
            amount = Decimal(str(getattr(line, "Amount", 0) or 0))
            description = str(getattr(line, "Description", "") or "")

            matched_line = _pick_line_for_bill_line(
                target, description,
                lines_by_bucket=lines_by_bucket,
                lines_by_account=lines_by_account,
            )

            if matched_line is not None:
                if _bill_already_recorded(matched_line, bill_id, line_id):
                    counts["skipped"] += 1
                    continue
                matched_line.qb_bill_refs = list(matched_line.qb_bill_refs or []) + [{
                    "bill_id": bill_id,
                    "line_id": line_id,
                    "doc_number": doc_number,
                    "vendor": vendor_name,
                    "txn_date": txn_date_iso,
                    "amount": str(amount),
                }]
                matched_line.actual = (matched_line.actual or Decimal("0")) + amount
                matched_line.last_paid_at = timezone.now()
                matched_line.save(update_fields=[
                    "qb_bill_refs", "actual", "last_paid_at",
                ])
                counts["matched"] += 1
                continue

            # ── Trade-bucket fallback (legacy path) ──
            line_trade = target["trade_bucket"]
            if not line_trade:
                counts["ambiguous"] += 1
                continue
            tb = trade_rows.get(line_trade)
            if tb is None:
                counts["skipped"] += 1
                continue
            if tb.is_complete:
                counts["skipped"] += 1
                continue
            tb.actual = amount
            tb.is_complete = True
            tb.qb_bill_id = bill_id
            tb.paid_at = timezone.now()
            tb.qb_bill_doc_number = doc_number
            tb.qb_bill_vendor = vendor_name
            tb.qb_bill_txn_date = txn_date
            tb.save(update_fields=[
                "actual", "is_complete", "qb_bill_id", "paid_at",
                "qb_bill_doc_number", "qb_bill_vendor", "qb_bill_txn_date",
            ])
            counts["matched"] += 1

    # Roll line actuals up into JobTradeBudget so legacy templates keep working.
    if line_rows:
        _rebuild_trade_actuals_from_lines(job)

    return counts


def _pick_line_for_bill_line(target, description, *, lines_by_bucket, lines_by_account):
    """Choose the best JobBudgetLineItem for a Bill line.

    Strategy: start with candidates whose trade_bucket matches the resolved
    bucket (Item path), or whose qb_account_name matches the AccountRef.name
    (Account path). Tiebreak by BT-code substring in description, then by
    largest remaining (budgeted - actual).
    """
    candidates = []
    bucket = target["trade_bucket"]
    account = target["account_name"]
    if bucket and bucket in lines_by_bucket:
        candidates = lines_by_bucket[bucket]
    elif account and account in lines_by_account:
        candidates = lines_by_account[account]

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    desc_lc = (description or "").lower()
    bt_hits = [c for c in candidates if c.bt_code and c.bt_code.lower() in desc_lc]
    if len(bt_hits) == 1:
        return bt_hits[0]
    pool = bt_hits if bt_hits else candidates

    def remaining(c):
        return (c.budgeted or Decimal("0")) - (c.actual or Decimal("0"))
    pool_sorted = sorted(pool, key=lambda c: (remaining(c), -c.sort_order), reverse=True)
    return pool_sorted[0]


def _bill_already_recorded(line_row, bill_id, line_id):
    refs = line_row.qb_bill_refs or []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        if ref.get("bill_id") == bill_id and ref.get("line_id") == line_id:
            return True
    return False


def _rebuild_trade_actuals_from_lines(job):
    """Recompute JobTradeBudget.actual per bucket = sum of line.actual.

    Also stamps `is_complete` when any bill landed (kept for legacy
    templates that read this field). Single-row updates per bucket.
    """
    bucket_totals = {}
    bucket_paid = {}
    for ln in job.demo_budget_lines.all():
        if not ln.trade_bucket:
            continue
        bucket_totals[ln.trade_bucket] = bucket_totals.get(ln.trade_bucket, Decimal("0")) + (ln.actual or Decimal("0"))
        if ln.qb_bill_refs:
            bucket_paid[ln.trade_bucket] = True

    for tb in job.demo_trade_budgets.all():
        new_actual = bucket_totals.get(tb.trade_name, Decimal("0"))
        new_complete = bool(bucket_paid.get(tb.trade_name))
        changed = []
        if tb.actual != new_actual:
            tb.actual = new_actual
            changed.append("actual")
        if new_complete and not tb.is_complete:
            tb.is_complete = True
            changed.append("is_complete")
        if changed:
            tb.save(update_fields=changed)


def _extract_line_target(line):
    """Resolve a Bill line into routing targets used by the matcher.

    Returns a dict with keys:
      customer_id   — the line's CustomerRef.value (None if missing)
      item_name     — ItemRef.name when this is an item-based line
      account_name  — AccountRef.name when this is an account-based line
      trade_bucket  — the resolved trade-bucket name (1:1 from Item.Name,
                      or via QB_ACCOUNT_TO_TRADES when the account maps to
                      exactly one bucket). None if ambiguous.
    """
    out = {
        "customer_id": None,
        "item_name": None,
        "account_name": None,
        "trade_bucket": None,
    }

    item_detail = getattr(line, "ItemBasedExpenseLineDetail", None)
    if item_detail is not None:
        cust_ref = getattr(item_detail, "CustomerRef", None)
        item_ref = getattr(item_detail, "ItemRef", None)
        out["customer_id"] = getattr(cust_ref, "value", None) if cust_ref else None
        item_name = getattr(item_ref, "name", None) if item_ref else None
        out["item_name"] = item_name
        # Item.Name == JobTradeBudget.trade_name 1:1 (qb_seed_sandbox seeds
        # one Item per trade bucket).
        out["trade_bucket"] = item_name
        return out

    acct_detail = getattr(line, "AccountBasedExpenseLineDetail", None)
    if acct_detail is not None:
        cust_ref = getattr(acct_detail, "CustomerRef", None)
        acct_ref = getattr(acct_detail, "AccountRef", None)
        out["customer_id"] = getattr(cust_ref, "value", None) if cust_ref else None
        acct_name = getattr(acct_ref, "name", None) if acct_ref else None
        out["account_name"] = acct_name
        if acct_name:
            candidates = QB_ACCOUNT_TO_TRADES.get(acct_name, [])
            if len(candidates) == 1:
                out["trade_bucket"] = candidates[0]
            elif len(candidates) > 1:
                logger.warning(
                    "Bill line uses Account '%s' which maps to multiple trades %s; "
                    "tiebreak will rely on description / line-level account match.",
                    acct_name, candidates,
                )
        return out

    return out


# ─────────────────────────────────────────────────────────────
# PHASE 4 — DRAW INVOICE PAID-STATUS PULL
# ─────────────────────────────────────────────────────────────


def refresh_draw_invoices_for_job(qb, job: Job) -> dict:
    """For every draw on `job` that's currently INVOICED, query its QB
    Invoice's Balance. If Balance == 0 (accountant recorded a Payment in
    QB), flip the local JobDraw status to PAID, set paid_date, and stamp
    QbInvoiceEvent.paid_at.

    This is the ONLY path that flips a draw to PAID. PM "Mark Complete"
    only gets us to INVOICED -- the bank's release of funds (recorded as
    a QB Payment by the accountant) is the source of truth for PAID.

    Returns `{paid_now, still_open, skipped}` for logging.

    Raises on QB error -- caller in `refresh_snapshot` wraps in try/except.
    """
    from quickbooks.objects.invoice import Invoice
    counts = {"paid_now": 0, "still_open": 0, "skipped": 0}

    # Only walk INVOICED draws (the lifecycle says PM has clicked Mark
    # Complete, the QB Invoice's DueDate is today, but no Payment has
    # been recorded yet). PENDING + CURRENT haven't reached due-state;
    # PAID is already terminal.
    invoiced_draws = (
        JobDraw.objects.filter(job=job, status=JobDraw.STATUS_INVOICED)
        .order_by("draw_number")
    )

    for draw in invoiced_draws:
        # Find the SENT QbInvoiceEvent for this draw -- it carries the
        # qb_invoice_id we need to query.
        event = (
            QbInvoiceEvent.objects
            .filter(job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT)
            .order_by("-created_at")
            .first()
        )
        if event is None or not event.qb_invoice_id:
            counts["skipped"] += 1
            continue

        try:
            results = Invoice.query(
                f"SELECT Id, Balance FROM Invoice WHERE Id = '{event.qb_invoice_id}'",
                qb=qb,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "refresh_draw_invoices_for_job: lookup failed for invoice %s on draw %s",
                event.qb_invoice_id, draw.pk,
            )
            counts["skipped"] += 1
            continue

        if not results:
            counts["skipped"] += 1
            continue

        invoice = results[0]
        balance = Decimal(str(getattr(invoice, "Balance", 0) or 0))
        if balance > Decimal("0"):
            counts["still_open"] += 1
            continue

        # Balance == 0 -> bank paid this draw. Flip locally + stamp event.
        now = timezone.now()
        today_str = now.strftime("%b ") + str(now.day)
        JobDraw.objects.filter(pk=draw.pk).update(
            status=JobDraw.STATUS_PAID,
            paid_date=today_str,
        )
        event.paid_at = now
        event.save(update_fields=["paid_at"])
        counts["paid_now"] += 1

    # If every draw on this job is now PAID, close the build. The previous
    # behavior closed it as soon as the PM marked the final draw complete,
    # but a draw being marked complete only means INVOICED — the bank can
    # still take days to release the funds. The closed-builds list (PM and
    # owner) now reflects fully-funded jobs, not just PM-completed ones.
    remaining_unpaid = (
        JobDraw.objects.filter(job_id=job.pk)
        .exclude(status=JobDraw.STATUS_PAID)
        .count()
    )
    if remaining_unpaid == 0:
        Job.objects.filter(pk=job.pk).exclude(current_phase="closed").update(
            current_phase="closed"
        )

    return counts


def fetch_unpaid_payments(qb) -> Decimal:
    
    from quickbooks.objects.invoice import Invoice
    
    query = (
        "SELECT Id, Balance,TxnDate FROM Invoice WHERE Balance > '0'"
        "MAXRESULTS 1000"
    )
    
    results = Invoice.query(query, qb=qb)
    total = Decimal("0.00")
    for i in results:
        total += Decimal(str(getattr(i, "Balance", 0) or 0))
    return total

# ─────────────────────────────────────────────────────────────
# ORCHESTRATION
# ─────────────────────────────────────────────────────────────


def refresh_snapshot() -> QbSyncSnapshot:
    """Pull fresh metrics from QB and write them into the singleton snapshot.

    Always returns a `QbSyncSnapshot` — the caller can inspect `.status`
    to know whether the pull succeeded:

        snap = refresh_snapshot()
        if snap.status == QbSyncSnapshot.STATUS_OK:   # fresh data
        if snap.status == QbSyncSnapshot.STATUS_STALE:  # pull failed
        if snap.status == QbSyncSnapshot.STATUS_OFFLINE: # not connected
    """
    snapshot = _get_or_create_snapshot()

    connection = qb_client.get_connection()
    if connection is None:
        snapshot.status = QbSyncSnapshot.STATUS_OFFLINE
        snapshot.last_error = "QuickBooks is not connected."
        snapshot.save(update_fields=["status", "last_error"])
        return snapshot

    try:
        with qb_client.with_qb_client() as qb:
            payments = fetch_month_payments(qb)

            # ── Phase 2: refresh trade actuals from paid Bills ──
            # Only iterate jobs that haven't closed AND have a cached QB
            # Customer mapping. Bound the loop so a sandbox with hundreds
            # of jobs doesn't blow the request budget.
            active_jobs = (
                Job.objects
                .exclude(current_phase="closed")
                .filter(qb_customer_map__isnull=False)
                .select_related("qb_customer_map")[:50]
            )
            totals = {"matched": 0, "skipped": 0, "ambiguous": 0}
            for job in active_jobs:
                try:
                    counts = refresh_actuals_for_job(qb, job)
                    for k, v in counts.items():
                        totals[k] += v
                except Exception as job_exc:  # noqa: BLE001
                    # One failed job shouldn't kill the whole snapshot refresh.
                    logger.warning(
                        "refresh_actuals_for_job failed for job=%s: %s",
                        job.pk, job_exc,
                    )
            if totals["matched"] or totals["ambiguous"]:
                logger.info(
                    "QB actuals refresh: matched=%d skipped=%d ambiguous=%d",
                    totals["matched"], totals["skipped"], totals["ambiguous"],
                )

            # ── Phase 4: refresh draw-invoice paid status ──
            # Walks JobDraws in INVOICED state for each active job. If
            # the corresponding QB Invoice's Balance hits 0 (accountant
            # recorded a Payment in QB), the draw flips to PAID locally
            # and the QbInvoiceEvent gets paid_at stamped. This is the
            # ONLY path that flips a draw to PAID -- PM mark-complete
            # only takes us to INVOICED.
            draw_totals = {"paid_now": 0, "still_open": 0, "skipped": 0}
            for job in active_jobs:
                try:
                    counts = refresh_draw_invoices_for_job(qb, job)
                    for k, v in counts.items():
                        draw_totals[k] += v
                except Exception as job_exc:  # noqa: BLE001
                    logger.warning(
                        "refresh_draw_invoices_for_job failed for job=%s: %s",
                        job.pk, job_exc,
                    )
            if draw_totals["paid_now"]:
                logger.info(
                    "QB draws refresh: paid_now=%d still_open=%d skipped=%d",
                    draw_totals["paid_now"], draw_totals["still_open"], draw_totals["skipped"],
                )
    except qb_client.QbNotConnected as exc:
        logger.warning("QB not connected during snapshot refresh: %s", exc)
        snapshot.status = QbSyncSnapshot.STATUS_STALE
        snapshot.last_error = str(exc)[:500]
        snapshot.save(update_fields=["status", "last_error"])
        return snapshot
    except Exception as exc:  # noqa: BLE001 — deliberate broad catch
        logger.exception("QB snapshot refresh failed")
        snapshot.status = QbSyncSnapshot.STATUS_STALE
        snapshot.last_error = f"{type(exc).__name__}: {exc}"[:500]
        snapshot.save(update_fields=["status", "last_error"])
        return snapshot

    # Success — persist and mark fresh.
    snapshot.payments_this_month = payments
    snapshot.fetched_at = timezone.now()
    snapshot.status = QbSyncSnapshot.STATUS_OK
    snapshot.last_error = ""
    snapshot.save(update_fields=[
        "payments_this_month",
        "fetched_at",
        "status",
        "last_error",
    ])
    return snapshot


def get_snapshot() -> Optional[QbSyncSnapshot]:
    """Non-refreshing read. Returns the cached snapshot or None if the
    refresh button has never been clicked."""
    return QbSyncSnapshot.objects.first()


def _get_or_create_snapshot() -> QbSyncSnapshot:
    """Ensure exactly one row exists. Idempotent."""
    snap = QbSyncSnapshot.objects.first()
    if snap is not None:
        return snap
    return QbSyncSnapshot.objects.create()
