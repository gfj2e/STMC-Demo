#!/usr/bin/env python3
"""
Shell Contract Estimator
========================
Looks up the three values needed for the ESTIMATED SHELL CONTRACT form:
  - Estimated Total Shell Contract
  - Concrete Budget (Draw 2)
  - Labor Budget (Draw 3)

Source data: BASE_TURN_KEY_MODEL_PRICING_all.xlsx

Usage examples:
    python shell_contract_estimator.py "Huntley 2.0"
    python shell_contract_estimator.py Brookside --region tnky
    python shell_contract_estimator.py --list
    python shell_contract_estimator.py --interactive
    python shell_contract_estimator.py "rocky" --region both
"""

import argparse
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required. Install with:  pip install openpyxl")


# Column indices in the master pricing sheet (1-based for openpyxl)
COL_MODEL        = 1   # A: Home Model
COL_SQFT         = 2   # B: Sq. Foot
COL_MATERIAL     = 4   # D: Material Price
COL_LABOR        = 5   # E: New Labor Rate
COL_CONCRETE_STD = 6   # F: Concrete Price @ $8 (standard)
COL_SHELL_STD    = 7   # G: Shell Only Price (standard)
COL_CONCRETE_TN  = 14  # N: Concrete @ $9 (E. TN & KY)
COL_SHELL_TN     = 15  # O: Shell Price E. TN & KY
COL_QUOTE_ID     = 21  # U: QUOTE ID #


def load_models(xlsx_path: Path) -> dict:
    """Load all model rows into a dict keyed by clean model name."""
    if not xlsx_path.exists():
        sys.exit(f"File not found: {xlsx_path}")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["Sheet1"]
    models = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        name_raw = row[COL_MODEL - 1]
        if name_raw is None:
            continue
        # Strip non-breaking spaces and regular whitespace
        name = str(name_raw).replace("\xa0", " ").strip()
        if not name:
            continue

        models[name] = {
            "sqft":          row[COL_SQFT - 1],
            "material":      row[COL_MATERIAL - 1],
            "labor":         row[COL_LABOR - 1],
            "concrete_std":  row[COL_CONCRETE_STD - 1],
            "shell_std":     row[COL_SHELL_STD - 1],
            "concrete_tnky": row[COL_CONCRETE_TN - 1],
            "shell_tnky":    row[COL_SHELL_TN - 1],
            "quote_id":      row[COL_QUOTE_ID - 1] if len(row) > COL_QUOTE_ID - 1 else None,
        }
    return models


def find_models(models: dict, query: str) -> list:
    """Return matching model names. Exact match wins; otherwise partial (case-insensitive)."""
    q = query.lower().strip()
    for name in models:
        if name.lower() == q:
            return [name]
    return [name for name in models if q in name.lower()]


def fmt_money(val) -> str:
    if val is None:
        return "N/A"
    try:
        return f"${val:,.2f}"
    except (TypeError, ValueError):
        return str(val)


def print_estimate(name: str, data: dict, region: str = "standard") -> None:
    """Print the estimate block. region: 'standard', 'tnky', or 'both'."""
    print()
    print("=" * 64)
    print(f"  {name}")
    sqft = data["sqft"]
    if sqft:
        print(f"  Square Footage: {sqft:,}")
    if data.get("quote_id"):
        print(f"  Quote ID: {data['quote_id']}")
    print("=" * 64)

    blocks = []
    if region in ("standard", "both"):
        blocks.append(("Standard Pricing", data["shell_std"], data["concrete_std"]))
    if region in ("tnky", "both"):
        blocks.append(("East TN & KY Pricing", data["shell_tnky"], data["concrete_tnky"]))

    for header, shell, concrete in blocks:
        print(f"\n  {header}")
        print(f"  {'-' * len(header)}")
        print(f"    ESTIMATED TOTAL SHELL CONTRACT : {fmt_money(shell):>14}")
        print(f"    CONCRETE BUDGET (Draw 2)       : {fmt_money(concrete):>14}")
        print(f"    LABOR BUDGET (Draw 3)          : {fmt_money(data['labor']):>14}")

    # Material reference (filled in later from Summertown Metals quote)
    print(f"\n  Reference (Draw 1 placeholder until Summertown quote returns):")
    print(f"    Material (P10)                 : {fmt_money(data['material']):>14}")
    print()


def list_models(models: dict) -> None:
    print(f"\n{len(models)} models available:\n")
    # Sort by sqft for a useful overview
    sorted_models = sorted(models.items(), key=lambda kv: (kv[1]["sqft"] or 0, kv[0]))
    print(f"  {'Model':<32} {'SqFt':>7} {'Shell (Std)':>14}")
    print(f"  {'-'*32} {'-'*7} {'-'*14}")
    for name, d in sorted_models:
        print(f"  {name:<32} {d['sqft'] or 0:>7,} {fmt_money(d['shell_std']):>14}")
    print()


def interactive_loop(models: dict) -> None:
    print("\nShell Contract Estimator — interactive mode")
    print("Type a model name (or part of one). 'list' to see all, 'quit' to exit.")
    print("Append ' tn' to a query to use East TN & KY pricing  (e.g. 'huntley tn')\n")

    while True:
        try:
            raw = input("model > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not raw:
            continue
        if raw.lower() in ("quit", "exit", "q"):
            return
        if raw.lower() in ("list", "ls"):
            list_models(models)
            continue

        region = "standard"
        query = raw
        lower = raw.lower()
        if lower.endswith(" tn") or lower.endswith(" tnky"):
            region = "tnky"
            query = raw.rsplit(" ", 1)[0]
        elif lower.endswith(" both"):
            region = "both"
            query = raw.rsplit(" ", 1)[0]

        matches = find_models(models, query)
        if not matches:
            print(f"  No models match '{query}'. Try 'list' to see options.\n")
        elif len(matches) > 1:
            print(f"  {len(matches)} matches — be more specific:")
            for m in matches:
                print(f"    - {m}")
            print()
        else:
            print_estimate(matches[0], models[matches[0]], region=region)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Look up Shell Contract estimates from the master pricing sheet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "model",
        nargs="?",
        help="Home model name (full or partial, case-insensitive).",
    )
    parser.add_argument(
        "-f", "--file",
        default="BASE_TURN_KEY_MODEL_PRICING_all.xlsx",
        help="Path to the master pricing xlsx (default: %(default)s)",
    )
    parser.add_argument(
        "-r", "--region",
        choices=["standard", "tnky", "both"],
        default="standard",
        help="Pricing region. 'tnky' = East TN & KY. (default: %(default)s)",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all available models and exit.",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Start an interactive prompt.",
    )
    args = parser.parse_args()

    xlsx_path = Path(args.file)
    models = load_models(xlsx_path)

    if args.list:
        list_models(models)
        return 0

    if args.interactive or not args.model:
        interactive_loop(models)
        return 0

    matches = find_models(models, args.model)
    if not matches:
        print(f"No models match '{args.model}'.")
        print("Use --list to see all available models.")
        return 1
    if len(matches) > 1:
        print(f"{len(matches)} models match '{args.model}' — be more specific:")
        for m in matches:
            print(f"  - {m}")
        return 1

    print_estimate(matches[0], models[matches[0]], region=args.region)
    return 0


if __name__ == "__main__":
    sys.exit(main())
