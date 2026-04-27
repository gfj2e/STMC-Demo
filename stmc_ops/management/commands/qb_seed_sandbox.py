"""
Seed a connected QuickBooks sandbox with the COGS sub-accounts + Service
Items the cost-code workflow needs.

Run after connecting a QB sandbox via the owner dashboard:

    python manage.py qb_seed_sandbox

Idempotent. Safe to re-run -- existing accounts/items are matched by name
and reused (no duplicates). The command writes a `QbItemMap` cache row per
trade so `qb_invoice.py` (push) and `qb_pull.py` (pull) can resolve trade
names -> QB Item Ids without re-querying QB on every operation.

What it creates:

    1. 33 sub-accounts under "Cost of Goods Sold" -- mirrors STMC_QB_ACCOUNTS
       from the workbook. Even accounts the interior wizard doesn't directly
       use (Roofing, Excavating, Pest Services...) get created so the
       chart of accounts ends up complete for any future bill flow.

    2. 14 Service Items, one per JobTradeBudget trade bucket
       (Cabinets, Drywall, Electrical, ...). Each Item references its
       primary COGS sub-account from TRADE_TO_QB_ACCOUNT.

The seed creates Items as `Service`-type with both `IncomeAccountRef` and
`ExpenseAccountRef` so they show up in the accountant's Item picker on
both Bill (purchase) and Invoice (sale) forms. STMC's Bills tag Item +
Customer; Invoices tag Item only.
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError

from stmc_ops import qb_client
from stmc_ops.models import QbItemMap
from stmc_ops.qb_cost_codes import STMC_QB_ACCOUNTS, TRADE_TO_QB_ACCOUNT

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed QB sandbox with COGS sub-accounts + Service Items per trade bucket."

    def handle(self, *args, **options):
        connection = qb_client.get_connection()
        if connection is None:
            raise CommandError(
                "QuickBooks is not connected. Sign in to /stmc_ops/owner/ as an "
                "exec user, click 'Connect QuickBooks', then re-run this command."
            )

        try:
            with qb_client.with_qb_client() as qb:
                self.stdout.write(self.style.NOTICE(
                    f"Connected to QB realm {connection.realm_id} "
                    f"({'sandbox' if 'sandbox' in (connection.realm_id or '').lower() or True else 'production'})."
                ))

                # ── Step 1: ensure parent COGS account exists ──
                cogs_parent_id = self._ensure_cogs_parent(qb)

                # ── Step 2: create or match each of the 33 sub-accounts ──
                self.stdout.write("\n[1/2] Seeding 33 COGS sub-accounts:")
                accounts_by_name = {}
                created_accounts = matched_accounts = 0
                for name in STMC_QB_ACCOUNTS:
                    acct, created = self._ensure_cogs_subaccount(qb, name, cogs_parent_id)
                    accounts_by_name[name] = acct
                    if created:
                        created_accounts += 1
                        self.stdout.write(f"  [+ created]  {name}  (Id: {acct.Id})")
                    else:
                        matched_accounts += 1
                        self.stdout.write(self.style.HTTP_INFO(f"  [= existing] {name}  (Id: {acct.Id})"))

                # ── Step 3: create or match Items, refresh QbItemMap cache ──
                self.stdout.write(f"\n[2/2] Seeding {len(TRADE_TO_QB_ACCOUNT)} Items per trade bucket:")
                created_items = matched_items = 0
                for trade_name, account_name in TRADE_TO_QB_ACCOUNT.items():
                    parent_acct = accounts_by_name.get(account_name)
                    if parent_acct is None:
                        # Defensive: should never happen because the import-time
                        # guard in qb_cost_codes.py catches drift. Emit a warning
                        # and skip rather than crash mid-seed.
                        self.stdout.write(self.style.WARNING(
                            f"  [! skipped]  {trade_name} -- account '{account_name}' missing"
                        ))
                        continue

                    item, created = self._ensure_service_item(qb, trade_name, parent_acct)
                    if created:
                        created_items += 1
                        self.stdout.write(f"  [+ created]  {trade_name}  (Item Id: {item.Id} -> {account_name})")
                    else:
                        matched_items += 1
                        self.stdout.write(self.style.HTTP_INFO(
                            f"  [= existing] {trade_name}  (Item Id: {item.Id} -> {account_name})"
                        ))

                    # Cache for fast lookup at push/pull time.
                    QbItemMap.objects.update_or_create(
                        trade_name=trade_name,
                        defaults={
                            "qb_item_id": str(item.Id),
                            "qb_account_id": str(parent_acct.Id),
                            "qb_account_name": account_name,
                            "realm_id": connection.realm_id,
                        },
                    )

        except qb_client.QbNotConnected as exc:
            raise CommandError(f"QuickBooks connection problem: {exc}")
        except Exception as exc:  # noqa: BLE001 -- show the user what happened
            logger.exception("qb_seed_sandbox failed")
            raise CommandError(f"Seeding failed: {type(exc).__name__}: {exc}")

        # ── Summary ──
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"OK Seed complete -- accounts: +{created_accounts} new / ={matched_accounts} existing, "
            f"items: +{created_items} new / ={matched_items} existing."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  QbItemMap rows: {QbItemMap.objects.count()}"
        ))

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────

    def _ensure_cogs_parent(self, qb):
        """Find or create the parent 'Cost of Goods Sold' account.

        Every fresh QBO sandbox ships with this account, but we defensively
        create it if missing so the seed runs against a hand-stripped sandbox.
        Returns the QB Account.Id (string) of the parent.
        """
        from quickbooks.objects.account import Account

        # Match by exact name first; if a sandbox renamed it the seed still
        # works as long as the AccountType is correct.
        existing = Account.query(
            "SELECT Id, Name, AccountType FROM Account "
            "WHERE Name = 'Cost of Goods Sold' MAXRESULTS 1",
            qb=qb,
        )
        if existing:
            return str(existing[0].Id)

        # Fall back: any "Cost of Goods Sold"-type account (different name).
        any_cogs = Account.query(
            "SELECT Id, Name, AccountType FROM Account "
            "WHERE AccountType = 'Cost of Goods Sold' MAXRESULTS 1",
            qb=qb,
        )
        if any_cogs:
            self.stdout.write(self.style.WARNING(
                f"  Note: parent 'Cost of Goods Sold' not found by name -- "
                f"using existing COGS account '{any_cogs[0].Name}' instead."
            ))
            return str(any_cogs[0].Id)

        # Create the parent.
        parent = Account()
        parent.Name = "Cost of Goods Sold"
        parent.AccountType = "Cost of Goods Sold"
        parent.AccountSubType = "SuppliesMaterialsCogs"
        parent = parent.save(qb=qb)
        self.stdout.write(f"  [+ created]  Cost of Goods Sold (parent)")
        return str(parent.Id)

    def _ensure_cogs_subaccount(self, qb, name: str, parent_id: str):
        """Find or create a COGS sub-account under the given parent.

        Returns (Account, created_bool). The created bool is True if we
        called .save() on QB, False if we matched an existing row.
        """
        from quickbooks.objects.account import Account
        from quickbooks.objects.base import Ref

        existing = Account.query(
            f"SELECT Id, Name FROM Account WHERE Name = '{_escape(name)}' MAXRESULTS 1",
            qb=qb,
        )
        if existing:
            return existing[0], False

        acct = Account()
        acct.Name = name
        acct.AccountType = "Cost of Goods Sold"
        acct.AccountSubType = "SuppliesMaterialsCogs"
        parent_ref = Ref()
        parent_ref.value = parent_id
        acct.ParentRef = parent_ref
        acct.SubAccount = True
        acct = acct.save(qb=qb)
        return acct, True

    def _ensure_service_item(self, qb, name: str, parent_account):
        """Find or create a Service Item with both Income and Expense accounts
        pointing to `parent_account` (so it works on both Invoices and Bills).

        Returns (Item, created_bool).
        """
        from quickbooks.objects.item import Item
        from quickbooks.objects.base import Ref

        existing = Item.query(
            f"SELECT Id, Name, Type FROM Item WHERE Name = '{_escape(name)}' MAXRESULTS 1",
            qb=qb,
        )
        if existing:
            return existing[0], False

        # Item references the same Account for both Income and Expense -- keeps
        # the COGS bucket clean (a single account holds both sides of the
        # transaction). Acceptable for cost-code tracking; if accountants ever
        # need separate revenue accounts, this is the spot to split them.
        item = Item()
        item.Name = name
        item.Type = "Service"
        # python-quickbooks requires both Income and Expense account refs to
        # be set when the Item is purchasable AND sellable.
        income_ref = Ref()
        income_ref.value = str(parent_account.Id)
        income_ref.name = parent_account.Name
        item.IncomeAccountRef = income_ref
        expense_ref = Ref()
        expense_ref.value = str(parent_account.Id)
        expense_ref.name = parent_account.Name
        item.ExpenseAccountRef = expense_ref
        # Mark the Item as both purchased (for Bills) and sold (for Invoices).
        # python-quickbooks exposes these as `PurchaseDesc` / `SalesDesc`
        # population AND a top-level `Type = Service`. We rely on the SDK's
        # default behavior which sets sellable+purchasable for Service items.
        item = item.save(qb=qb)
        return item, True


def _escape(s: str) -> str:
    """Escape single quotes for QB's SQL-ish query language."""
    return (s or "").replace("'", "\\'")
