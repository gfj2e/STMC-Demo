"""
STMC Turnkey Estimator — Django Database Schema
================================================
Derived from STMC_TURNKEY_WIZARD_BUILD_SPEC.md (2,324 lines)
Covers all 9 wizard steps, 39 models, rate cards, upgrade routing, and budget tracking.

Design principles:
- All monetary fields use DecimalField (max_digits=12, decimal_places=2)
- Model presets are seeded from PM, MD, RD, P10, MODELS, CRAFTSMAN, INT_CONTRACT, BASE_COSTS
- Job state is stored per-project, not in browser memory
- Backend-only profitability fields are on the Job model (never exposed to PM UI)
- Upgrade routing uses a ForeignKey to BudgetTrade for precise budget allocation
"""

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import json


# ═══════════════════════════════════════════════════════════════
# REFERENCE DATA — Seeded once, rarely changes
# ═══════════════════════════════════════════════════════════════

class Branch(models.Model):
    """Branch locations that affect concrete zone, miles tier, and default rates."""
    key = models.CharField(max_length=30, unique=True)  # e.g. "summertown"
    label = models.CharField(max_length=100)             # e.g. "Summertown Main"
    conc_rate = models.DecimalField(max_digits=6, decimal_places=2, default=8)
    default_miles = models.IntegerField(default=0)       # 0=under100, 1=over100
    zone = models.IntegerField(default=1)                # 1, 2, or 3

    class Meta:
        verbose_name_plural = "Branches"

    def __str__(self):
        return self.label


class AppUser(models.Model):
    """Simple app user directory for login role routing."""
    ROLE_CHOICES = [
        ('sales', 'Sales'),
        ('pm', 'Project Manager'),
        ('exec', 'Executive / Owner'),
    ]

    user_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    initials = models.CharField(max_length=4)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    title = models.CharField(max_length=80, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.role})"


class FloorPlanModel(models.Model):
    """
    A barndominium floor plan model (e.g. HUNTLEY 2.0, THE PETTUS).
    Contains all preset data from PM, MD, RD, P10, MODELS, CRAFTSMAN, INT_CONTRACT, BASE_COSTS.
    """
    name = models.CharField(max_length=60, unique=True)  # ALL CAPS: "CAJUN", "HUNTLEY 2.0"

    # From PM — Exterior Plan Metrics
    stories = models.DecimalField(max_digits=3, decimal_places=1, default=1)  # 1, 1.5, or 2
    ext_wall_sf = models.IntegerField(default=0)
    dbl_doors = models.IntegerField(default=0)
    sgl_doors = models.IntegerField(default=0)
    dbl_windows = models.IntegerField(default=0)
    sgl_windows = models.IntegerField(default=0)

    # From P10 — Material price
    p10_material = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # From MODELS — Cabinet/island data
    cabinetry_lf_display = models.CharField(max_length=20, blank=True)  # "44' - 0\""
    cabinetry_lf_num = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    island_depth = models.IntegerField(default=3)
    island_width = models.IntegerField(default=8)
    island_label = models.CharField(max_length=20, blank=True)  # "4' x 8'"
    pdf_pages = models.IntegerField(default=2)
    is_custom = models.BooleanField(default=False)

    # From INT_CONTRACT — Turnkey interior contract price
    int_contract = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # From BASE_COSTS — Cabinet base + INT contract
    cabinet_top_line = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # model LF × $330

    # PDF file reference
    pdf_filename = models.CharField(max_length=100, blank=True)  # e.g. "CAJUN.pdf"

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SlabAreaPreset(models.Model):
    """Default slab schedule rows per model (from MD)."""
    model = models.ForeignKey(FloorPlanModel, on_delete=models.CASCADE, related_name='slab_presets')
    area_name = models.CharField(max_length=40)  # "1st Floor Living Area", "Garage Area", etc.
    sqft = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']


class RoofAreaPreset(models.Model):
    """Default roof schedule rows per model (from RD)."""
    model = models.ForeignKey(FloorPlanModel, on_delete=models.CASCADE, related_name='roof_presets')
    area_name = models.CharField(max_length=40)  # "Main House", "Front Porch", etc.
    sqft = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']


