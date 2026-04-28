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
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
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


class AppUser(AbstractUser):
    """STMC app user — authenticates by email, routes by role."""
    ROLE_SALES = 'sales'
    ROLE_PM = 'pm'
    ROLE_EXEC = 'exec'
    ROLE_CHOICES = [
        (ROLE_SALES, 'Sales'),
        (ROLE_PM, 'Project Manager'),
        (ROLE_EXEC, 'Executive / Owner'),
    ]

    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=120)
    initials = models.CharField(max_length=4)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    title = models.CharField(max_length=80, blank=True)
    sort_order = models.IntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name', 'role']

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
# ExteriorRateCard was dropped when the wizard pivoted to interior-only.


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
    # job_mode is always 'turnkey' since the wizard pivoted to interior-only.
    # 'shell' is retained as a choice only so legacy rows don't fail validation;
    # nothing in the codebase writes it anymore.
    MODE_CHOICES = [('shell', 'Shell Only (legacy)'), ('turnkey', 'Turnkey Interior')]
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('llc', 'LLC / Business'),
        ('trust', 'Trust / Estate'),
    ]
    FOUNDATION_TYPE_CHOICES = [
        ('slab', 'Monolithic Slab w/ Footers'),
        ('crawlspace', 'Crawlspace'),
        ('basement', 'Basement'),
        ('blockfill', 'Block-and-Fill'),
    ]
    PHASE_CHOICES = [
        ('estimate', 'Estimate'),
        ('framing', 'Framing'),
        ('roughin', 'Rough-In'),
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
    custom_rep_name = models.CharField(max_length=100, blank=True)
    contracts_rep = models.CharField(max_length=50, blank=True)
    order_number = models.CharField(max_length=50, blank=True)
    order_number_secondary = models.CharField(max_length=50, blank=True,
        help_text="Secondary S/M order number for shop/detached garage builds")
    bank_name = models.CharField(max_length=120, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    floor_plan = models.ForeignKey(FloorPlanModel, on_delete=models.SET_NULL, null=True, blank=True)
    job_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='turnkey')
    miles_over_100 = models.BooleanField(default=False)
    p10_material = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text="Entered on Contract step once material quote returns")

    # Buyer + co-buyer (V10 — drives DocuSign and QB Customer record)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    co_buyer_name = models.CharField(max_length=200, blank=True)
    co_buyer_email = models.EmailField(max_length=200, blank=True)
    co_buyer_phone = models.CharField(max_length=40, blank=True)

    # Billing + job-site addresses (V10)
    bill_street = models.CharField(max_length=200, blank=True)
    bill_city = models.CharField(max_length=100, blank=True)
    bill_state = models.CharField(max_length=2, default='TN')
    bill_zip = models.CharField(max_length=10, blank=True)
    site_street = models.CharField(max_length=200, blank=True)
    site_city = models.CharField(max_length=100, blank=True)
    site_state = models.CharField(max_length=2, default='TN')
    site_zip = models.CharField(max_length=10, blank=True)
    site_same_as_billing = models.BooleanField(default=True)

    # Sales-rep-entered shell budget (replaces the retired exterior calculator)
    shell_contract = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Estimated total exterior shell contract — entered by sales rep on Step 1")
    concrete_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Concrete portion of the shell budget — flows to Draw 2")
    labor_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Exterior/framing labor portion of the shell budget — flows to Draw 3")
    manual_living_sf = models.IntegerField(default=0,
        help_text="Custom Floor Plan only — user-entered Living SF")

    # Contract metadata (V10) — supersedes / permit / site prep / detached shop
    foundation_type = models.CharField(max_length=20, choices=FOUNDATION_TYPE_CHOICES, default='slab',
        help_text="Drives contract template wording (slab vs. crawlspace clauses)")
    permit_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=2000)
    site_prep_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    det_shop_material = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Detached shop material — flows to Draw 1 shop line")
    det_shop_conc_labor = models.DecimalField(max_digits=12, decimal_places=2, default=0,
        help_text="Detached shop concrete + labor — flows to Draw 2 shop line")
    contract_notes = models.TextField(blank=True,
        help_text="Free-text spec notes appended to the contract")
    supersedes_prev_contract = models.BooleanField(default=False)
    supersedes_reason = models.CharField(max_length=200, blank=True)

    stories = models.DecimalField(max_digits=3, decimal_places=1, default=1)

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

    # ── SALES-SIDE STATE ──
    wizard_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw BuildWizard STATE payload, used to rehydrate the wizard on Edit.",
    )
    sales_closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when sales rep clicks DocuSign or Interior Contracts handoff. "
                  "Null = In Progress; set = Closed on the sales side.",
    )

    # ── LEAD FIELDS ──
    # A Lead is a Job where the rep has captured customer info but hasn't
    # committed a full contract estimate yet. Clearing is_lead (via the
    # wizard save) promotes the row to In Progress.
    LEAD_SOURCE_CHOICES = [
        ('referral', 'Referral'),
        ('web', 'Web / Inbound'),
        ('walk_in', 'Walk-in'),
        ('trade_show', 'Trade Show'),
        ('repeat', 'Repeat Customer'),
        ('other', 'Other'),
    ]
    is_lead = models.BooleanField(
        default=False,
        help_text="True = sales lead (early contact), False = committed contract. "
                  "Cleared automatically when the wizard is saved.",
    )
    customer_phone = models.CharField(max_length=40, blank=True)
    customer_email = models.EmailField(max_length=200, blank=True)
    lead_source = models.CharField(max_length=20, choices=LEAD_SOURCE_CHOICES, blank=True)
    lead_notes = models.TextField(blank=True)
    lead_next_followup = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date the rep plans to next contact the customer.",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer_name} — {self.floor_plan or 'No Model'} ({self.job_mode})"


