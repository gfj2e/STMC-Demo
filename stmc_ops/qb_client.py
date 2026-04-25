"""
QuickBooks Online client helpers.

One-stop module for everything OAuth- and client-session-related. The rest of
the app (views, the draw-completion hook) goes through the functions here so
token refresh, connection lookup, and sandbox-vs-prod URL selection all live
in one place.

Dependencies (installed via requirements.txt):
    intuit-oauth      — official Intuit OAuth 2.0 SDK (token exchange + refresh)
    python-quickbooks — community REST SDK (Customer/Invoice/Item/... objects)

Design notes
------------
* We treat QbConnection as a singleton: one QuickBooks company at a time.
  `get_connection()` returns it or None.
* Access tokens are refreshed proactively when within 5 minutes of expiry.
  If the refresh token itself is dead (100-day hard limit, or user revoked
  access on Intuit's side) we raise QbNotConnected so callers fall back
  gracefully.
* Callers should always use `with_qb_client()` as a context manager:

      try:
          with with_qb_client() as qb:
              customer = Customer.query(..., qb=qb)
      except QbNotConnected:
          # degrade gracefully (demo fallback, toast error, etc.)
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone

from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError
from quickbooks import QuickBooks

from .models import QbConnection


# ─────────────────────────────────────────────────────────────
# EXCEPTIONS
# ─────────────────────────────────────────────────────────────


class QbError(Exception):
    """Base class for all QuickBooks-integration errors."""


class QbNotConnected(QbError):
    """Raised when no QbConnection row exists, or the stored refresh token
    has expired / been revoked. Callers should fall back gracefully."""


class QbConfigError(QbError):
    """Raised when QB_CLIENT_ID / QB_CLIENT_SECRET settings are missing."""


# ─────────────────────────────────────────────────────────────
# AUTH CLIENT FACTORY
# ─────────────────────────────────────────────────────────────


def _scope_objects():
    """Translate scope strings from settings into intuitlib Scope enum values."""
    mapping = {
        "com.intuit.quickbooks.accounting": Scopes.ACCOUNTING,
        "com.intuit.quickbooks.payment": Scopes.PAYMENT,
    }
    out = []
    for name in getattr(settings, "QB_SCOPES", ["com.intuit.quickbooks.accounting"]):
        scope = mapping.get(name)
        if scope is None:
            raise QbConfigError(f"Unknown QB scope: {name}")
        out.append(scope)
    return out


def build_auth_client(connection: Optional[QbConnection] = None) -> AuthClient:
    """Construct an intuitlib AuthClient from Django settings, optionally
    prefilled with tokens from an existing connection.

    Use this for:
      * generating the authorize URL (connect flow)
      * exchanging an authorization code for tokens (callback flow)
      * refreshing an expired access token
    """
    client_id = settings.QB_CLIENT_ID
    client_secret = settings.QB_CLIENT_SECRET
    if not client_id or not client_secret:
        raise QbConfigError(
            "QB_CLIENT_ID and QB_CLIENT_SECRET must be set in settings "
            "(or via environment variables QB_CLIENT_ID / QB_CLIENT_SECRET) "
            "before the QuickBooks integration can be used."
        )

    auth_client = AuthClient(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=settings.QB_REDIRECT_URI,
        environment=settings.QB_ENVIRONMENT,  # "sandbox" or "production"
    )
    if connection:
        auth_client.access_token = connection.access_token
        auth_client.refresh_token = connection.refresh_token
        auth_client.realm_id = connection.realm_id
    return auth_client


# ─────────────────────────────────────────────────────────────
# CONNECTION LIFECYCLE
# ─────────────────────────────────────────────────────────────


def get_connection() -> Optional[QbConnection]:
    """Return the current QB connection row, or None if we've never connected
    (or the connection was disconnected)."""
    return QbConnection.objects.first()


def save_connection_from_auth_client(
    auth_client: AuthClient,
    realm_id: str,
    connected_by_email: str = "",
) -> QbConnection:
    """After a successful OAuth exchange, persist the tokens. Overwrites any
    existing row (we treat QbConnection as a singleton)."""
    now = timezone.now()
    # intuitlib exposes expires_in (seconds) — we translate to an absolute ts.
    access_ttl = getattr(auth_client, "expires_in", 3600) or 3600
    refresh_ttl = getattr(auth_client, "x_refresh_token_expires_in", 100 * 24 * 3600) or (100 * 24 * 3600)

    QbConnection.objects.all().delete()
    return QbConnection.objects.create(
        realm_id=realm_id,
        access_token=auth_client.access_token,
        refresh_token=auth_client.refresh_token,
        access_token_expires_at=now + timedelta(seconds=int(access_ttl)),
        refresh_token_expires_at=now + timedelta(seconds=int(refresh_ttl)),
        connected_at=now,
        connected_by_email=connected_by_email[:200],
    )


def disconnect() -> None:
    """Drop the stored connection row. The user can reconnect via the Connect
    QuickBooks button on the owner dashboard. We don't revoke on Intuit's side
    here — that happens via the Intuit app dashboard."""
    QbConnection.objects.all().delete()


# ─────────────────────────────────────────────────────────────
# TOKEN REFRESH + CLIENT SESSION
# ─────────────────────────────────────────────────────────────


def _ensure_fresh_access_token(connection: QbConnection, auth_client: AuthClient) -> None:
    """Refresh the access token if it's within 5 minutes of expiry. Updates
    both the AuthClient (for the current call) and the stored QbConnection row
    (so future calls skip this step)."""
    threshold = timezone.now() + timedelta(minutes=5)
    if connection.access_token_expires_at > threshold:
        return  # still fresh

    try:
        auth_client.refresh(refresh_token=connection.refresh_token)
    except AuthClientError as exc:
        raise QbNotConnected(
            "QuickBooks refresh failed — the connection may have been revoked "
            "or the refresh token expired. Reconnect via the owner dashboard."
        ) from exc

    now = timezone.now()
    connection.access_token = auth_client.access_token
    connection.refresh_token = auth_client.refresh_token
    connection.access_token_expires_at = now + timedelta(
        seconds=int(getattr(auth_client, "expires_in", 3600) or 3600)
    )
    # Intuit issues a fresh refresh token on each refresh; its TTL resets.
    connection.refresh_token_expires_at = now + timedelta(
        seconds=int(getattr(auth_client, "x_refresh_token_expires_in", 100 * 24 * 3600) or (100 * 24 * 3600))
    )
    connection.last_refreshed_at = now
    connection.save(update_fields=[
        "access_token",
        "refresh_token",
        "access_token_expires_at",
        "refresh_token_expires_at",
        "last_refreshed_at",
    ])


@contextmanager
def with_qb_client():
    """Context manager yielding a live python-quickbooks `QuickBooks` instance,
    ready to use for `Customer.query(qb=...)`, `Invoice.save(qb=...)`, etc.

    Raises QbNotConnected if there's no stored connection or token refresh
    failed. Callers are expected to catch that and fall back gracefully.
    """
    connection = get_connection()
    if connection is None:
        raise QbNotConnected("QuickBooks is not connected. Connect via the owner dashboard first.")

    auth_client = build_auth_client(connection)
    _ensure_fresh_access_token(connection, auth_client)

    qb = QuickBooks(
        auth_client=auth_client,
        refresh_token=connection.refresh_token,
        company_id=connection.realm_id,
    )
    try:
        yield qb
    finally:
        # python-quickbooks doesn't hold persistent state we need to tear down;
        # the context manager is here to keep call-sites tidy and to leave
        # room for future cleanup (e.g. metrics).
        pass


# ─────────────────────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────────────────────


def is_connected() -> bool:
    """Cheap bool check for UI — does not hit the Intuit API."""
    return QbConnection.objects.exists()


def invoice_public_url(connection: QbConnection, qb_invoice_id: str) -> str:
    """Build a URL that opens QBO to a page where the user can find this
    invoice.

    We intentionally link to the Sales Transactions list rather than to
    QBO's "direct invoice" deep-link (`/app/invoice?txnId=X`). The deep-
    link is officially supported but unreliable in practice: if the user
    has multiple QB companies, a stale session, or hits the URL without
    being pre-authenticated, QBO silently opens an empty new-invoice form
    instead of loading the specified transaction. The Sales Transactions
    list always opens the right page — users locate the specific invoice
    by its DocNumber (shown as the link text in the bell dropdown).

    `qb_invoice_id` is accepted but unused — kept on the signature so
    future callers can swap back to a deep-link format if Intuit's URL
    behavior becomes reliable.
    """
    # QBO's Sales page (menu label "Sales" / "Sales Transactions") lives
    # at /app/sales, not /app/salestransactions. The list is sorted newest
    # first so freshly-created invoices appear at the top.
    return f"{_qbo_base_url()}/app/sales"


def portal_url(connection: QbConnection) -> str:
    """Build the URL that drops the user into the connected company's
    QuickBooks Online portal homepage. The realm id is included as a hint;
    QBO will prompt the user to switch companies if they're signed into a
    different one."""
    return f"{_qbo_base_url()}/app/homepage?companyId={connection.realm_id}"


def _qbo_base_url() -> str:
    """Sandbox and production live on different QBO domains."""
    if settings.QB_ENVIRONMENT == "production":
        return "https://app.qbo.intuit.com"
    return "https://app.sandbox.qbo.intuit.com"