class CraftsmanPreset(models.Model):
    """Per-model craftsman door style paint/stain pricing by area (from CRAFTSMAN)."""
    model = models.ForeignKey(FloorPlanModel, on_delete=models.CASCADE, related_name='craftsman_presets')
    area = models.CharField(max_length=20)  # kitchen, island, laundry, baths, other
    paint_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stain_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['model', 'area']


class PlanMetric(models.Model):
    """Per-model interior plan metrics (from PLAN_METRICS)."""
    model = models.ForeignKey(FloorPlanModel, on_delete=models.CASCADE, related_name='plan_metrics')
    key = models.CharField(max_length=40)    # "Total Living SF", "Bath Count", etc.
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['model', 'key']


# ═══════════════════════════════════════════════════════════════
# RATE CARDS — Seeded, adjustable per branch/override
# ═══════════════════════════════════════════════════════════════

class ExteriorRateCard(models.Model):
    """
    Exterior pricing rates (from P object).
    Stores sales rates (customer-facing) and contractor rates (under/over 100mi).
    """
    key = models.CharField(max_length=30, unique=True)  # e.g. "sales_base", "ctr_fSlab_u"
    category = models.CharField(max_length=20)           # "sales", "contractor", "concrete"
    label = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10)               # "SF", "LF", "ea", "flat"
    miles_tier = models.CharField(max_length=10, blank=True)  # "u", "o", or "" for flat

    def __str__(self):
        return f"{self.label}: ${self.rate}/{self.unit}"


class InteriorRateCard(models.Model):
    """
    Interior rate card (from INT_RC).
    Each row is one rate line that drives a budget trade.
    """
    key = models.CharField(max_length=30, unique=True)  # e.g. "cabinets", "floorMat", "electrical"
    label = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10)               # "/LF", "/SF", "/bath", "/fix", "/ton", "flat"
    driver = models.CharField(max_length=30)             # "cabLF", "livingSF", "bathCount", "flat", etc.

    def __str__(self):
        return f"{self.label}: ${self.rate}{self.unit}"


# ═══════════════════════════════════════════════════════════════
# BUDGET TRADE STRUCTURE
# ═══════════════════════════════════════════════════════════════

class BudgetTrade(models.Model):
    """
    Budget trade groups for both interior and exterior.
    16 interior + 7 exterior = 23 total trades.
    """
    SCOPE_CHOICES = [('interior', 'Interior'), ('exterior', 'Exterior')]

    key = models.CharField(max_length=30, unique=True)   # "cabinets", "flooring", "framing", etc.
    name = models.CharField(max_length=40)               # Display name
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    sort_order = models.IntegerField(default=0)
    has_base_cost = models.BooleanField(default=True)    # False for upgrade-only trades (fireplaces, tile, etc.)

    class Meta:
        ordering = ['scope', 'sort_order']

    def __str__(self):
        return f"[{self.scope}] {self.name}"


class BudgetTradeRate(models.Model):
    """Maps rate card entries to budget trades (which rates roll into which trade)."""
    trade = models.ForeignKey(BudgetTrade, on_delete=models.CASCADE, related_name='rate_mappings')
    rate_card = models.ForeignKey(InteriorRateCard, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['trade', 'rate_card']


# ═══════════════════════════════════════════════════════════════
# UPGRADE ITEMS — Seeded catalog of all available upgrades
# ═══════════════════════════════════════════════════════════════

class UpgradeCategory(models.Model):
    """
    Top-level upgrade category / pill tab.
    Maps to Steps 6-7 UI structure.
    """
    STEP_CHOICES = [
        ('cabinets', 'Step 6 - Cabinets'),
        ('countertops', 'Step 6 - Countertops'),
        ('docusign', 'Step 7 - Docusign Upgrades'),
        ('electrical', 'Step 7 - Electrical'),
        ('plumbing', 'Step 7 - Plumbing'),
        ('trim', 'Step 7 - Interior Trim & Flooring'),
        ('custom', 'Step 7 - Custom'),
    ]

    key = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    step = models.CharField(max_length=20, choices=STEP_CHOICES)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']
        verbose_name_plural = "Upgrade Categories"

    def __str__(self):
        return self.name


class UpgradeSection(models.Model):
    """Section within an upgrade category (e.g. "Kitchen Upgrades", "Outlets & Technology")."""
    category = models.ForeignKey(UpgradeCategory, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=60)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.category.name} > {self.name}"


