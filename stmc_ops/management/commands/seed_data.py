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

from django.core.management.base import BaseCommand
from decimal import Decimal
from stmc_ops.models import (
    AppUser, Branch, BudgetTrade, BudgetTradeRate, FloorPlanModel, InteriorRateCard, ExteriorRateCard, Job,
    JobTradeBudget, JobDraw,
    UpgradeCategory, UpgradeSection, UpgradeItem, ApplianceConfig, IslandAddon,
)


# Wizard display options that are not model rows but still part of seeded config.
WIZARD_ROOF_AREA_NAMES = [
    "House Roof", "Main Roof", "Main House", "Front Porch", "Back Porch", "Porch Roof",
    "Porch & Garage", "Garage", "Garage Roof", "Carport", "Carport Roof", "Dormers",
    "Lean-To", "Bonus Room", "Side Entry", "Side Shed", "Custom",
]

WIZARD_ROOF_TYPES = [
    {"v": "metal", "l": "Metal"},
    {"v": "ss", "l": "Standing Seam"},
    {"v": "shingles", "l": "Shingles"},
]

WIZARD_CONC_TYPES = [
    {"v": "", "l": "None / Not Yet Selected"},
    {"v": "4fiber", "l": "4\" w/ Fiber"},
    {"v": "6fiber", "l": "6\" w/ Fiber"},
    {"v": "4mono", "l": "4\" Mono Footer & Fiber"},
    {"v": "6mono", "l": "6\" Mono Footer & Fiber"},
]

WIZARD_CUSTOM_TRADE_CATS = [
    {"v": "trim", "l": "Trim & Doors", "route": "trim", "hasSub": True},
    {"v": "flooring", "l": "Flooring", "route": "flooring", "hasSub": True},
    {"v": "drywall", "l": "Drywall", "route": "drywall", "hasSub": True},
    {"v": "paint", "l": "Paint", "route": "paint", "hasSub": True},
    {"v": "electrical", "l": "Electrical", "route": "electrical", "hasSub": True},
    {"v": "plumbing", "l": "Plumbing", "route": "plumbing", "hasSub": True},
    {"v": "insulation", "l": "Insulation", "route": "insulation", "hasSub": True},
    {"v": "hvac", "l": "HVAC", "route": "hvac", "hasSub": True},
    {"v": "cabinets", "l": "Cabinets", "route": "cabinets", "hasSub": False},
    {"v": "countertops", "l": "Countertops", "route": "countertops", "hasSub": False},
    {"v": "tile", "l": "Tile", "route": "tile", "hasSub": False},
    {"v": "concreteFinish", "l": "Concrete Finish", "route": "concreteFinish", "hasSub": False},
    {"v": "fireplaces", "l": "Fireplaces", "route": "fireplaces", "hasSub": False},
    {"v": "lighting", "l": "Lighting", "route": "lighting", "hasSub": False},
    {"v": "general", "l": "General / Other", "route": "general", "hasSub": False},
]

WIZARD_CONCRETE_FINISH_REFERENCE_PRICING = [
    {"l": "Joint Filler on Saw-Cut Joints", "r": "$3.00/SF"},
    {"l": "Grind & Seal - Solvent Base", "r": "$4.50/SF"},
    {"l": "Grind & Seal - Water Base", "r": "$4.25/SF"},
    {"l": "Exterior Clean & Seal", "r": "$3.75/SF"},
    {"l": "Polish Concrete", "r": "$5.50/SF"},
    {"l": "Flake Epoxy", "r": "$5.75/SF"},
    {"l": "Metallic Epoxy", "r": "$12.50/SF"},
    {"l": "Add Dye", "r": "+$0.75/SF"},
    {"l": "Travel Fee (75+ miles)", "r": "$350 flat"},
]


