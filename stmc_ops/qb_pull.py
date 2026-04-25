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

from .models import QbSyncSnapshot
from . import qb_client

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