class UpgradeItem(models.Model):
    """
    Individual upgrade line item (e.g. "Can Lights ($250 each)").
    Includes budget routing and special calculation rules.
    """
    INPUT_TYPE_CHOICES = [
        ('toggle', 'Checkbox (flat cost)'),
        ('qty', 'Quantity stepper'),
        ('sf', 'Square footage input'),
        ('lf', 'Linear footage input'),
        ('radio', 'Radio buttons (informational)'),
    ]

    section = models.ForeignKey(UpgradeSection, on_delete=models.CASCADE, related_name='items')
    item_id = models.CharField(max_length=40, unique=True)  # e.g. "canLight", "selFarmSink"
    label = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    unit = models.CharField(max_length=10, default='each')  # "each", "SF", "LF"

    # Budget routing
    budget_trade = models.ForeignKey(BudgetTrade, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="Which trade this upgrade's true cost routes to")
    true_cost_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=0.80,
                                                help_text="Usually 0.80 (20% margin). Set to 1.0 for pass-through.")

    # Special calculation flags
    has_base_addon = models.BooleanField(default=False)  # e.g. HVAC upgrade with $1,039 gas line
    base_addon_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    adds_fixture_points = models.DecimalField(max_digits=4, decimal_places=1, default=0,
                                               help_text="Plumbing fixture points added (e.g. 1.0 for sink stub, 0.5 for ice line)")
    is_split_budget = models.BooleanField(default=False,
                                           help_text="True for tankless WH: 50% to materials, +1 fixture point")
    has_note_box = models.BooleanField(default=False,
                                        help_text="Shows text input when qty > 0 (cabinet inserts)")

    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.label} (${self.price})"


# ═══════════════════════════════════════════════════════════════
# APPLIANCE & ISLAND CONFIGURATION OPTIONS
# ═══════════════════════════════════════════════════════════════

class ApplianceConfig(models.Model):
    """Appliance configuration options (from APPLIANCE_COSTS/LABELS)."""
    key = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.label


class IslandAddon(models.Model):
    """Island add-on options (from ISLAND_ADDON_LABELS)."""
    key = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=500)

    def __str__(self):
        return self.label


# ═══════════════════════════════════════════════════════════════
# JOB / PROJECT — One per customer build
# ═══════════════════════════════════════════════════════════════