class Command(BaseCommand):
    help = 'Seed STMC reference data (branches, rate cards, trades, upgrades)'

    def handle(self, *args, **options):
        self.seed_users()
        self.seed_branches()
        self.seed_interior_rate_card()
        self.seed_exterior_rate_card()
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
                "email": "admin@stmc.com",
                "username": "admin@stmc.com",
                "name": "STMC Admin",
                "initials": "AD",
                "role": "admin",
                "title": "System Administrator",
                "sort_order": 0,
                "is_staff": True,
                "is_superuser": True,
                "password": "stmadmin",
            },
            {
                "email": "d.robinson@stmc.com",
                "username": "d.robinson@stmc.com",
                "name": "Derek Robinson",
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
            is_staff = row.pop("is_staff", False)
            is_superuser = row.pop("is_superuser", False)
            user, _ = AppUser.objects.update_or_create(
                email=row["email"], defaults=row
            )
            user.set_password(password)
            user.is_active = True
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
        self.stdout.write(f'  App Users: {len(data)}')

    # ─────────────────────────────────────────
    # BRANCHES
    # ─────────────────────────────────────────
    def seed_branches(self):
        data = [
            {"key": "summertown", "label": "Summertown Main", "conc_rate": 8, "default_miles": 0, "zone": 1},
            {"key": "hayden_al", "label": "Hayden, AL", "conc_rate": 8, "default_miles": 0, "zone": 1},
            {"key": "morristown", "label": "Morristown", "conc_rate": 9, "default_miles": 1, "zone": 2},
            {"key": "hopkinsville", "label": "Hopkinsville", "conc_rate": 9, "default_miles": 1, "zone": 3},
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

    # ─────────────────────────────────────────
    # EXTERIOR RATE CARD (P object — flattened)
    # ─────────────────────────────────────────
    def seed_exterior_rate_card(self):
        data = [
            # Sales (customer-facing)
            {"key": "sales_base", "category": "sales", "label": "Base Labor", "rate": 12, "unit": "SF", "miles_tier": ""},
            {"key": "sales_crawl", "category": "sales", "label": "Crawlspace Add", "rate": 3, "unit": "SF", "miles_tier": ""},
            {"key": "sales_ssAdd", "category": "sales", "label": "Standing Seam Add", "rate": 2, "unit": "SF", "miles_tier": ""},
            {"key": "sales_sidingAdd", "category": "sales", "label": "Siding Upgrade", "rate": 1.5, "unit": "SF", "miles_tier": ""},
            {"key": "sales_steepAdd", "category": "sales", "label": "Steep Pitch Add", "rate": 1.75, "unit": "SF", "miles_tier": ""},
            {"key": "sales_stoneW", "category": "sales", "label": "Stone (≤100mi)", "rate": 24, "unit": "SF", "miles_tier": "u"},
            {"key": "sales_stoneO", "category": "sales", "label": "Stone (>100mi)", "rate": 26, "unit": "SF", "miles_tier": "o"},
            {"key": "sales_stoneLift", "category": "sales", "label": "Stone Chimney/Roofline", "rate": 1500, "unit": "ea", "miles_tier": ""},
            {"key": "sales_tg", "category": "sales", "label": "T&G Porch Ceilings", "rate": 5, "unit": "SF", "miles_tier": ""},
            {"key": "sales_awning", "category": "sales", "label": "Timber Framed Awnings", "rate": 450, "unit": "ea", "miles_tier": ""},
            {"key": "sales_cupola", "category": "sales", "label": "Cupola Installation", "rate": 250, "unit": "ea", "miles_tier": ""},
            {"key": "sales_deck", "category": "sales", "label": "Deck", "rate": 5, "unit": "SF", "miles_tier": ""},
            {"key": "sales_bsmtWall", "category": "sales", "label": "Basement Wall", "rate": 10, "unit": "LF", "miles_tier": ""},
            # Contractor — Framing
            {"key": "ctr_fSlab_u", "category": "contractor", "label": "Framing Slab (under 100mi)", "rate": 5.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fSlab_o", "category": "contractor", "label": "Framing Slab (over 100mi)", "rate": 6, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_fUp_u", "category": "contractor", "label": "Framing Upstairs (under)", "rate": 5.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fUp_o", "category": "contractor", "label": "Framing Upstairs (over)", "rate": 6, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_fAttic_u", "category": "contractor", "label": "Attic/Carport (under)", "rate": 4, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fAttic_o", "category": "contractor", "label": "Attic/Carport (over)", "rate": 4.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_fPorch_u", "category": "contractor", "label": "Porch Framing (under)", "rate": 5.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fPorch_o", "category": "contractor", "label": "Porch Framing (over)", "rate": 6, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_fBsmt_u", "category": "contractor", "label": "Basement Framing (under)", "rate": 7.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fBsmt_o", "category": "contractor", "label": "Basement Framing (over)", "rate": 8, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_fRafter_u", "category": "contractor", "label": "Rafter Framing (under)", "rate": 6, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_fRafter_o", "category": "contractor", "label": "Rafter Framing (over)", "rate": 6.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_bsmtLf", "category": "contractor", "label": "Basement Rooms LF", "rate": 10, "unit": "LF", "miles_tier": ""},
            {"key": "ctr_deckRoof_u", "category": "contractor", "label": "Deck w/ Roof (under)", "rate": 7, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_deckRoof_o", "category": "contractor", "label": "Deck w/ Roof (over)", "rate": 7.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_awnU", "category": "contractor", "label": "Awning Under 8'", "rate": 350, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_awnO", "category": "contractor", "label": "Awning Over 8'", "rate": 450, "unit": "ea", "miles_tier": ""},
            # Contractor — Roof
            {"key": "ctr_r612_u", "category": "contractor", "label": "Metal Roof ≤7/12 (under)", "rate": 1.3, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_r612_o", "category": "contractor", "label": "Metal Roof ≤7/12 (over)", "rate": 1.3, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_r812_u", "category": "contractor", "label": "Metal Roof ≥8/12 (under)", "rate": 1.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_r812_o", "category": "contractor", "label": "Metal Roof ≥8/12 (over)", "rate": 1.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_ss_u", "category": "contractor", "label": "Standing Seam ≤7/12", "rate": 2.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_ss_o", "category": "contractor", "label": "Standing Seam ≤7/12", "rate": 2.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_ss912_u", "category": "contractor", "label": "Standing Seam ≥8/12", "rate": 2.8, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_ss912_o", "category": "contractor", "label": "Standing Seam ≥8/12", "rate": 2.8, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_shing_u", "category": "contractor", "label": "Shingles", "rate": 0.75, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_shing_o", "category": "contractor", "label": "Shingles", "rate": 0.75, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_osb", "category": "contractor", "label": "OSB Sheathing", "rate": 0.5, "unit": "SF", "miles_tier": ""},
            # Contractor — Walls
            {"key": "ctr_mWall_u", "category": "contractor", "label": "Metal Walls (under)", "rate": 1.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_mWall_o", "category": "contractor", "label": "Metal Walls (over)", "rate": 1.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_mCeil_u", "category": "contractor", "label": "Metal Ceiling (under)", "rate": 1.75, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_mCeil_o", "category": "contractor", "label": "Metal Ceiling (over)", "rate": 1.75, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_bb_u", "category": "contractor", "label": "Board & Batten", "rate": 3, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_bb_o", "category": "contractor", "label": "Board & Batten", "rate": 3, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_lph_u", "category": "contractor", "label": "LP/Hardie Siding", "rate": 2, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_lph_o", "category": "contractor", "label": "LP/Hardie Siding", "rate": 2, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_vinyl_u", "category": "contractor", "label": "Vinyl Siding", "rate": 1.5, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_vinyl_o", "category": "contractor", "label": "Vinyl Siding", "rate": 1.5, "unit": "SF", "miles_tier": "o"},
            {"key": "ctr_sof_u", "category": "contractor", "label": "Soffit", "rate": 5.5, "unit": "LF", "miles_tier": "u"},
            {"key": "ctr_sof_o", "category": "contractor", "label": "Soffit", "rate": 5.5, "unit": "LF", "miles_tier": "o"},
            {"key": "ctr_bw_u", "category": "contractor", "label": "Beam Wrap", "rate": 5.5, "unit": "LF", "miles_tier": "u"},
            {"key": "ctr_bw_o", "category": "contractor", "label": "Beam Wrap", "rate": 5.5, "unit": "LF", "miles_tier": "o"},
            # Contractor — Stone
            {"key": "ctr_stone_u", "category": "contractor", "label": "Stone Labor (under)", "rate": 16, "unit": "SF", "miles_tier": "u"},
            {"key": "ctr_stone_o", "category": "contractor", "label": "Stone Labor (over)", "rate": 17, "unit": "SF", "miles_tier": "o"},
            # Contractor — D&W
            {"key": "ctr_dblD", "category": "contractor", "label": "Double Door", "rate": 150, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_sglD", "category": "contractor", "label": "Single Door", "rate": 100, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_dblW", "category": "contractor", "label": "Double Window", "rate": 100, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_sglW", "category": "contractor", "label": "Single Window", "rate": 50, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_s2s", "category": "contractor", "label": "2nd Story Single Window", "rate": 75, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_s2d", "category": "contractor", "label": "2nd Story Double Window", "rate": 150, "unit": "ea", "miles_tier": ""},
            # Contractor — Other
            {"key": "ctr_cup", "category": "contractor", "label": "Cupola Install", "rate": 125, "unit": "ea", "miles_tier": ""},
            {"key": "ctr_tgC", "category": "contractor", "label": "T&G Porch Ceiling", "rate": 2.25, "unit": "SF", "miles_tier": ""},
            {"key": "ctr_deckNR", "category": "contractor", "label": "Deck No Roof", "rate": 5.5, "unit": "SF", "miles_tier": ""},
            {"key": "ctr_trex", "category": "contractor", "label": "TREX Decking", "rate": 1, "unit": "SF", "miles_tier": ""},
            # Concrete
            {"key": "conc_4fiber_z1", "category": "concrete", "label": "4\" Fiber Zone 1", "rate": 5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_4fiber_z2", "category": "concrete", "label": "4\" Fiber Zone 2", "rate": 5.25, "unit": "SF", "miles_tier": ""},
            {"key": "conc_4fiber_z3", "category": "concrete", "label": "4\" Fiber Zone 3", "rate": 5.25, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6fiber_z1", "category": "concrete", "label": "6\" Fiber Zone 1", "rate": 6.25, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6fiber_z2", "category": "concrete", "label": "6\" Fiber Zone 2", "rate": 6.5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6fiber_z3", "category": "concrete", "label": "6\" Fiber Zone 3", "rate": 6.5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_4mono_z1", "category": "concrete", "label": "4\" Mono Zone 1", "rate": 8, "unit": "SF", "miles_tier": ""},
            {"key": "conc_4mono_z2", "category": "concrete", "label": "4\" Mono Zone 2", "rate": 8.5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_4mono_z3", "category": "concrete", "label": "4\" Mono Zone 3", "rate": 9, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6mono_z1", "category": "concrete", "label": "6\" Mono Zone 1", "rate": 8.5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6mono_z2", "category": "concrete", "label": "6\" Mono Zone 2", "rate": 9, "unit": "SF", "miles_tier": ""},
            {"key": "conc_6mono_z3", "category": "concrete", "label": "6\" Mono Zone 3", "rate": 9.5, "unit": "SF", "miles_tier": ""},
            {"key": "conc_lp", "category": "concrete", "label": "Line Pump", "rate": 1750, "unit": "flat", "miles_tier": ""},
            {"key": "conc_bp", "category": "concrete", "label": "Boom Pump", "rate": 2500, "unit": "flat", "miles_tier": ""},
            {"key": "conc_wire", "category": "concrete", "label": "Wire on 4' Grid", "rate": 0.85, "unit": "SF", "miles_tier": ""},
            {"key": "conc_rebar", "category": "concrete", "label": "Rebar on 4' Grid", "rate": 1.25, "unit": "SF", "miles_tier": ""},
            {"key": "conc_foam", "category": "concrete", "label": "2\" Foam Perimeter", "rate": 9, "unit": "LF", "miles_tier": ""},
            {"key": "conc_punch", "category": "concrete", "label": "Punch Minimum", "rate": 2500, "unit": "flat", "miles_tier": ""},
            {"key": "conc_minF", "category": "concrete", "label": "Fiber Minimum", "rate": 3500, "unit": "flat", "miles_tier": ""},
            {"key": "conc_minM", "category": "concrete", "label": "Mono Minimum", "rate": 5500, "unit": "flat", "miles_tier": ""},
        ]
        for d in data:
            ExteriorRateCard.objects.update_or_create(key=d["key"], defaults=d)
        self.stdout.write(f'  Exterior Rate Card: {len(data)} entries')

    # ─────────────────────────────────────────
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

    # ─────────────────────────────────────────
    # DEMO JOBS (manager/owner dashboards)
    # ─────────────────────────────────────────
    def seed_demo_jobs(self):
        branch_default = Branch.objects.filter(key="summertown").first() or Branch.objects.first()
        model_lookup = {
            "HUNTLEY 2.0": FloorPlanModel.objects.filter(name__iexact="HUNTLEY 2.0").first(),
            "CAJUN": FloorPlanModel.objects.filter(name__iexact="CAJUN").first(),
            "MINI PETTUS": FloorPlanModel.objects.filter(name__iexact="MINI PETTUS").first(),
        }

        # Full demo project data matching STMC_Full_Platform_Demo.html PJ array
        demo_jobs = [
            {
                "order_number": "DEMO-1001",
                "customer_name": "Theiss Build",
                "customer_display": "Julie Theiss",
                "phase": "roughin",
                "pm_name": "P. Olson",
                "model_key": "HUNTLEY 2.0",
                "contract_total": Decimal("282127.00"),
                "p10_material": Decimal("63075.00"),
                "adjusted_int": Decimal("219052.00"),
                "collected": Decimal("106233.00"),
                "trade_budgets": [
                    ("Framing",     25000,  23800, 1),
                    ("Roofing",      8200,      0, 2),
                    ("Siding",       4800,      0, 3),
                    ("Ext Trim",     6100,      0, 4),
                    ("D&W",          2900,      0, 5),
                    ("Cabinets",    22140,      0, 6),
                    ("Flooring",     4032,      0, 7),
                    ("Drywall",      9055,      0, 8),
                    ("Paint",        6720,      0, 9),
                    ("Trim",         7450,      0, 10),
                    ("Electrical",  11760,      0, 11),
                    ("Plumbing",     7200,      0, 12),
                    ("Insulation",   6468,      0, 13),
                    ("HVAC",        12000,      0, 14),
                    ("General",      5375,   2875, 15),
                ],
                "draws": [
                    (0, "Deposit",            2500, "p", "Feb 17"),
                    (1, "1st \u2014 Materials", 75333, "p", "Mar 2"),
                    (2, "2nd \u2014 Concrete",  28400, "p", "Mar 18"),
                    (3, "3rd \u2014 Framing",   25000, "p", "Apr 18"),
                    (4, "4th \u2014 Rough-ins", 56425, "c", ""),
                    (5, "5th \u2014 Finishes",  56425, "x", ""),
                    (6, "6th \u2014 Final",     38044, "x", ""),
                ],
            },
            {
                "order_number": "DEMO-1002",
                "customer_name": "Henderson Build",
                "customer_display": "James Henderson",
                "phase": "interior",
                "pm_name": "P. Olson",
                "model_key": "CAJUN",
                "contract_total": Decimal("318320.00"),
                "p10_material": Decimal("71150.00"),
                "adjusted_int": Decimal("247170.00"),
                "collected": Decimal("224734.00"),
                "trade_budgets": [
                    ("Framing",     28080,  27500, 1),
                    ("Roofing",      9600,   9200, 2),
                    ("Siding",       5400,   5100, 3),
                    ("Ext Trim",     7200,   6800, 4),
                    ("D&W",          3400,   3400, 5),
                    ("Cabinets",    24500,  23200, 6),
                    ("Flooring",     4320,   4100, 7),
                    ("Drywall",      9702,   9500, 8),
                    ("Paint",        7200,      0, 9),
                    ("Trim",         8100,      0, 10),
                    ("Electrical",  12600,  12200, 11),
                    ("Plumbing",     8400,   8100, 12),
                    ("Insulation",   6930,   6800, 13),
                    ("HVAC",        12000,  11500, 14),
                    ("General",      5875,   4200, 15),
                ],
                "draws": [
                    (0, "Deposit",            2500, "p", "Jan 5"),
                    (1, "1st \u2014 Materials", 82000, "p", "Jan 12"),
                    (2, "2nd \u2014 Concrete",  31590, "p", "Jan 28"),
                    (3, "3rd \u2014 Framing",   45480, "p", "Feb 18"),
                    (4, "4th \u2014 Rough-ins", 63664, "p", "Mar 15"),
                    (5, "5th \u2014 Finishes",  63664, "c", ""),
                    (6, "6th \u2014 Final",     29422, "x", ""),
                ],
            },
            {
                "order_number": "DEMO-1003",
                "customer_name": "Cooper Ranch",
                "customer_display": "Sarah Cooper",
                "phase": "punch",
                "pm_name": "P. Olson",
                "model_key": "MINI PETTUS",
                "contract_total": Decimal("399457.00"),
                "p10_material": Decimal("100750.00"),
                "adjusted_int": Decimal("298707.00"),
                "collected": Decimal("350159.00"),
                "trade_budgets": [
                    ("Framing",     32000,  31200, 1),
                    ("Roofing",     11200,  10800, 2),
                    ("Siding",       6200,   6100, 3),
                    ("Ext Trim",     8400,   8200, 4),
                    ("D&W",          3800,   3650, 5),
                    ("Cabinets",    28600,  27900, 6),
                    ("Flooring",     4910,   4750, 7),
                    ("Drywall",     11028,  10800, 8),
                    ("Paint",        8184,   7900, 9),
                    ("Trim",         9200,   8900, 10),
                    ("Electrical",  14322,  14100, 11),
                    ("Plumbing",     9600,   9400, 12),
                    ("Insulation",   7877,   7600, 13),
                    ("HVAC",        16000,  15500, 14),
                    ("General",      5875,   5600, 15),
                ],
                "draws": [
                    (0, "Deposit",            2500, "p", "Nov 1"),
                    (1, "1st \u2014 Materials", 104000, "p", "Nov 8"),
                    (2, "2nd \u2014 Concrete",   32742, "p", "Nov 25"),
                    (3, "3rd \u2014 Framing",    51135, "p", "Dec 20"),
                    (4, "4th \u2014 Rough-ins",  79891, "p", "Jan 30"),
                    (5, "5th \u2014 Finishes",   79891, "p", "Mar 5"),
                    (6, "6th \u2014 Final",      49298, "c", ""),
                ],
            },
        ]

        seeded = 0
        for row in demo_jobs:
            model = model_lookup.get(row["model_key"])
            budget_total = sum(t[1] for t in row["trade_budgets"])
            budget_spent = sum(t[2] for t in row["trade_budgets"])

            job, _ = Job.objects.update_or_create(
                order_number=row["order_number"],
                defaults={
                    "customer_name": row["customer_name"],
                    "customer_addr": row["customer_display"],
                    "sales_rep": row["pm_name"],
                    "branch": branch_default,
                    "floor_plan": model,
                    "job_mode": "turnkey",
                    "p10_material": row["p10_material"],
                    "adjusted_int_contract": row["adjusted_int"],
                    "current_phase": row["phase"],
                    "budget_total_amount": Decimal(str(budget_total)),
                    "budget_spent_amount": Decimal(str(budget_spent)),
                    "collected_amount": row["collected"],
                    "current_draw_amount": Decimal(str(
                        next((d[2] for d in row["draws"] if d[3] == "c"), 0)
                    )),
                },
            )

            # Seed trade-level budgets
            for trade_name, budgeted, actual, sort_order in row["trade_budgets"]:
                JobTradeBudget.objects.update_or_create(
                    job=job,
                    trade_name=trade_name,
                    defaults={
                        "budgeted": Decimal(str(budgeted)),
                        "actual": Decimal(str(actual)),
                        "sort_order": sort_order,
                    },
                )

            # Seed draw schedule
            for draw_number, label, amount, status, paid_date in row["draws"]:
                JobDraw.objects.update_or_create(
                    job=job,
                    draw_number=draw_number,
                    defaults={
                        "label": label,
                        "amount": Decimal(str(amount)),
                        "status": status,
                        "paid_date": paid_date,
                    },
                )

            seeded += 1

        self.stdout.write(f'  Demo Jobs: {seeded} (with trade budgets and draw schedules)')

