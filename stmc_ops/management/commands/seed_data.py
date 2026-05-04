"""
STMC Turnkey Estimator — Seed Data
===================================
Run: python manage.py seed_data

Seeds all reference data: branches, rate cards, budget trades, upgrade items,
appliance configs, and island addons. Model-specific data (PM, MD, RD, P10, MODELS,
CRAFTSMAN, INT_CONTRACT, BASE_COSTS) must be loaded from the source HTML files.

This file contains the STRUCTURE seed. The model preset seed is in seed_models.py
(generated separately from the V8 HTML and INT_CONTRACTS_APP HTML source files).
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from stmc_ops.models import (
    AppUser, Branch, BudgetTrade, BudgetTradeRate, FloorPlanModel, InteriorRateCard, Job,
    JobBudgetLineItem, JobTradeBudget, JobDraw,
    UpgradeCategory, UpgradeSection, UpgradeItem, ApplianceConfig, IslandAddon,
)


# Canonical line-item template per seeded trade bucket. Mirrors the BT cost code
# / QB account / draw assignment from the wizard's buildPMBudgetRows() so the
# manager dashboard drill-down has plausible cost-code data without needing the
# wizard to run for every demo job.
SEED_TRADE_LINE_TEMPLATES = {
    "Cabinets":          ("Cabinets",                    "Cabinets and Ctops",         "Cabinets and Ctops",         5),
    "Countertops":       ("Countertops",                 "Cabinets and Ctops",         "Cabinets and Ctops",         5),
    "Flooring":          ("Flooring Materials",          "Flooring",                   "Flooring",                   5),
    "Drywall":           ("Drywall Material",            "Drywall",                    "Drywall & Painting",         5),
    "Paint":             ("Painting",                    "Painting",                   "Drywall & Painting",         5),
    "Trim":              ("Trim and Door Materials",     "Interior Trim & Doors",      "Interior Trim & Doors",      5),
    "Trim & Doors":      ("Trim and Door Materials",     "Interior Trim & Doors",      "Interior Trim & Doors",      5),
    "Electrical":        ("Electrical",                  "Electrical Installation",    "Electrical Installation",    4),
    "Plumbing":          ("Plumbing Installation",       "Plumbing Installation",      "Plumbing Installation",      4),
    "Insulation":        ("Insulation",                  "Insulation - Spray Foam",    "Insulation - Spray Foam",    4),
    "HVAC":              ("HVAC",                        "HVAC",                       "HVAC",                       4),
    "Light Fixtures":    ("Plumbing & Light Fixtures",   "Plumbing & Lighting Fixtures","Plumbing & Lighting Fixtures",5),
    "Fireplaces":        ("Fireplace",                   "Fireplace",                  "Fireplaces",                 5),
    "Contractor Labor":  ("Framing",                     "Whole House Framing",        "Framing of Home",            3),
    "General":           ("Permits",                     "Permits",                    "Permits",                    6),
    "Permits & General": ("Permits",                     "Permits",                    "Permits",                    6),
}


class Command(BaseCommand):
    help = 'Seed STMC reference data (branches, rate cards, trades, upgrades)'

    def handle(self, *args, **options):
        self.seed_users()
        self.seed_branches()
        self.seed_interior_rate_card()
        self.seed_budget_trades()
        self.seed_trade_rate_mappings()
        self.seed_appliance_configs()
        self.seed_island_addons()
        self.seed_upgrade_catalog()
        self.seed_demo_jobs()
        self.stdout.write(self.style.SUCCESS('All reference data seeded.'))

    # ─────────────────────────────────────────
    # APP USERS
    # ─────────────────────────────────────────
    def seed_users(self):
        data = [
            {
                "email": "d.robinson@stmc.com",
                "username": "d.robinson@stmc.com",
                "name": "Danny Robinson",
                "initials": "DR",
                "role": "sales",
                "title": "Sales Rep",
                "sort_order": 1,
                "password": "stmsales",
            },
            {
                "email": "p.olson@stmc.com",
                "username": "p.olson@stmc.com",
                "name": "Phillip Olson",
                "initials": "PO",
                "role": "pm",
                "title": "Project Manager",
                "sort_order": 2,
                "password": "stmpm",
            },
            {
                "email": "m.stoll@stmc.com",
                "username": "m.stoll@stmc.com",
                "name": "Matt Stoll",
                "initials": "MS",
                "role": "exec",
                "title": "Executive / Owner",
                "sort_order": 3,
                "password": "stmexecutive",
            },
        ]
        for row in data:
            password = row.pop("password")
            user, _ = AppUser.objects.update_or_create(
                email=row["email"], defaults=row
            )
            user.set_password(password)
            user.is_active = True
            user.save(update_fields=["password", "is_active"])
        self.stdout.write(f'  App Users: {len(data)}')

    # ─────────────────────────────────────────
    # BRANCHES
    # ─────────────────────────────────────────
    def seed_branches(self):
        # qb_bank_account_id values are valid for the demo QB sandbox realm
        # only. After connecting a different realm (or moving to production)
        # re-map via /stmc_ops/owner/qb/bank-accounts/ — these IDs will not
        # match any account on a different company.
        data = [
            {
                "key": "summertown", "label": "Summertown Main",
                "conc_rate": 8, "default_miles": 0, "zone": 1,
                "qb_bank_account_id": "1150040037",
                "qb_bank_account_name": "Summertown Main TN Branch",
            },
            {
                "key": "hayden_al", "label": "Hayden, AL",
                "conc_rate": 8, "default_miles": 0, "zone": 1,
                "qb_bank_account_id": "1150040039",
                "qb_bank_account_name": "Summertown Hayden AL Branch",
            },
            {
                "key": "morristown", "label": "Morristown",
                "conc_rate": 9, "default_miles": 1, "zone": 2,
                "qb_bank_account_id": "1150040038",
                "qb_bank_account_name": "Summertown Morristown TN Branch",
            },
            {
                "key": "hopkinsville", "label": "Hopkinsville",
                "conc_rate": 9, "default_miles": 1, "zone": 3,
                "qb_bank_account_id": "1150040040",
                "qb_bank_account_name": "Summertown Hopkinsville KY Branch",
            },
        ]
        for d in data:
            Branch.objects.update_or_create(key=d["key"], defaults=d)
        self.stdout.write(f'  Branches: {len(data)}')

    # ─────────────────────────────────────────
    # INTERIOR RATE CARD (INT_RC)
    # ─────────────────────────────────────────
    def seed_interior_rate_card(self):
        data = [
            # Materials & Fixtures
            {"key": "cabinets", "label": "Cabinets (incl install)", "rate": 250, "unit": "/LF", "driver": "cabLF"},
            {"key": "countertops", "label": "Countertops (budget true cost)", "rate": 43, "unit": "/SF", "driver": "counterSF"},
            {"key": "floorMat", "label": "Flooring Material (LVP)", "rate": 1.89, "unit": "/SF", "driver": "livingSF"},
            {"key": "drywallMat", "label": "Drywall Material", "rate": 0.87, "unit": "/SF", "driver": "drywallSF"},
            {"key": "paint", "label": "Paint (material + labor)", "rate": 4.00, "unit": "/SF", "driver": "livingSF"},
            {"key": "paintExtDoor", "label": "Exterior Door Paint", "rate": 300, "unit": "flat", "driver": "flat"},
            {"key": "trimMat", "label": "Trim Material", "rate": 3.96, "unit": "/LF", "driver": "trimLF"},
            {"key": "doorMat", "label": "Interior Doors (prehung)", "rate": 150, "unit": "/door", "driver": "doors"},
            {"key": "lightBase", "label": "Light Fixtures — Base", "rate": 800, "unit": "flat", "driver": "flat"},
            {"key": "lightBath", "label": "Light Fixtures — Per Bath", "rate": 600, "unit": "/bath", "driver": "bathCount"},
            {"key": "plumbFixBase", "label": "Plumb Fixtures — Base (WH + kitchen)", "rate": 900, "unit": "flat", "driver": "flat"},
            {"key": "plumbFixBath", "label": "Plumb Fixtures — Per Bath", "rate": 1100, "unit": "/bath", "driver": "bathCount"},
            {"key": "insulation", "label": "Spray Foam Insulation", "rate": 3.26, "unit": "/SF", "driver": "livingSF"},
            # Labor
            {"key": "floorLab", "label": "Flooring Install Labor", "rate": 1.00, "unit": "/SF", "driver": "livingSF"},
            {"key": "drywallLab", "label": "Drywall Labor", "rate": 0.83, "unit": "/SF", "driver": "drywallSF"},
            {"key": "trimDoorLab", "label": "Trim & Door Install Labor", "rate": 2.71, "unit": "/SF", "driver": "livingSF"},
            {"key": "electrical", "label": "Electrical Labor", "rate": 7.50, "unit": "/SF", "driver": "livingSF"},
            {"key": "plumbingLab", "label": "Plumbing Labor ($230 R/I + $150 trim)", "rate": 380, "unit": "/fix", "driver": "fixtures"},
            {"key": "hvac", "label": "HVAC (per ton)", "rate": 3400, "unit": "/ton", "driver": "hvacTons"},
            # General
            {"key": "permits", "label": "Permits", "rate": 2000, "unit": "flat", "driver": "flat"},
            {"key": "cleaning", "label": "Final Cleaning", "rate": 875, "unit": "flat", "driver": "flat"},
            {"key": "dumpster", "label": "Dumpster", "rate": 1000, "unit": "flat", "driver": "flat"},
        ]
        for d in data:
            InteriorRateCard.objects.update_or_create(key=d["key"], defaults=d)
        self.stdout.write(f'  Interior Rate Card: {len(data)} entries')

    # BUDGET TRADES (16 interior + 7 exterior)
    # ─────────────────────────────────────────
    def seed_budget_trades(self):
        interior = [
            {"key": "cabinets", "name": "Cabinets", "sort_order": 1, "has_base_cost": True},
            {"key": "countertops", "name": "Countertops", "sort_order": 2, "has_base_cost": True},
            {"key": "flooring", "name": "Flooring", "sort_order": 3, "has_base_cost": True},
            {"key": "drywall", "name": "Drywall", "sort_order": 4, "has_base_cost": True},
            {"key": "paint", "name": "Paint", "sort_order": 5, "has_base_cost": True},
            {"key": "trim", "name": "Trim & Doors", "sort_order": 6, "has_base_cost": True},
            {"key": "electrical", "name": "Electrical", "sort_order": 7, "has_base_cost": True},
            {"key": "plumbing", "name": "Plumbing", "sort_order": 8, "has_base_cost": True},
            {"key": "insulation", "name": "Insulation", "sort_order": 9, "has_base_cost": True},
            {"key": "hvac", "name": "HVAC", "sort_order": 10, "has_base_cost": True},
            {"key": "lighting", "name": "Light Fixtures", "sort_order": 11, "has_base_cost": True},
            {"key": "fireplaces", "name": "Fireplaces", "sort_order": 12, "has_base_cost": False},
            {"key": "tile", "name": "Tile", "sort_order": 13, "has_base_cost": False},
            {"key": "concreteFinish", "name": "Concrete Floor Finish", "sort_order": 14, "has_base_cost": False},
            {"key": "general", "name": "Permits & General", "sort_order": 15, "has_base_cost": True},
            {"key": "customSelections", "name": "Custom Selections", "sort_order": 16, "has_base_cost": False},
        ]
        exterior = [
            {"key": "framing", "name": "Framing", "sort_order": 1, "has_base_cost": True},
            {"key": "sheathing", "name": "Sheathing", "sort_order": 2, "has_base_cost": True},
            {"key": "roof", "name": "Roof", "sort_order": 3, "has_base_cost": True},
            {"key": "walls", "name": "Walls & Soffit", "sort_order": 4, "has_base_cost": True},
            {"key": "stone", "name": "Stone", "sort_order": 5, "has_base_cost": True},
            {"key": "dw", "name": "Doors & Windows", "sort_order": 6, "has_base_cost": True},
            {"key": "other", "name": "Other", "sort_order": 7, "has_base_cost": True},
        ]
        for d in interior:
            BudgetTrade.objects.update_or_create(key=d["key"], defaults={**d, "scope": "interior"})
        for d in exterior:
            BudgetTrade.objects.update_or_create(key=d["key"], defaults={**d, "scope": "exterior"})
        self.stdout.write(f'  Budget Trades: {len(interior)} interior + {len(exterior)} exterior')

    # ─────────────────────────────────────────
    # TRADE ↔ RATE CARD MAPPINGS
    # ─────────────────────────────────────────
    def seed_trade_rate_mappings(self):
        mappings = {
            "cabinets": ["cabinets"],
            "countertops": ["countertops"],
            "flooring": ["floorMat", "floorLab"],
            "drywall": ["drywallMat", "drywallLab"],
            "paint": ["paint", "paintExtDoor"],
            "trim": ["trimMat", "doorMat", "trimDoorLab"],
            "electrical": ["electrical"],
            "plumbing": ["plumbFixBase", "plumbFixBath", "plumbingLab"],
            "insulation": ["insulation"],
            "hvac": ["hvac"],
            "lighting": ["lightBase", "lightBath"],
            "general": ["permits", "cleaning", "dumpster"],
        }
        count = 0
        for trade_key, rate_keys in mappings.items():
            trade = BudgetTrade.objects.get(key=trade_key)
            for rk in rate_keys:
                rc = InteriorRateCard.objects.get(key=rk)
                BudgetTradeRate.objects.update_or_create(trade=trade, rate_card=rc)
                count += 1
        self.stdout.write(f'  Trade-Rate Mappings: {count}')

    # ─────────────────────────────────────────
    # APPLIANCE CONFIGS
    # ─────────────────────────────────────────
    def seed_appliance_configs(self):
        data = [
            {"key": "standard_range_mw", "label": "Standard Range with Microwave or Undercabinet Vent Hood Above", "cost": 0, "sort_order": 1},
            {"key": "wall_oven_mw_cooktop", "label": "Wall Oven/Microwave and Cooktop", "cost": 1500, "sort_order": 2},
            {"key": "range_wall_oven_mw", "label": "Range with added Wall Oven/Microwave Cabinet", "cost": 1200, "sort_order": 3},
            {"key": "rangetop_dbl_oven", "label": "Gas Rangetop with Double Oven/Microwave Cabinet", "cost": 2500, "sort_order": 4},
            {"key": "customer_hood", "label": "Customer to Supply Hood Vent Above Range", "cost": 0, "sort_order": 5},
        ]
        for d in data:
            ApplianceConfig.objects.update_or_create(key=d["key"], defaults=d)
        self.stdout.write(f'  Appliance Configs: {len(data)}')

    # ─────────────────────────────────────────
    # ISLAND ADDONS
    # ─────────────────────────────────────────
    def seed_island_addons(self):
        data = [
            {"key": "microwave", "label": "Microwave Shown in Island", "cost": 500},
            {"key": "sink", "label": "Sink Added to Island", "cost": 500},
            {"key": "sink_microwave", "label": "Sink and Microwave Shown in Island", "cost": 1000},
        ]
        for d in data:
            IslandAddon.objects.update_or_create(key=d["key"], defaults=d)
        self.stdout.write(f'  Island Addons: {len(data)}')

    # ─────────────────────────────────────────
    # UPGRADE CATALOG (all pills)
    # ─────────────────────────────────────────
    def seed_upgrade_catalog(self):
        # Helper to get or create category + section, then create items
        def cat(key, name, step, sort):
            obj, _ = UpgradeCategory.objects.update_or_create(key=key, defaults={"name": name, "step": step, "sort_order": sort})
            return obj

        def sec(category, name, sort):
            obj, _ = UpgradeSection.objects.update_or_create(category=category, name=name, defaults={"sort_order": sort})
            return obj

        def item(section, trade_key, **kw):
            trade = BudgetTrade.objects.get(key=trade_key) if trade_key else None
            kw["budget_trade"] = trade
            kw["section"] = section
            item_id = kw.pop("item_id")
            UpgradeItem.objects.update_or_create(item_id=item_id, defaults=kw)

        # ── PILL 1: DOCUSIGN ──
        c = cat("docusign", "Docusign Upgrades", "docusign", 1)

        s = sec(c, "Kitchen Sink Upgrades", 1)
        item(s, "plumbing", item_id="selFarmSink", label="Farm Sink", price=778, input_type="toggle", sort_order=1)

        s = sec(c, "Bathtub Upgrades", 2)
        item(s, "plumbing", item_id="selFreestandingTub", label="59 x 32 in Freestanding Bathtub with End Drain in White", price=248, input_type="qty", sort_order=1)
        item(s, "plumbing", item_id="selFloorMount", label="Floor Mount", price=475, input_type="qty", sort_order=2)

        s = sec(c, "Ceiling Fan Upgrades", 3)
        item(s, "lighting", item_id="selCeilingFan60", label='60" Ceiling Fans', price=141, input_type="qty", sort_order=1)

        s = sec(c, "Fireplace Upgrades", 4)
        item(s, "fireplaces", item_id="selEL42", label="EL42", price=5500, input_type="qty", sort_order=1)
        item(s, "fireplaces", item_id="selBIR42B", label="BIR42-B", price=10200, input_type="qty", sort_order=2)
        item(s, "fireplaces", item_id="sel18OCT", label="18OCT", price=7000, input_type="qty", sort_order=3)
        item(s, "fireplaces", item_id="selNorthStarC", label="NorthStar-C — Heat & Glo", price=11300, input_type="qty", sort_order=4)
        item(s, "fireplaces", item_id="selBUF36T", label="BUF36-T", price=4500, input_type="qty", sort_order=5)
        item(s, "fireplaces", item_id="selBUF42T", label="BUF42-T", price=5500, input_type="qty", sort_order=6)

        s = sec(c, "Water Heater Upgrades", 5)
        item(s, "plumbing", item_id="selWH40Gal", label="40-Gal Gas Water Heater", price=1039, input_type="toggle", sort_order=1)
        item(s, "plumbing", item_id="selWHTanklessNP", label="Tankless Water Heater (No Pump)", price=2048, input_type="toggle", sort_order=2, is_split_budget=True, adds_fixture_points=1)
        item(s, "plumbing", item_id="selWHTanklessWP", label="Tankless Water Heater (With Pump)", price=2411, input_type="toggle", sort_order=3, is_split_budget=True, adds_fixture_points=1)

        s = sec(c, "Utilities", 6)
        item(s, "plumbing", item_id="selWaterLF", label="Water", price=12, input_type="lf", unit="LF", sort_order=1)
        item(s, "plumbing", item_id="selSewerLF", label="Sewer", price=20, input_type="lf", unit="LF", sort_order=2)

        s = sec(c, "Gas Type", 7)
        # Gas type is informational — no items with costs, handled by Job.gas_type field

        s = sec(c, "Appliance Selection", 8)
        item(s, "plumbing", item_id="selAppStove", label="Stove", price=1000, input_type="toggle", sort_order=1)
        item(s, "plumbing", item_id="selAppDryer", label="Dryer", price=1000, input_type="toggle", sort_order=2)
        item(s, "plumbing", item_id="selAppWH", label="Water Heater", price=1000, input_type="toggle", sort_order=3)
        item(s, "plumbing", item_id="selAppOther", label="Other", price=1000, input_type="toggle", sort_order=4)

        s = sec(c, "Electrical Upgrades", 9)
        item(s, "electrical", item_id="selElec200OH", label="200 AMP Overhead Connection", price=2500, input_type="toggle", sort_order=1)
        item(s, "electrical", item_id="selElec200UG", label="200 AMP Underground Connection", price=5000, input_type="toggle", sort_order=2)
        item(s, "electrical", item_id="selElec400UG", label="400 AMP Underground Connection", price=8000, input_type="toggle", sort_order=3)
        item(s, "electrical", item_id="selJunctionBox", label="Interior Junction Box", price=500, input_type="qty", sort_order=4)

        # ── PILL 2: ELECTRICAL ──
        c = cat("electrical", "Electrical", "electrical", 2)

        s = sec(c, "Electrical Service", 1)
        item(s, "electrical", item_id="miniSplit", label="Mini Split", price=3200, input_type="toggle", sort_order=1)

        s = sec(c, "HVAC Upgrades", 2)
        item(s, "hvac", item_id="hvacTon", label="HVAC Upgrade ($750/ton + Gas Line $1,039)", price=750, input_type="qty", sort_order=1, has_base_addon=True, base_addon_amount=1039)

        s = sec(c, "Lighting", 3)
        item(s, "electrical", item_id="canLight", label="Can Lights", price=250, input_type="qty", sort_order=1)
        item(s, "electrical", item_id="floorLight", label="Floor Lights", price=529, input_type="qty", sort_order=2)

        s = sec(c, "Outlets & Technology", 4)
        item(s, "electrical", item_id="out220", label="220V Outlet", price=1227, input_type="qty", sort_order=1)
        item(s, "electrical", item_id="outRV", label="50-Amp RV Outlet", price=519, input_type="qty", sort_order=2)
        item(s, "electrical", item_id="outFloor", label="Floor Outlet", price=455, input_type="qty", sort_order=3)
        item(s, "electrical", item_id="outExtra", label="Extra Outlet", price=155, input_type="qty", sort_order=4)
        item(s, "electrical", item_id="outIsland", label="Power to Island", price=155, input_type="qty", sort_order=5)
        item(s, "electrical", item_id="usbc", label="USB-C Outlets", price=55, input_type="qty", sort_order=6)
        item(s, "electrical", item_id="mudBox", label="Mud Box", price=250, input_type="qty", sort_order=7)
        item(s, "electrical", item_id="dimmer", label="Dimmer Switch", price=95, input_type="qty", sort_order=8)
        item(s, "electrical", item_id="cat6", label="Cat 6 Data Drops", price=525, input_type="qty", sort_order=9)

        s = sec(c, "Junction Boxes", 5)
        item(s, "electrical", item_id="jbExt", label="Junction Box — Exterior", price=630, input_type="qty", sort_order=1)
        item(s, "electrical", item_id="jbMetal", label="Junction Box — Metal Ceiling / T&G", price=355, input_type="qty", sort_order=2)

        s = sec(c, "Finish Electrical", 6)
        item(s, "electrical", item_id="fanRemote", label="Fan Remote", price=75, input_type="qty", sort_order=1)
        item(s, "electrical", item_id="fanDimmer", label="Fan Dimmer", price=95, input_type="qty", sort_order=2)

        # ── PILL 3: PLUMBING ──
        c = cat("plumbing", "Plumbing", "plumbing", 3)

        s = sec(c, "Tile & Shower", 1)
        item(s, "tile", item_id="tileShowerSF", label="Tile Shower — Custom SF — Cust. Supplies Tile", price=50, input_type="sf", unit="SF", sort_order=1)
        item(s, "tile", item_id="tileFloorSF", label="Tile Floors — Custom SF — Cust. Supplies Tile", price=30, input_type="sf", unit="SF", sort_order=2)
        item(s, "tile", item_id="showerAcrylic", label="Std 3x5 Tile Shower — Acrylic Base", price=3000, input_type="toggle", sort_order=3)
        item(s, "tile", item_id="showerTile", label="Std 3x5 Tile Shower — Tile Floor", price=3200, input_type="toggle", sort_order=4)
        item(s, "tile", item_id="showerBench", label="Tile Shower Bench", price=484, input_type="toggle", sort_order=5)
        item(s, "tile", item_id="showerNiche", label="Tile Shower Niche", price=459, input_type="toggle", sort_order=6)

        s = sec(c, "Plumbing Stubs & Add-Ons", 2)
        item(s, "plumbing", item_id="freeTub", label="Freestanding Tub & Faucet", price=3876, input_type="qty", sort_order=1, adds_fixture_points=1)
        item(s, "plumbing", item_id="sinkStub", label="Additional Sink Stub", price=800, input_type="qty", sort_order=2, adds_fixture_points=1)
        item(s, "plumbing", item_id="iceLine", label="Ice Machine Line", price=800, input_type="qty", sort_order=3, adds_fixture_points=0.5)
        item(s, "plumbing", item_id="dogWash", label="Dog Wash Drain", price=1000, input_type="qty", sort_order=4, adds_fixture_points=1)
        item(s, "plumbing", item_id="garageStub", label="Garage Stub", price=1550, input_type="qty", sort_order=5, adds_fixture_points=2)
        item(s, "plumbing", item_id="addSpigot", label="Additional Spigots — 2 Included Standard", price=400, input_type="qty", sort_order=6)
        item(s, "plumbing", item_id="gasLine", label="Gas Line per Fixture", price=1039, input_type="qty", sort_order=7)
        item(s, "plumbing", item_id="floorDrain", label="Floor Drain — Must Show in Blueprints", price=1500, input_type="qty", sort_order=8, adds_fixture_points=1)
        item(s, "plumbing", item_id="potFiller", label="Pot Filler — Install Only", price=450, input_type="toggle", sort_order=9, adds_fixture_points=0.5)

        s = sec(c, "Bath Accessories", 3)
        item(s, "plumbing", item_id="div10", label="Division 10 Install — Mirrors & Accessories — Cust. Supplies / No Warranty", price=1600, input_type="toggle", sort_order=1)
        item(s, "plumbing", item_id="grabBar", label="ADA Grab Bars — Structural Support & Install w/ Warranty", price=1000, input_type="qty", sort_order=2)

        # ── PILL 4: INTERIOR TRIM & FLOORING ──
        c = cat("trim", "Interior Trim & Flooring", "trim", 4)

        s = sec(c, "Wall & Ceiling Finishes", 1)
        item(s, "trim", item_id="vgroove", label="1x6 V-Groove / T&G Ceiling", price=2.25, input_type="sf", unit="SF", sort_order=1)
        item(s, "trim", item_id="shiplap", label="Shiplap — Primed", price=8, input_type="sf", unit="SF", sort_order=2)
        item(s, "trim", item_id="beams", label="Faux Beams", price=50, input_type="lf", unit="LF", sort_order=3)
        item(s, "trim", item_id="backsplash", label="Kitchen Backsplash — Cust. Supplies", price=80, input_type="sf", unit="SF", sort_order=4)
        item(s, "trim", item_id="underCabLight", label="Under Cabinet Lighting", price=225, input_type="qty", sort_order=5)

        s = sec(c, "Trim & Windows", 2)
        item(s, "trim", item_id="winTrim", label="Window Trim", price=1, input_type="sf", unit="SF", sort_order=1)
        item(s, "trim", item_id="trim1x4", label="Trim 1x4", price=75, input_type="qty", sort_order=2)
        item(s, "trim", item_id="trim325", label='Trim 3.25"', price=60, input_type="qty", sort_order=3)

        s = sec(c, "Doors & Stairs", 3)
        item(s, "trim", item_id="stairs", label="Finished Stairs", price=1800, input_type="toggle", sort_order=1)
        item(s, "trim", item_id="pineDoor", label="Pine Doors", price=400, input_type="qty", sort_order=2)
        item(s, "trim", item_id="door36", label='36" Doors Upgrade', price=100, input_type="qty", sort_order=3)
        item(s, "trim", item_id="barnDoor", label="Barn Doors — Install Only — Cust. Supplies Door", price=275, input_type="qty", sort_order=4)
        item(s, "trim", item_id="pocketDoor", label="Pocket Doors", price=649, input_type="qty", sort_order=5)
        item(s, "trim", item_id="doggyDoor", label="Doggy Door", price=655, input_type="toggle", sort_order=6)

        s = sec(c, "Flooring Upgrades", 4)
        item(s, "flooring", item_id="woodSupply", label="Wood Floors — Supply & Install", price=8.5, input_type="sf", unit="SF", sort_order=1)
        item(s, "flooring", item_id="woodInstall", label="Wood Floors — Install Only", price=5.5, input_type="sf", unit="SF", sort_order=2)
        item(s, "flooring", item_id="carpet", label="Carpet", price=3.5, input_type="sf", unit="SF", sort_order=3)
        item(s, "flooring", item_id="radiant", label="Radiant Flooring — 1 Zone", price=13.2, input_type="sf", unit="SF", sort_order=4)
        item(s, "trim", item_id="closetShelf", label="Closet Shelving", price=80, input_type="lf", unit="LF", sort_order=5)

        # Concrete Floor Finishes section intentionally empty — uses JobConcreteFinishLine custom rows

        self.stdout.write(f'  Upgrade Catalog: seeded all categories, sections, and items')

    # ----------------------------------------------------------------
    # DEMO JOBS (manager/owner dashboards)
    # ----------------------------------------------------------------
    def seed_demo_jobs(self):
        # Wipe every existing Job - cascades to JobDraw, JobTradeBudget,
        # JobBudgetLineItem, JobChangeOrder, QbCustomerMap, QbInvoiceEvent.
        # The 30 contracts below become the entire demo dataset.
        deleted, _ = Job.objects.all().delete()
        self.stdout.write(f"  Deleted prior jobs (and cascaded children): {deleted} rows")

        branches = {b.key: b for b in Branch.objects.all()}
        models_by_name = {m.name: m for m in FloorPlanModel.objects.all()}

        # Deterministic so reruns produce identical demo data.
        rng = random.Random(20260504)

        seeded = 0
        for spec in _DEMO_CONTRACT_SPECS:
            branch = branches.get(spec["branch"]) or next(iter(branches.values()), None)
            floor_plan = models_by_name.get(spec["model"])
            if floor_plan is None:
                self.stdout.write(self.style.WARNING(
                    f"  Skipped {spec['on']} ({spec['name']}): model {spec['model']!r} not seeded."
                ))
                continue
            self._build_demo_contract(spec, branch, floor_plan, rng)
            seeded += 1

        self.stdout.write(f"  Demo Jobs: {seeded} (with trade budgets, line items, draws, and bills)")

    # ----------------------------------------------------------------
    # Internal helpers for demo contract generation
    # ----------------------------------------------------------------
    def _build_demo_contract(self, spec, branch, floor_plan, rng):
        bucket = spec["bucket"]
        phase = spec["phase"]

        p10_material = Decimal(floor_plan.p10_material or 0)
        int_contract = Decimal(floor_plan.int_contract or 0)
        if int_contract <= 0:
            int_contract = Decimal("180000.00")
        contract_total = (p10_material + int_contract).quantize(Decimal("1"))
        adjusted_int = int_contract

        # Total trade budget ~ 48% of contract total - matches the legacy
        # demo ratio of vendor/labor cost vs customer-facing contract price.
        trade_budget_total = int(contract_total * Decimal("0.48"))
        trade_rows = _allocate_trade_budgets(trade_budget_total)

        completed_draw, in_progress_factor, base_efficiency = _PHASE_PROGRESS[bucket]

        draws = _build_draw_schedule(contract_total, bucket, rng)

        created_at = _job_created_at_for(bucket, draws, rng)
        # Sales-in-progress contracts haven't been DocuSigned yet — leaving
        # sales_closed_at null is what tags them as still-on-the-sales-side
        # (vs. handed off to PM).
        if bucket == "sales_in_progress":
            sales_closed_at = None
        else:
            sales_closed_at = created_at + timedelta(days=rng.randint(7, 21))

        trade_actuals = []
        for trade_name, budgeted, sort_order in trade_rows:
            draw_number = _DEMO_TRADE_DRAW.get(
                trade_name,
                SEED_TRADE_LINE_TEMPLATES.get(trade_name, (None, None, None, 5))[3],
            )
            actual = _compute_trade_actual(
                bucket, budgeted, draw_number, completed_draw,
                in_progress_factor, base_efficiency, rng,
            )
            trade_actuals.append((trade_name, budgeted, actual, sort_order, draw_number))

        budget_spent = sum(t[2] for t in trade_actuals)
        collected = sum(int(d["amount"]) for d in draws if d["status"] == "p")
        current_draw_amount = next(
            (int(d["amount"]) for d in draws if d["status"] == "c"), 0
        )

        job = Job.objects.create(
            order_number=spec["on"],
            customer_name=spec["name"],
            customer_addr=spec["addr"],
            sales_rep=spec.get("sales_rep", "Danny Robinson"),
            branch=branch,
            floor_plan=floor_plan,
            job_mode="turnkey",
            p10_material=p10_material,
            adjusted_int_contract=adjusted_int,
            current_phase=phase,
            budget_total_amount=Decimal(str(trade_budget_total)),
            budget_spent_amount=Decimal(str(budget_spent)),
            collected_amount=Decimal(str(collected)),
            current_draw_amount=Decimal(str(current_draw_amount)),
            customer_email=_demo_email_for(spec["name"]),
            customer_phone=_demo_phone(rng),
            sales_closed_at=sales_closed_at,
        )
        # Override created_at (auto_now_add) so dashboards order by build age.
        Job.objects.filter(pk=job.pk).update(created_at=created_at)

        for trade_name, budgeted, actual, sort_order, _ in trade_actuals:
            JobTradeBudget.objects.create(
                job=job,
                trade_name=trade_name,
                budgeted=Decimal(str(budgeted)),
                actual=Decimal(str(actual)),
                sort_order=sort_order,
            )

        # One JobBudgetLineItem per trade. Trades with actual > 0 get
        # synthetic qb_bill_refs so the manager Bills tab shows realistic
        # invoice rows. Trades with no actual leave qb_bill_refs empty so
        # the same view renders them as Pending placeholders.
        for idx, (trade_name, budgeted, actual, sort_order, draw_number) in enumerate(trade_actuals):
            tmpl = SEED_TRADE_LINE_TEMPLATES.get(trade_name)
            if tmpl is None:
                title, bt_code, qb_account, _draw = trade_name, trade_name, trade_name, draw_number
            else:
                title, bt_code, qb_account, _draw = tmpl

            qb_bill_refs, last_paid_at = _build_bill_refs(
                trade_name, actual, branch, created_at, rng,
            )

            JobBudgetLineItem.objects.create(
                job=job,
                po_number=str(idx + 1).zfill(4),
                title=title,
                bt_code=bt_code,
                qb_account_name=qb_account,
                trade_bucket=trade_name,
                draw_number=draw_number,
                budgeted=Decimal(str(budgeted)),
                actual=Decimal(str(actual)),
                qb_bill_refs=qb_bill_refs,
                last_paid_at=last_paid_at,
                sort_order=sort_order,
            )

        for d in draws:
            JobDraw.objects.create(
                job=job,
                draw_number=d["draw_number"],
                label=d["label"],
                amount=Decimal(str(d["amount"])),
                status=d["status"],
                paid_date=d["paid_date"],
            )


# =================================================================
# Demo contract specs + helpers
# =================================================================
#
# 35 named contracts spanning the full sales-to-close lifecycle. Order
# numbers are 6-digit (100001..100035) to match how the office numbers
# real builds. Buckets:
#   sales_in_progress (5) - sales-side; sales_closed_at is null (not yet
#                           DocuSigned, so the PM dashboard never sees them)
#   awaiting_deposit  (2) - sales-closed; deposit draw is Current
#   awaiting_loan     (4) - deposit paid; loan-close draw is Current
#   active_framing    (3) - PM handoff; on the 2nd Home Draw (Concrete)
#   active_roughin    (4) - draws 0-3 paid; 4th Home Draw current
#   active_interior   (4) - draws 0-4 paid; 5th Home Draw current
#   active_punch      (3) - draws 0-5 paid; 6th Home Draw current
#   active_final      (3) - 6th Home Draw invoiced, awaiting payment
#   closed_under      (1) - finished under budget (clear margin)
#   closed_over       (1) - finished over budget (clear overrun)
#   closed_normal     (5) - finished within +/-5% of budget

_DEMO_CONTRACT_SPECS = [
    # Sales side - in progress (sales rep still working, not handed off)
    {"on": "100001", "name": "Erica Pittman",     "addr": "215 Persimmon Hollow, Summertown, TN 38483",
     "model": "PETTUS",           "branch": "summertown",  "phase": "estimate", "bucket": "sales_in_progress"},
    {"on": "100002", "name": "Trevor Russo",      "addr": "78 Lakeside Trail, Hayden, AL 35079",
     "model": "CAJUN",            "branch": "hayden_al",   "phase": "estimate", "bucket": "sales_in_progress"},
    {"on": "100003", "name": "Natalie Ortega",    "addr": "994 Old Mill Rd, Morristown, TN 37814",
     "model": "THE HADLEY",       "branch": "morristown",  "phase": "estimate", "bucket": "sales_in_progress"},
    {"on": "100004", "name": "Sebastian Reyna",   "addr": "631 Stillwater Dr, Hopkinsville, KY 42240",
     "model": "BUFFALO RUN",      "branch": "hopkinsville","phase": "estimate", "bucket": "sales_in_progress"},
    {"on": "100005", "name": "Marisa Hollis",     "addr": "1422 Crystal Brook Ln, Summertown, TN 38483",
     "model": "WHISPERING PINES", "branch": "summertown",  "phase": "estimate", "bucket": "sales_in_progress"},

    # Sales-closed but pre-loan-close (deposit/loan draws still pending)
    {"on": "100006", "name": "Kevin Anderson",    "addr": "412 Bluff Run Rd, Hayden, AL 35079",
     "model": "WHISPERING PINES", "branch": "hayden_al",   "phase": "estimate", "bucket": "awaiting_deposit"},
    {"on": "100007", "name": "Rachel Bennett",    "addr": "88 Sycamore Ridge, Summertown, TN 38483",
     "model": "THE BERKLEY",      "branch": "summertown",  "phase": "estimate", "bucket": "awaiting_deposit"},
    {"on": "100008", "name": "Sam Carter",        "addr": "1207 Crestview Ln, Morristown, TN 37814",
     "model": "CAJUN",            "branch": "morristown",  "phase": "estimate", "bucket": "awaiting_loan"},
    {"on": "100009", "name": "Megan Davis",       "addr": "523 Pine Meadow Way, Hopkinsville, KY 42240",
     "model": "BUFFALO RUN",      "branch": "hopkinsville","phase": "estimate", "bucket": "awaiting_loan"},
    {"on": "100010", "name": "Tyler Edwards",     "addr": "76 Oakridge Dr, Hayden, AL 35079",
     "model": "HUNTLEY 2.0",      "branch": "hayden_al",   "phase": "estimate", "bucket": "awaiting_loan"},
    {"on": "100011", "name": "Amanda Foster",     "addr": "915 Whitetail Trace, Summertown, TN 38483",
     "model": "COTTONWOOD BEND",  "branch": "summertown",  "phase": "estimate", "bucket": "awaiting_loan"},

    # PM side - just handed off (on the 2nd Home Draw - Concrete)
    {"on": "100012", "name": "Marcus Garcia",     "addr": "330 Maple Hollow, Summertown, TN 38483",
     "model": "MAPLE GROVE",      "branch": "summertown",  "phase": "framing",  "bucket": "active_framing"},
    {"on": "100013", "name": "Jordan Hayes",      "addr": "612 Hickory Pass, Morristown, TN 37814",
     "model": "PETTUS",           "branch": "morristown",  "phase": "framing",  "bucket": "active_framing"},
    {"on": "100014", "name": "Brooke Iverson",    "addr": "147 Cedar Bluff Dr, Hopkinsville, KY 42240",
     "model": "NORTHVIEW LODGE",  "branch": "hopkinsville","phase": "framing",  "bucket": "active_framing"},

    # PM side - rough-in stage
    {"on": "100015", "name": "Wesley Jackson",    "addr": "508 Roebuck Rd, Hayden, AL 35079",
     "model": "CAJUN",            "branch": "hayden_al",   "phase": "roughin",  "bucket": "active_roughin"},
    {"on": "100016", "name": "Jessica Kim",       "addr": "29 Briar Patch Ln, Summertown, TN 38483",
     "model": "RIVERVIEW COTTAGE","branch": "summertown",  "phase": "roughin",  "bucket": "active_roughin"},
    {"on": "100017", "name": "Brandon Lawson",    "addr": "844 Tanglewood Ct, Morristown, TN 37814",
     "model": "BUFFALO RUN",      "branch": "morristown",  "phase": "roughin",  "bucket": "active_roughin"},
    {"on": "100018", "name": "Olivia Mitchell",   "addr": "1130 Stoneybrook Dr, Hopkinsville, KY 42240",
     "model": "HUNTLEY",          "branch": "hopkinsville","phase": "roughin",  "bucket": "active_roughin"},

    # PM side - interior finishes
    {"on": "100019", "name": "Caleb Nelson",      "addr": "67 Magnolia Bend, Hayden, AL 35079",
     "model": "MINI PETTUS",      "branch": "hayden_al",   "phase": "interior", "bucket": "active_interior"},
    {"on": "100020", "name": "Sophia Owens",      "addr": "418 Wildwood Trail, Summertown, TN 38483",
     "model": "MARTIN LODGE",     "branch": "summertown",  "phase": "interior", "bucket": "active_interior"},
    {"on": "100021", "name": "Rohan Patel",       "addr": "203 River Glen Rd, Morristown, TN 37814",
     "model": "COTTONWOOD BEND",  "branch": "morristown",  "phase": "interior", "bucket": "active_interior"},
    {"on": "100022", "name": "Shelby Quinn",      "addr": "925 Greenbriar Ave, Hopkinsville, KY 42240",
     "model": "PETTUS",           "branch": "hopkinsville","phase": "interior", "bucket": "active_interior"},

    # PM side - punch
    {"on": "100023", "name": "Diego Reyes",       "addr": "311 Hidden Springs Ln, Hayden, AL 35079",
     "model": "CAJUN",            "branch": "hayden_al",   "phase": "punch",    "bucket": "active_punch"},
    {"on": "100024", "name": "Chloe Stewart",     "addr": "1502 Dogwood Way, Summertown, TN 38483",
     "model": "THE HADLEY",       "branch": "summertown",  "phase": "punch",    "bucket": "active_punch"},
    {"on": "100025", "name": "Logan Thompson",    "addr": "740 Falcon Ridge, Morristown, TN 37814",
     "model": "WESTVIEW MANOR",   "branch": "morristown",  "phase": "punch",    "bucket": "active_punch"},

    # PM side - final draw invoiced, awaiting payment
    {"on": "100026", "name": "Madison Underwood", "addr": "85 Sunrise Ct, Hopkinsville, KY 42240",
     "model": "BUFFALO RUN",      "branch": "hopkinsville","phase": "final",    "bucket": "active_final"},
    {"on": "100027", "name": "Tristan Vance",     "addr": "1245 Persimmon Trail, Hayden, AL 35079",
     "model": "PETTUS",           "branch": "hayden_al",   "phase": "final",    "bucket": "active_final"},
    {"on": "100028", "name": "Hannah Walters",    "addr": "356 Quail Hollow Dr, Summertown, TN 38483",
     "model": "NORTHVIEW LODGE",  "branch": "summertown",  "phase": "final",    "bucket": "active_final"},

    # Closed: under budget (1) and over budget (1) for the executive view
    {"on": "100029", "name": "Daniel Xu",         "addr": "112 Tall Pines Rd, Morristown, TN 37814",
     "model": "CAJUN",            "branch": "morristown",  "phase": "closed",   "bucket": "closed_under"},
    {"on": "100030", "name": "Audrey Young",      "addr": "967 Bellridge Way, Hopkinsville, KY 42240",
     "model": "MINI PETTUS",      "branch": "hopkinsville","phase": "closed",   "bucket": "closed_over"},

    # Closed: routine completions
    {"on": "100031", "name": "Brett Zimmerman",   "addr": "224 Westshore Blvd, Hayden, AL 35079",
     "model": "THE BERKLEY",      "branch": "hayden_al",   "phase": "closed",   "bucket": "closed_normal"},
    {"on": "100032", "name": "Kayla Adams",       "addr": "1040 Foxglove Ln, Summertown, TN 38483",
     "model": "HUNTLEY 2.0",      "branch": "summertown",  "phase": "closed",   "bucket": "closed_normal"},
    {"on": "100033", "name": "Nathan Brooks",     "addr": "62 Spring Branch Rd, Morristown, TN 37814",
     "model": "PETTUS",           "branch": "morristown",  "phase": "closed",   "bucket": "closed_normal"},
    {"on": "100034", "name": "Vanessa Coleman",   "addr": "488 Birchwood Park, Hopkinsville, KY 42240",
     "model": "COTTONWOOD BEND",  "branch": "hopkinsville","phase": "closed",   "bucket": "closed_normal"},
    {"on": "100035", "name": "Eric Dawson",       "addr": "1311 Honeysuckle Trail, Hayden, AL 35079",
     "model": "MAPLE GROVE",      "branch": "hayden_al",   "phase": "closed",   "bucket": "closed_normal"},
]


# Trade allocation as a percentage of total trade budget, mirroring the
# split used by the original DEMO-1001/2/3 contracts.
_TRADE_BUDGET_MIX = [
    ("Framing",     1, 0.181),
    ("Roofing",     2, 0.059),
    ("Siding",      3, 0.035),
    ("Ext Trim",    4, 0.044),
    ("D&W",         5, 0.021),
    ("Cabinets",    6, 0.160),
    ("Flooring",    7, 0.029),
    ("Drywall",     8, 0.066),
    ("Paint",       9, 0.049),
    ("Trim",       10, 0.054),
    ("Electrical", 11, 0.085),
    ("Plumbing",   12, 0.052),
    ("Insulation", 13, 0.047),
    ("HVAC",       14, 0.087),
    ("General",    15, 0.039),
]


# Trade name -> draw number when that trade is principally billed.
# Mirrors how SEED_TRADE_LINE_TEMPLATES assigns draws for interior trades,
# and adds explicit values for exterior trades (Framing/Roofing/Siding/etc.)
# that don't appear in the interior-focused template.
_DEMO_TRADE_DRAW = {
    "Framing":     3,
    "Roofing":     3,
    "Siding":      3,
    "Ext Trim":    3,
    "D&W":         3,
    "Cabinets":    5,
    "Flooring":    5,
    "Drywall":     5,
    "Paint":       5,
    "Trim":        5,
    "Electrical":  4,
    "Plumbing":    4,
    "Insulation":  4,
    "HVAC":        4,
    "General":     6,
}


# Phase progress: (completed_draw, in_progress_factor, base_efficiency)
_PHASE_PROGRESS = {
    "sales_in_progress": (0, 0.00, 1.00),
    "awaiting_deposit":  (0, 0.00, 1.00),
    "awaiting_loan":     (0, 0.00, 1.00),
    # PM has just been handed the build - 2nd Home Draw (Concrete) is the
    # current draw. Exterior trades (Framing/Roofing/Siding/Ext Trim/D&W,
    # draw_number=3) are early-in-progress.
    "active_framing":    (2, 0.30, 1.00),
    "active_roughin":    (4, 0.55, 1.00),
    "active_interior":   (5, 0.70, 1.00),
    "active_punch":      (6, 0.90, 1.00),
    "active_final":      (6, 1.00, 1.00),
    "closed_normal":     (6, 1.00, 1.00),
    "closed_under":      (6, 1.00, 0.88),
    "closed_over":       (6, 1.00, 1.18),
}


_VENDORS_BY_TRADE = {
    "Framing":     ["Sturdy Build Framing", "Pioneer Framing Co"],
    "Roofing":     ["Tennessee Roofing Group", "Apex Metal Roofs"],
    "Siding":      ["Southern Siding LLC", "Heritage Exteriors"],
    "Ext Trim":    ["Heritage Exteriors", "BoardWright Trim"],
    "D&W":         ["BuildersFirstSource", "Doors & More"],
    "Cabinets":    ["Stone Hill Cabinets", "Tennessee Custom Cabinetry"],
    "Flooring":    ["Hardwood Source", "Floor Express"],
    "Drywall":     ["South Coast Drywall", "BuildPro Materials"],
    "Paint":       ["Crisp Coat Painting", "Pro Painters Inc"],
    "Trim":        ["Heartwood Trim Co", "Doors & More"],
    "Electrical":  ["Voltage Electric", "Bright Spark Electric"],
    "Plumbing":    ["Crystal Clear Plumbing", "Mainline Plumbing"],
    "Insulation":  ["ThermaSeal Insulation", "Foam Pros"],
    "HVAC":        ["Cool Breeze HVAC", "Climate Control Inc"],
    "General":     ["County Permit Office", "City Inspections"],
}


_STATUS_PATTERN_BY_BUCKET = {
    "sales_in_progress": ["x", "x", "x", "x", "x", "x", "x"],  # not yet handed off
    "awaiting_deposit":  ["c", "x", "x", "x", "x", "x", "x"],
    "awaiting_loan":     ["p", "c", "x", "x", "x", "x", "x"],
    # 2nd Home Draw (Concrete) is the first draw the PM owns - deposit and
    # 1st Home Draw (Loan Close) are paid before handoff.
    "active_framing":    ["p", "p", "c", "x", "x", "x", "x"],
    "active_roughin":    ["p", "p", "p", "p", "c", "x", "x"],
    "active_interior":   ["p", "p", "p", "p", "p", "c", "x"],
    "active_punch":      ["p", "p", "p", "p", "p", "p", "c"],
    "active_final":      ["p", "p", "p", "p", "p", "p", "i"],
    "closed_normal":     ["p", "p", "p", "p", "p", "p", "p"],
    "closed_under":      ["p", "p", "p", "p", "p", "p", "p"],
    "closed_over":       ["p", "p", "p", "p", "p", "p", "p"],
}


def _allocate_trade_budgets(total):
    rows = []
    running = 0
    for trade_name, sort_order, pct in _TRADE_BUDGET_MIX[:-1]:
        amt = int(round(total * pct))
        rows.append((trade_name, amt, sort_order))
        running += amt
    last_name, last_sort, _ = _TRADE_BUDGET_MIX[-1]
    rows.append((last_name, max(0, total - running), last_sort))
    return rows


def _build_draw_schedule(contract_total, bucket, rng):
    """Build a 7-row draw schedule (Deposit + 6 progress draws) sized off
    the contract total. Status flags follow the bucket lifecycle stage."""
    deposit = 2500
    remaining = int(contract_total) - deposit
    pct = [0.27, 0.10, 0.15, 0.20, 0.20, 0.08]
    amounts = [int(round(remaining * p)) for p in pct]
    amounts[-1] = remaining - sum(amounts[:-1])

    # Match the wizard's "Nth Home Draw (Phase)" format - qb_invoice
    # `_phase_label_for` extracts the parenthetical for QB invoice
    # descriptions, so this format keeps the QB push path readable too.
    labels = [
        "Deposit",
        "1st Home Draw (Loan Close)",
        "2nd Home Draw (Concrete)",
        "3rd Home Draw (Framing Completion)",
        "4th Home Draw (Rough-Ins)",
        "5th Home Draw (Finishes)",
        "6th Home Draw (Final)",
    ]
    statuses = _STATUS_PATTERN_BY_BUCKET[bucket]

    today = date.today()
    base = today - timedelta(days=rng.randint(150, 240))
    paid_dates = []
    cursor = base
    for _ in range(7):
        cursor += timedelta(days=rng.randint(18, 32))
        paid_dates.append(cursor)

    schedule = []
    for i in range(7):
        amount = deposit if i == 0 else amounts[i - 1]
        status = statuses[i]
        d = paid_dates[i] if status == "p" else None
        schedule.append({
            "draw_number": i,
            "label": labels[i],
            "amount": amount,
            "status": status,
            "paid_date": d.strftime("%b %d") if d else "",
            "_paid_date_full": d,
        })
    return schedule


def _compute_trade_actual(bucket, budgeted, draw_number, completed_draw,
                           in_progress_factor, base_efficiency, rng):
    """Pick a sensible actual-spend amount given the contract lifecycle."""
    if completed_draw == 0 and in_progress_factor == 0:
        return 0  # awaiting_* — nothing on the cost side yet
    if draw_number > completed_draw + 1:
        return 0
    if draw_number == completed_draw + 1:
        ratio = in_progress_factor * rng.uniform(0.85, 1.05)
        return int(round(budgeted * ratio))
    if bucket == "closed_normal":
        eff = rng.uniform(0.94, 1.05)
    elif bucket == "closed_under":
        eff = rng.uniform(0.82, 0.92)
    elif bucket == "closed_over":
        eff = rng.uniform(1.10, 1.28)
    else:
        eff = base_efficiency * rng.uniform(0.95, 1.04)
    return int(round(budgeted * eff))


def _build_bill_refs(trade_name, actual, branch, job_created_at, rng):
    """Synthesize 1-2 QB Bill refs that sum to `actual`."""
    if actual <= 0:
        return [], None
    vendors = _VENDORS_BY_TRADE.get(trade_name, [f"{trade_name} Vendor"])
    bill_count = 1 if actual < 6000 else rng.randint(1, 2)
    if bill_count == 1:
        amounts = [actual]
    else:
        first = int(round(actual * rng.uniform(0.30, 0.55)))
        amounts = [first, actual - first]

    refs = []
    last_paid = None
    base_doc = rng.randint(20100, 20999)
    paid_from_id = (branch.qb_bank_account_id if branch else "") or ""
    paid_from_name = (branch.qb_bank_account_name if branch else "") or ""
    for i, amt in enumerate(amounts):
        bill_id = str(rng.randint(1_000_000_000, 9_999_999_999))
        line_id = str(rng.randint(1, 99))
        days_ago = rng.randint(7, 110)
        txn_dt = (timezone.now() - timedelta(days=days_ago)).date()
        if txn_dt < job_created_at.date():
            txn_dt = job_created_at.date() + timedelta(days=14 + i * 7)
        paid_at = timezone.now() - timedelta(days=max(1, days_ago - rng.randint(2, 10)))
        refs.append({
            "bill_id": bill_id,
            "line_id": line_id,
            "doc_number": f"INV-{base_doc + i}",
            "vendor": vendors[i % len(vendors)],
            "txn_date": txn_dt.strftime("%b %d, %Y"),
            "amount": float(amt),
            "paid_from_account_id": paid_from_id,
            "paid_from_account_name": paid_from_name,
        })
        if last_paid is None or paid_at > last_paid:
            last_paid = paid_at
    return refs, last_paid


def _job_created_at_for(bucket, draws, rng):
    """Pick a Job.created_at older for further-along contracts so the
    dashboard's `-created_at` ordering surfaces a believable mix."""
    today = timezone.now()
    paid_dates = [d.get("_paid_date_full") for d in draws if d.get("_paid_date_full")]
    if paid_dates:
        from datetime import datetime
        oldest = min(paid_dates)
        anchor = timezone.make_aware(
            datetime.combine(oldest, datetime.min.time())
        ) - timedelta(days=rng.randint(10, 30))
        return anchor
    days_back = {
        "awaiting_deposit": (3, 18),
        "awaiting_loan":    (10, 35),
    }.get(bucket, (60, 180))
    return today - timedelta(days=rng.randint(*days_back))


def _demo_email_for(name):
    parts = name.lower().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}.{parts[-1]}@example.com"
    return f"{parts[0]}@example.com"


def _demo_phone(rng):
    return f"({rng.randint(200, 989)}) {rng.randint(200, 989)}-{rng.randint(1000, 9999)}"