class Job(models.Model):
    """
    A single barndominium project. Contains all state for one customer build.
    This is the central entity — everything else references back here.
    """
    MODE_CHOICES = [('shell', 'Shell Only'), ('turnkey', 'Turnkey Interior')]
    PHASE_CHOICES = [
        ('estimate', 'Estimate'),
        ('framing', 'Framing'),
        ('interior', 'Interior'),
        ('punch', 'Punch'),
        ('final', 'Final'),
        ('closed', 'Closed'),
    ]
    DRAW_STAGE_CHOICES = [
        ('draw1', '1st - Deposit'),
        ('draw2', '2nd - Slab'),
        ('draw3', '3rd - Framing'),
        ('draw4', '4th - Dry-In'),
        ('draw5', '5th - Finishes'),
        ('draw6', '6th - Final'),
    ]
    DRAW_STATUS_CHOICES = [
        ('current', 'Current'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ('hold', 'Hold'),
        ('closed', 'Closed'),
    ]

    # Step 1 — Customer & Model
    customer_name = models.CharField(max_length=200, blank=True)
    customer_addr = models.CharField(max_length=300, blank=True)
    sales_rep = models.CharField(max_length=100, blank=True)
    order_number = models.CharField(max_length=50, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    floor_plan = models.ForeignKey(FloorPlanModel, on_delete=models.SET_NULL, null=True, blank=True)
    job_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='shell')
    miles_over_100 = models.BooleanField(default=False)
    p10_material = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text="Auto-filled from model P10 but editable")

    # Step 2 — Foundation
    foundation_type = models.CharField(max_length=10, default='concrete')  # "concrete" or "crawl"
    basement_framing = models.BooleanField(default=False)
    crawl_sf = models.IntegerField(default=0)
    stories = models.DecimalField(max_digits=3, decimal_places=1, default=1)

    # Step 3 — Exterior options
    wall_type = models.CharField(max_length=30, default='Metal')
    wall_tuff_sf = models.IntegerField(default=0)
    wainscot_enabled = models.BooleanField(default=False)
    wall_rock_sf = models.IntegerField(default=0)
    wall_stone_sf = models.IntegerField(default=0)
    stone_upgrade = models.BooleanField(default=False)
    sheathing = models.BooleanField(default=False)
    gauge_26 = models.BooleanField(default=False)
    awning_qty = models.IntegerField(default=0)
    cupola_qty = models.IntegerField(default=0)
    chimney_qty = models.IntegerField(default=0)
    punch_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2500)
    windows_above_12 = models.BooleanField(default=False)
    sgl_windows = models.IntegerField(default=0)
    dbl_windows = models.IntegerField(default=0)
    s2s_windows = models.IntegerField(default=0)
    s2d_windows = models.IntegerField(default=0)
    sgl_doors = models.IntegerField(default=0)
    dbl_doors = models.IntegerField(default=0)
    detached_shop = models.BooleanField(default=False)
    deck_shown = models.BooleanField(default=False)

    # Step 4 — Concrete
    conc_sqft = models.IntegerField(default=0)
    conc_type = models.CharField(max_length=20, blank=True)  # "4fiber", "6fiber", "4mono", "6mono"
    conc_zone = models.IntegerField(default=1)
    conc_line_pump = models.BooleanField(default=False)
    conc_boom_pump = models.BooleanField(default=False)
    conc_wire = models.BooleanField(default=False)
    conc_rebar = models.BooleanField(default=False)
    conc_foam_lf = models.IntegerField(default=0)

    # Step 5 — Interior Selections
    bedrooms = models.IntegerField(default=3)
    full_baths = models.IntegerField(default=2)
    half_baths = models.IntegerField(default=0)
    plumbing_fixtures = models.IntegerField(default=8)
    closet_qty = models.IntegerField(default=3)
    interior_doors = models.IntegerField(default=15)
    laundry_sink = models.BooleanField(default=False)
    modified_cab_lf = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    modified_island_depth = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    modified_island_width = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    island_addon = models.CharField(max_length=30, blank=True)  # "", "microwave", "sink", "sink_microwave"
    appliance_config = models.CharField(max_length=40, default='standard_range_mw')

    # Computed metrics (editable on Budget page)
    counter_sf = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    flooring_sf = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    trim_lf = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    drywall_sf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dw_sheets = models.IntegerField(default=0)
    paint_sf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hvac_tons = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    insulation_sf = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Step 6 — Cabinet discount
    cabinet_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Step 6 — Countertop notes
    countertop_notes = models.TextField(blank=True)

    # Step 7 Pill 1 — Gas type
    gas_type = models.CharField(max_length=10, blank=True)  # "natural", "propane", ""

    # ── BACKEND-ONLY PROFITABILITY (never shown in UI) ──
    int_true_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    adjusted_int_contract = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    int_margin_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    int_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ext_labor_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ext_labor_profit_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    margin_div = models.DecimalField(max_digits=6, decimal_places=4, default=1)

    # ── PROJECT TRACKING (Manager/Owner dashboards) ──
    current_phase = models.CharField(max_length=12, choices=PHASE_CHOICES, default='estimate')
    draw_stage = models.CharField(max_length=10, choices=DRAW_STAGE_CHOICES, default='draw1')
    draw_status = models.CharField(max_length=10, choices=DRAW_STATUS_CHOICES, default='current')
    progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    budget_total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    collected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_draw_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer_name} — {self.floor_plan or 'No Model'} ({self.job_mode})"


# ═══════════════════════════════════════════════════════════════
# JOB CHILD TABLES — Per-job editable schedules
# ═══════════════════════════════════════════════════════════════