# ═══════════════════════════════════════════════════════════════
# JOB CHILD TABLES — Per-job editable schedules
# ═══════════════════════════════════════════════════════════════
# JobSlabRow / JobRoofRow / JobCustomCharge / JobContractorOverride were
# dropped when the wizard pivoted to interior-only — they backed exterior
# steps that no longer exist. The current wizard saves slab/roof scaffold
# data in Job.wizard_state JSON if needed downstream.


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


# JobConcreteFinishLine was dropped along with the exterior steps; if the
# wizard surfaces any finish lines they ride in Job.wizard_state JSON.


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
    """Per-trade budget and actual amounts — used by manager/owner dashboards.

    `is_complete` flips to True the first time a paid Bill (Bill.Balance == 0)
    in QuickBooks credits this trade. The row locks at that point — subsequent
    Bills against the same trade are ignored by `qb_pull.refresh_actuals_for_job`
    so partial / change-order spend doesn't quietly overwrite the original
    paid amount. Anything beyond the first payment flows through the change-
    order workflow instead.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='demo_trade_budgets')
    trade_name = models.CharField(max_length=40)
    budgeted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)
    # ── Phase 2: paid-from-QB tracking ──
    is_complete = models.BooleanField(
        default=False,
        help_text="True once a paid Bill has credited this trade. Locks the row."
    )
    qb_bill_id = models.CharField(
        max_length=32, blank=True, default="",
        help_text="QB Bill.Id of the payment that locked this row (audit trail)."
    )
    paid_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp the puller observed Balance == 0 on the matching Bill."
    )

    class Meta:
        ordering = ['sort_order', 'trade_name']
        unique_together = ['job', 'trade_name']

    def __str__(self):
        return f"{self.job.customer_name} — {self.trade_name}"


class JobChangeOrder(models.Model):
    """A signed contract change order for a job. Modeled after the paper
    "Change Order" form (Version 2.2 Feb 2025). Numbered per-job (CO #1,
    CO #2, ...). Surfaced on the PM's My Builds card so the PM can see at
    a glance how many change orders a contract has accumulated."""

    PAYMENT_TIMING_CHOICES = [
        ('material_labor', 'Due with Material and Labor'),
        ('interiors', 'Due with Interiors'),
        ('immediately', 'Due immediately'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='change_orders')
    # Per-job sequential number. Allocated in the create view by counting
    # existing rows + 1 — there's no concurrency story for the demo.
    number = models.IntegerField()
    customer_name = models.CharField(max_length=200, blank=True)
    project_address = models.CharField(max_length=300, blank=True)
    project_manager = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    # Signed amount: negative for a credit, positive for additional charge.
    price_change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Optional — the paper form leaves it blank ("N/A") for credits, so we
    # allow zero / negative here too. The PM can fill it in if known.
    new_contract_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_timing = models.CharField(
        max_length=20, choices=PAYMENT_TIMING_CHOICES, default='immediately'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['number']
        unique_together = ['job', 'number']

    def __str__(self):
        return f"CO #{self.number} — {self.job.customer_name}"

    @property
    def is_credit(self):
        return self.price_change < 0


class JobDraw(models.Model):
    """Individual draw entry — used by manager/owner draw-schedule views.

    Phase 4 lifecycle (3-state):
      PENDING -> CURRENT (when prior draw paid; this draw becomes the next
                          one PM should mark complete)
      CURRENT -> INVOICED (PM clicks Mark Complete; QB Invoice DueDate is
                           updated to today)
      INVOICED -> PAID (qb_pull.refresh_draw_invoices_for_job observes
                        Balance == 0 on the QB Invoice; bank funds released)
    """
    STATUS_PAID = 'p'
    STATUS_INVOICED = 'i'
    STATUS_CURRENT = 'c'
    STATUS_PENDING = 'x'
    STATUS_CHOICES = [
        ('p', 'Paid'),
        ('i', 'Invoiced (Due)'),
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


# ═══════════════════════════════════════════════════════════════
# QUICKBOOKS ONLINE INTEGRATION
# ═══════════════════════════════════════════════════════════════
#
# Three models work together to back the draw-completion → QB invoice flow:
#
#   QbConnection  : singleton row holding the OAuth tokens + realm (QB company) ID.
#                   One row max. Populated by the Connect QuickBooks flow.
#   QbCustomerMap : caches the QB-side Customer.Id for each Job so repeated draws
#                   on the same contract don't create duplicate customers.
#   QbInvoiceEvent: one row per "draw marked complete" action. Stores the QB
#                   invoice identifiers (or null if the API call failed and we
#                   fell back to a local-only record), plus a read_at flag for
#                   the owner bell notification UI.


class QbConnection(models.Model):
    """Singleton row (enforced in code) holding the current QuickBooks OAuth
    tokens and realm (QB company) ID. The refresh token survives token refresh;
    the access token is rotated every ~60 minutes."""
    realm_id = models.CharField(max_length=64)
    access_token = models.TextField()
    refresh_token = models.TextField()
    # Approximate expiry; we refresh proactively when within 5 min of this value.
    access_token_expires_at = models.DateTimeField(default=timezone.now)
    refresh_token_expires_at = models.DateTimeField(default=timezone.now)
    connected_at = models.DateTimeField(default=timezone.now)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    # Intuit account email of the user who authorized the connection (for audit).
    connected_by_email = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "QuickBooks Connection"

    def __str__(self):
        return f"QuickBooks (realm {self.realm_id})"


class QbCustomerMap(models.Model):
    """One row per Job whose customer has been synced to QuickBooks. Keeps us
    from creating duplicate QB Customers when multiple draws complete for the
    same contract."""
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="qb_customer_map")
    qb_customer_id = models.CharField(max_length=32)
    # Realm this mapping was created under — so if the connected QB company ever
    # changes, we invalidate the cache.
    realm_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Job {self.job_id} → QB Customer {self.qb_customer_id}"


class QbItemMap(models.Model):
    """Cache: trade-bucket name → QB Item Id + Account Id.

    Populated by `python manage.py qb_seed_sandbox` after the QB connection
    is live. The seed creates one Item per JobTradeBudget trade bucket
    (Cabinets, Drywall, Electrical, ...) so the puller can match Bill lines
    1:1 even when multiple buckets share an Account (Cabinets/Countertops
    both → "Cabinets and Ctops"). Realm-aware so a QB company switch
    invalidates stale entries — mirrors `QbCustomerMap`.
    """
    trade_name = models.CharField(
        max_length=64, unique=True,
        help_text="JobTradeBudget.trade_name (e.g. 'Cabinets')"
    )
    qb_item_id = models.CharField(max_length=32)
    qb_account_id = models.CharField(max_length=32)
    qb_account_name = models.CharField(
        max_length=128,
        help_text="QB Chart of Accounts name (e.g. 'Cabinets and Ctops')"
    )
    realm_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.trade_name} → Item {self.qb_item_id} / Acct {self.qb_account_name}"


class QbInvoiceEvent(models.Model):
    """One row per 'draw marked complete' action. When the QB API call
    succeeds, qb_invoice_id / qb_invoice_doc_number / qb_invoice_url are set.
    On failure (no connection, token refresh failed, API error) we still
    create the row with status='failed_fallback' so the demo UI never breaks
    — the owner just won't see a live QB linkout for that event."""

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed_fallback"
    STATUS_CHOICES = [
        (STATUS_SENT, "Sent to QuickBooks"),
        (STATUS_FAILED, "Local fallback (QB unavailable)"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="qb_events")
    draw = models.ForeignKey(JobDraw, on_delete=models.CASCADE, related_name="qb_events")
    # Internal display values — always populated.
    team_name = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # QuickBooks-side identifiers — populated on success, null on fallback.
    qb_invoice_id = models.CharField(max_length=32, blank=True, default="")
    qb_invoice_doc_number = models.CharField(max_length=32, blank=True, default="")
    qb_invoice_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_SENT)
    error_message = models.CharField(max_length=500, blank=True, default="")
    # ── Phase 4: 3-state draw invoice lifecycle ──
    # PM "Mark Complete" updates the QB Invoice DueDate to today and stamps
    # qb_due_marked_at. Later, when an accountant records a Payment in QB
    # against the invoice, the next qb_pull.refresh_snapshot() observes
    # Balance == 0 and stamps paid_at (also flipping the JobDraw to PAID).
    # Both fields stay null until the corresponding lifecycle event fires.
    qb_due_marked_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    # Notification read-state (shared across all exec users for demo simplicity).
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        doc = self.qb_invoice_doc_number or f"(local #{self.pk})"
        return f"{doc} — {self.team_name} — ${self.amount}"

    @property
    def display_invoice_number(self):
        """For the bell UI: show the real QB DocNumber if we got one, else a
        local fallback tag so the row still reads sensibly."""
        return self.qb_invoice_doc_number or f"LOCAL-{self.pk:04d}"


class QbSyncSnapshot(models.Model):
    """Cached read-only aggregates pulled from QuickBooks.

    We don't hit the QB API on every dashboard page load — it's too slow
    (each query is 500ms-2s) and would bump us into Intuit's ~500/min rate
    limit with multiple concurrent viewers. Instead, we refresh this row
    explicitly (via the dashboard's "Refresh from QuickBooks" button) or
    on a schedule, and the dashboard reads from here.

    Singleton: we only ever keep one row. Code enforcement, not a DB
    constraint — same pattern as QbConnection.

    Statuses:
      ok       — last pull succeeded. Values are authoritative.
      stale    — last pull failed but we have prior values. UI shows the
                 old numbers with a warning.
      offline  — QB isn't connected at all. Values may be zero.
    """

    STATUS_OK = "ok"
    STATUS_STALE = "stale"
    STATUS_OFFLINE = "offline"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_STALE, "Stale (last pull failed)"),
        (STATUS_OFFLINE, "QB not connected"),
    ]

    # Dollar total of all Payment objects whose TxnDate falls in the current
    # calendar month, summed in the realm's currency. Stored as Decimal so
    # the dashboard can format with thousands separators.
    payments_this_month = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    # When the pull ran. Displayed as "Last pull: ..." in the header.
    fetched_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_OFFLINE
    )
    # Short error message from the most recent failed pull, for debugging.
    last_error = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "QuickBooks Sync Snapshot"

    def __str__(self):
        if self.fetched_at:
            return f"QB snapshot @ {self.fetched_at:%Y-%m-%d %H:%M} ({self.status})"
        return "QB snapshot (never fetched)"
