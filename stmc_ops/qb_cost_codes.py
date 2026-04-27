"""
QuickBooks cost-code mapping — Python mirror of the workbook constants.

Single source of truth backend-side. The wizard JS holds the same data
under `STMC_QB_ACCOUNTS`, `STMC_TRADE_MAP`, `STMC_OTHER_MAP` etc. (see
[stmc_ops/static/contracts/buildwizard.js]). Whenever the workbook
[STMC_COST_CODES_FOR_QUICKBOOKS_API_INTEGRATION.xlsm] is regenerated,
update both this file and the JS constants in lockstep.

Used by:
    - stmc_ops/management/commands/qb_seed_sandbox.py
        seeds Accounts + Items in a fresh QB sandbox
    - stmc_ops/qb_invoice.py
        looks up Item Ids when emitting multi-line invoices
    - stmc_ops/qb_pull.py
        matches inbound Bill lines (by Item.Name) back to JobTradeBudget rows

Two design decisions worth knowing:

1. The wizard saves 14 *aggregated* trade buckets into JobTradeBudget
   (see [buildwizard.js:saveContract] TRADE_ORDER). Several trade buckets
   share the same QB Account in the workbook (Cabinets/Countertops both
   route to "Cabinets and Ctops"; Drywall/Paint both route to "Drywall &
   Painting"). To keep cost-code matching unambiguous, the seed creates
   one *Item* per trade bucket — Items can be 1:1 even when their Accounts
   are shared.

2. The 33-account list mirrors the workbook in full so the QB Chart of
   Accounts ends up with every bucket the contractor pipeline needs,
   even though only ~14 are actively used by the interior wizard. That
   keeps room for exterior labor, freight, contract allowance etc. when
   they come back into scope.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# 1. STMC_QB_ACCOUNTS — full Chart of Accounts (33 entries)
# ─────────────────────────────────────────────────────────────
# Mirrors `STMC_QB_ACCOUNTS` in buildwizard.js. Every Bill that flows
# through STMC must route to one of these accounts. Order matches the
# workbook (alphabetical, with the "01-SALES CONTRACT" header first).
STMC_QB_ACCOUNTS = [
    "01-SALES CONTRACT - Summertown",
    "Appliances",
    "Buildertrend Invoice",
    "Cabinets and Ctops",
    "Concrete",
    "Contract Allowance Expense",
    "Cost of labor",
    "Drywall & Painting",
    "Electrical Installation",
    "Excavating",
    "Final Cleaning",
    "Fireplaces",
    "Flooring",
    "Framing of Home",
    "Freight in",
    "Gutters & Downspouts",
    "HVAC",
    "Insulation - Spray Foam",
    "Interior Trim & Doors",
    "Material Misc - For Completion",
    "Metal Walls",
    "Permits",
    "Pest Services",
    "Plumbing",
    "Plumbing & Lighting Fixtures",
    "Plumbing Installation",
    "Porta Potty",
    "Professional Services",
    "Punch List Labor",
    "Roofing",
    "Shipping/Delivery",
    "Warranty Work Performed",
    "Waste Removal",
]


# ─────────────────────────────────────────────────────────────
# 2. TRADE_TO_QB_ACCOUNT — JobTradeBudget bucket → primary QB Account
# ─────────────────────────────────────────────────────────────
# These 14 keys mirror the trade names that
# [buildwizard.js:saveContract] writes into JobTradeBudget. The seed
# command creates a QB Item with the trade-bucket name (the dict key),
# pointing at the QB Account named on the right.
#
# Where multiple buckets share one Account (Cabinets/Countertops →
# "Cabinets and Ctops"; Drywall/Paint → "Drywall & Painting"), each
# bucket still gets its own Item — the seed creates two Items both
# referencing the shared Account. The puller matches by Item.Name so
# the trades stay distinguishable.
#
# "Permits & General" rolls up Permits + Final Cleaning + Site Prep +
# Dumpster on the manager dashboard. We point its Item at the "Permits"
# Account (the largest sub-bucket) — accountants tagging Final Clean,
# Dumpster, etc. would tag the more specific Item if they want finer
# granularity, but for the demo a single rolled-up bucket is enough.
TRADE_TO_QB_ACCOUNT = {
    "Contractor Labor":  "Cost of labor",
    "Cabinets":          "Cabinets and Ctops",
    "Countertops":       "Cabinets and Ctops",
    "Flooring":          "Flooring",
    "Drywall":           "Drywall & Painting",
    "Paint":             "Drywall & Painting",
    "Trim & Doors":      "Interior Trim & Doors",
    "Electrical":        "Electrical Installation",
    "Plumbing":          "Plumbing Installation",
    "Insulation":        "Insulation - Spray Foam",
    "HVAC":              "HVAC",
    "Light Fixtures":    "Plumbing & Lighting Fixtures",
    "Fireplaces":        "Fireplaces",
    "Permits & General": "Permits",
}


# ─────────────────────────────────────────────────────────────
# 3. Reverse map — QB Account → list of trade buckets
# ─────────────────────────────────────────────────────────────
# Used by the puller's fallback path: if an accountant tags a Bill line
# with an Account (not an Item), and exactly one trade bucket maps to
# that Account, the puller can still credit the right row. If multiple
# trade buckets share the Account (e.g. "Cabinets and Ctops"), the
# puller logs an "ambiguous" warning and skips — the accountant must
# re-enter the Bill using the Item picker. The demo workflow always
# uses Items so this path is informational only.
def _build_reverse_map():
    rev = {}
    for trade, account in TRADE_TO_QB_ACCOUNT.items():
        rev.setdefault(account, []).append(trade)
    return rev


QB_ACCOUNT_TO_TRADES = _build_reverse_map()


# ─────────────────────────────────────────────────────────────
# Sanity: every account referenced by TRADE_TO_QB_ACCOUNT must exist
# in the master STMC_QB_ACCOUNTS list. Dev-time guard — fails loudly
# at import time if the two lists drift.
# ─────────────────────────────────────────────────────────────
_missing = [
    a for a in TRADE_TO_QB_ACCOUNT.values()
    if a not in STMC_QB_ACCOUNTS
]
if _missing:
    raise RuntimeError(
        "qb_cost_codes.py: TRADE_TO_QB_ACCOUNT references accounts not in "
        f"STMC_QB_ACCOUNTS: {sorted(set(_missing))}. Update one or the other."
    )