class JobSlabRow(models.Model):
    """Editable slab schedule row for a job (from Step 2)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='slab_rows')
    area_name = models.CharField(max_length=40)
    sqft = models.IntegerField(default=0)
    tg_ceiling = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']


class JobRoofRow(models.Model):
    """Editable roof schedule row for a job (from Step 3)."""
    ROOF_TYPE_CHOICES = [('metal', 'Metal'), ('ss', 'Standing Seam'), ('shingles', 'Shingles')]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='roof_rows')
    area_name = models.CharField(max_length=40)
    roof_type = models.CharField(max_length=10, choices=ROOF_TYPE_CHOICES, default='metal')
    steep = models.BooleanField(default=False)  # True = 8/12 or greater
    sqft = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']


class JobCustomCharge(models.Model):
    """Custom charges on Steps 3 and 4 (exterior + concrete)."""
    CHARGE_TYPE_CHOICES = [('exterior', 'Exterior'), ('concrete', 'Concrete')]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='custom_charges')
    charge_type = models.CharField(max_length=10, choices=CHARGE_TYPE_CHOICES)
    description = models.CharField(max_length=200, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=5, default='SF')  # "SF", "LF", "ea"
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def cost(self):
        return self.rate * self.qty


class JobContractorOverride(models.Model):
    """PM overrides on the contractor calculator (Step 9 Part A)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='contractor_overrides')
    item_key = models.CharField(max_length=30)  # Matches buildCtrItems() key
    override_qty = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['job', 'item_key']


# ═══════════════════════════════════════════════════════════════
# STEP 6 — Cabinet & Countertop Selections
# ═══════════════════════════════════════════════════════════════

class JobCraftsmanSelection(models.Model):
    """Craftsman door style selection per area (Step 6, Section 2 Part A)."""
    FINISH_CHOICES = [('', 'None'), ('paint', 'Craftsman Paint'), ('stain', 'Craftsman Stain')]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='craftsman_selections')
    area = models.CharField(max_length=20)  # kitchen, island, laundry, baths, other
    finish = models.CharField(max_length=10, choices=FINISH_CHOICES, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['job', 'area']


class JobCustomCraftsmanRow(models.Model):
    """Custom craftsman area rows (Step 6, Section 2 Part B)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='custom_craftsman_rows')
    area = models.CharField(max_length=100, blank=True)
    finish = models.CharField(max_length=10)  # "paint" ($35/LF) or "stain" ($45/LF)
    lf = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    @property
    def cost(self):
        rate = 35 if self.finish == 'paint' else 45
        return round(float(self.lf) * rate)


class JobCabinetUpgrade(models.Model):
    """Cabinet upgrade selections (Step 6, Sections 3-7)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='cabinet_upgrades')
    item = models.ForeignKey(UpgradeItem, on_delete=models.CASCADE)
    qty = models.IntegerField(default=0)
    checked = models.BooleanField(default=False)  # For toggle types
    lf_value = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # For LF types
    note = models.TextField(blank=True)  # For insert note boxes

    @property
    def cost(self):
        if self.item.input_type == 'toggle':
            return float(self.item.price) if self.checked else 0
        elif self.item.input_type == 'qty':
            return self.qty * float(self.item.price)
        elif self.item.input_type == 'lf':
            return round(float(self.lf_value) * float(self.item.price))
        return 0


class JobCabinetCustomLine(models.Model):
    """Custom cabinet line items (Step 6, Section 7 free-form)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='cabinet_custom_lines')
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    area = models.CharField(max_length=100, blank=True)


class JobCountertopArea(models.Model):
    """Countertop upgrade area rows (Step 6 Sub-Tab B, Section 2)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='countertop_areas')
    area = models.CharField(max_length=100, blank=True)
    rate_per_sf = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sqft = models.IntegerField(default=0)

    @property
    def cost(self):
        return round(float(self.rate_per_sf) * self.sqft)


# ═══════════════════════════════════════════════════════════════
# STEP 7 — Selections (Pills 1-4)
# ═══════════════════════════════════════════════════════════════

