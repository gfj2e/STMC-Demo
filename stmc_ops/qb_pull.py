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
from datetime import date
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from .models import Job, JobTradeBudget, QbCustomerMap, QbSyncSnapshot
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
    """Pull paid Bills from QB for `job` and stamp matching JobTradeBudget rows.

    Match logic:
      * Filter Bills where any line's `CustomerRef.value == job's cached
        QB Customer Id` (`QbCustomerMap`). Skip if no map row -- the eager
        push hasn't fired yet.
      * For each Bill where `Balance == 0` (fully paid):
          - Item-based line: extract `ItemRef.name`, match to a
            JobTradeBudget by exact `trade_name`.
          - Account-based line (fallback): extract `AccountRef.name`,
            look up in QB_ACCOUNT_TO_TRADES. Credit only if exactly
            ONE trade maps to that account; log + skip if ambiguous.
      * If matching JobTradeBudget exists AND `is_complete == False`:
        stamp `actual = line.Amount`, set `is_complete = True`,
        `qb_bill_id = bill.Id`, `paid_at = now()`. Save.
      * If `is_complete == True` already: skip (lock-on-first-payment).

    Returns `{matched: int, skipped: int, ambiguous: int}` for logging.

    Raises on any QB error -- caller in `refresh_snapshot` wraps in
    try/except and downgrades the snapshot to STALE on failure.
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

    # Pull all Bills tagged to this customer. QB's query language doesn't
    # support filtering by nested CustomerRef on Line directly, so we fetch
    # candidate Bills and filter client-side. For a sandbox with a few
    # hundred Bills this is one round-trip and ~200ms.
    #
    # NOTE: There's no top-level CustomerRef on a Bill in QBO -- the
    # CustomerRef lives on the Line.AccountBasedExpenseLineDetail or
    # Line.ItemBasedExpenseLineDetail. So we have to scan and filter.
    bills = Bill.query("SELECT * FROM Bill MAXRESULTS 500", qb=qb)

    # Pre-load all trade-budget rows for this job in a single query.
    trade_rows = {tb.trade_name: tb for tb in job.demo_trade_budgets.all()}
    if not trade_rows:
        return counts

    for bill in bills:
        # Only fully-paid bills count -- "lock on first payment" behavior.
        if Decimal(str(getattr(bill, "Balance", 0) or 0)) != Decimal("0"):
            continue

        for line in (bill.Line or []):
            line_customer_id, line_trade = _extract_line_target(line)
            if line_customer_id is None:
                # Paid bill with no Customer reference — the accountant likely
                # forgot to tag the line with a job, OR the QB sandbox setting
                # "Track expenses and items by customer" is OFF (so the
                # Customer column isn't appearing on Bill forms). Either way
                # we can't attribute it. Log once per offending bill so the
                # owner dashboard owner knows to follow up.
                logger.warning(
                    "QB Bill %s (paid, $%s, item=%s) has no CustomerRef -- "
                    "edit the bill in QB to set Customer = the job, or check "
                    "that 'Track expenses and items by customer' is ON in "
                    "Account and Settings -> Expenses.",
                    getattr(bill, "Id", "?"),
                    getattr(line, "Amount", "?"),
                    line_trade or "(unknown)",
                )
                continue
            if line_customer_id != customer_id:
                continue
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

            tb.actual = Decimal(str(getattr(line, "Amount", 0) or 0))
            tb.is_complete = True
            tb.qb_bill_id = str(bill.Id)
            tb.paid_at = timezone.now()
            tb.save(update_fields=["actual", "is_complete", "qb_bill_id", "paid_at"])
            counts["matched"] += 1

    return counts


def _extract_line_target(line):
    """Pick the CustomerRef and trade name (matching JobTradeBudget.trade_name)
    out of a Bill line's detail block.

    Returns `(customer_id, trade_name)` where either may be None if the
    line doesn't carry the relevant ref. `trade_name` is None for
    ambiguous Account-based lines (account shared between multiple trades).
    """
    # Item-based line: ItemBasedExpenseLineDetail with ItemRef + CustomerRef
    item_detail = getattr(line, "ItemBasedExpenseLineDetail", None)
    if item_detail is not None:
        cust_ref = getattr(item_detail, "CustomerRef", None)
        item_ref = getattr(item_detail, "ItemRef", None)
        cust_id = getattr(cust_ref, "value", None) if cust_ref else None
        # ItemRef.name matches JobTradeBudget.trade_name 1:1 because the
        # seed command creates one Item per trade bucket (e.g. "Cabinets",
        # "Drywall") -- see qb_seed_sandbox._ensure_service_item.
        item_name = getattr(item_ref, "name", None) if item_ref else None
        return cust_id, item_name

    # Account-based fallback: AccountRef.name -> reverse-map to trade(s).
    acct_detail = getattr(line, "AccountBasedExpenseLineDetail", None)
    if acct_detail is not None:
        cust_ref = getattr(acct_detail, "CustomerRef", None)
        acct_ref = getattr(acct_detail, "AccountRef", None)
        cust_id = getattr(cust_ref, "value", None) if cust_ref else None
        acct_name = getattr(acct_ref, "name", None) if acct_ref else None
        if not acct_name:
            return cust_id, None
        candidates = QB_ACCOUNT_TO_TRADES.get(acct_name, [])
        if len(candidates) == 1:
            return cust_id, candidates[0]
        # Ambiguous (account shared between trades like Cabinets+Countertops).
        # Log and let the caller increment the ambiguous counter.
        logger.warning(
            "Bill line uses Account '%s' which maps to multiple trades %s; "
            "accountant should re-enter using the Item picker. Skipping.",
            acct_name, candidates,
        )
        return cust_id, None

    return None, None


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