class JobUpgradeSelection(models.Model):
    """
    A single upgrade selection on a job (Steps 7 Pills 1-4).
    Covers toggle, qty, sf, and lf input types.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='upgrade_selections')
    item = models.ForeignKey(UpgradeItem, on_delete=models.CASCADE)
    qty = models.IntegerField(default=0)
    checked = models.BooleanField(default=False)
    sf_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lf_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def customer_cost(self):
        if self.item.input_type == 'toggle':
            return float(self.item.price) if self.checked else 0
        elif self.item.input_type == 'qty':
            base = self.qty * float(self.item.price)
            if self.item.has_base_addon and self.qty > 0:
                base += float(self.item.base_addon_amount)
            return base
        elif self.item.input_type == 'sf':
            return round(float(self.sf_value) * float(self.item.price))
        elif self.item.input_type == 'lf':
            return round(float(self.lf_value) * float(self.item.price))
        return 0

    @property
    def budget_true_cost(self):
        if self.item.is_split_budget:
            # Tankless WH: 50% to materials (fixture point handled separately)
            return round(self.customer_cost * 0.50)
        return round(self.customer_cost * float(self.item.true_cost_multiplier))

    class Meta:
        unique_together = ['job', 'item']


class JobSelectionCustomLine(models.Model):
    """Custom line items within Docusign, Electrical, Plumbing, or Trim pills."""
    PILL_CHOICES = [
        ('docusign', 'Docusign'), ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'), ('trim', 'Interior Trim'),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='selection_custom_lines')
    pill = models.CharField(max_length=20, choices=PILL_CHOICES)
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    budget_trade = models.ForeignKey(BudgetTrade, on_delete=models.SET_NULL, null=True, blank=True)


class JobConcreteFinishLine(models.Model):
    """Concrete floor finish custom lines (Pill 4, Section 5)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='concrete_finish_lines')
    description = models.CharField(max_length=200, blank=True)
    rate_per_sf = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sqft = models.IntegerField(default=0)

    @property
    def cost(self):
        return round(float(self.rate_per_sf) * self.sqft)


# ═══════════════════════════════════════════════════════════════
# STEP 7 PILL 5 — Custom Upgrades & Credits
# ═══════════════════════════════════════════════════════════════

class JobCustomUpgrade(models.Model):
    """Custom upgrade from Pill 5 Part A."""
    PRICING_CHOICES = [('flat', 'Flat Rate'), ('per_unit', 'Per SF/LF')]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='custom_upgrades')
    trade = models.ForeignKey(BudgetTrade, on_delete=models.CASCADE,
                               help_text="Which budget trade this routes to")
    pricing_type = models.CharField(max_length=10, choices=PRICING_CHOICES)
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # For flat rate
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)    # For per-unit
    unit = models.CharField(max_length=5, default='SF')                       # "SF" or "LF"
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def customer_cost(self):
        if self.pricing_type == 'flat':
            return float(self.amount)
        return round(float(self.rate) * float(self.qty))

    @property
    def budget_true_cost(self):
        return round(self.customer_cost * 0.80)


class JobCredit(models.Model):
    """Credit from Pill 5 Part B — subtracts from INT contract and budget trade."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='credits')
    trade = models.ForeignKey(BudgetTrade, on_delete=models.CASCADE,
                               help_text="Which budget trade gets reduced")
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                  help_text="Full credit amount (NOT × 0.80 — entire expense eliminated)")


# ═══════════════════════════════════════════════════════════════
# BUDGET SNAPSHOT — Computed on save, stored for reporting
# ═══════════════════════════════════════════════════════════════

class JobBudgetLine(models.Model):
    """
    Computed budget line per trade for a job.
    Recalculated whenever the job is saved.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='budget_lines')
    trade = models.ForeignKey(BudgetTrade, on_delete=models.CASCADE)
    base_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    upgrade_adder = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_reduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_budgeted = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Backend-only (not shown in PM UI)
    customer_price_allocation = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ['job', 'trade']


# ═══════════════════════════════════════════════════════════════
# DEMO DASHBOARD TABLES — Granular budget/draw data for PM & Owner views
# ═══════════════════════════════════════════════════════════════

class JobTradeBudget(models.Model):
    """Per-trade budget and actual amounts — used by manager/owner dashboards."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='demo_trade_budgets')
    trade_name = models.CharField(max_length=40)
    budgeted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'trade_name']
        unique_together = ['job', 'trade_name']

    def __str__(self):
        return f"{self.job.customer_name} — {self.trade_name}"


class JobDraw(models.Model):
    """Individual draw entry — used by manager/owner draw-schedule views."""
    STATUS_PAID = 'p'
    STATUS_CURRENT = 'c'
    STATUS_PENDING = 'x'
    STATUS_CHOICES = [
        ('p', 'Paid'),
        ('c', 'Current'),
        ('x', 'Pending'),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='demo_draws')
    draw_number = models.IntegerField()
    label = models.CharField(max_length=60)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='x')
    paid_date = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['draw_number']
        unique_together = ['job', 'draw_number']

    def __str__(self):
        return f"{self.job.customer_name} — {self.label}"
