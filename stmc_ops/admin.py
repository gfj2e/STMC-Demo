from django.contrib import admin
from .models import (
    AppUser, Branch,
    FloorPlanModel, SlabAreaPreset, RoofAreaPreset, CraftsmanPreset, PlanMetric,
    ExteriorRateCard, InteriorRateCard,
    BudgetTrade, BudgetTradeRate,
    UpgradeCategory, UpgradeSection, UpgradeItem,
    ApplianceConfig, IslandAddon,
    Job, JobDraw, JobTradeBudget,
    JobSlabRow, JobRoofRow, JobCustomCharge, JobContractorOverride,
    JobCraftsmanSelection, JobCustomCraftsmanRow,
    JobCabinetUpgrade, JobCabinetCustomLine, JobCountertopArea,
    JobUpgradeSelection, JobSelectionCustomLine, JobConcreteFinishLine,
    JobCustomUpgrade, JobCredit, JobBudgetLine,
)


# ═══════════════════════════════════════════════════════
# REFERENCE DATA — seed_data
# ═══════════════════════════════════════════════════════

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "conc_rate", "default_miles", "zone")
    search_fields = ("key", "label")


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("name", "user_id", "role", "title", "sort_order", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("name", "user_id")


@admin.register(ExteriorRateCard)
class ExteriorRateCardAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "category", "rate", "unit", "miles_tier")
    list_filter = ("category", "miles_tier")
    search_fields = ("label", "key")


@admin.register(InteriorRateCard)
class InteriorRateCardAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "rate", "unit", "driver")
    search_fields = ("label", "key", "driver")


class BudgetTradeRateInline(admin.TabularInline):
    model = BudgetTradeRate
    extra = 0
    raw_id_fields = ("rate_card",)


@admin.register(BudgetTrade)
class BudgetTradeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "scope", "sort_order", "has_base_cost")
    list_filter = ("scope",)
    search_fields = ("name", "key")
    inlines = [BudgetTradeRateInline]


@admin.register(ApplianceConfig)
class ApplianceConfigAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "cost", "sort_order")
    search_fields = ("label", "key")


@admin.register(IslandAddon)
class IslandAddonAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "cost")
    search_fields = ("label", "key")


# ═══════════════════════════════════════════════════════
# UPGRADE CATALOG — seed_data
# ═══════════════════════════════════════════════════════

class UpgradeSectionInline(admin.TabularInline):
    model = UpgradeSection
    extra = 0
    show_change_link = True


@admin.register(UpgradeCategory)
class UpgradeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "step", "sort_order")
    list_filter = ("step",)
    search_fields = ("name", "key")
    inlines = [UpgradeSectionInline]


class UpgradeItemInline(admin.TabularInline):
    model = UpgradeItem
    extra = 0
    fields = ("item_id", "label", "price", "input_type", "unit", "sort_order")


@admin.register(UpgradeSection)
class UpgradeSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "sort_order")
    list_filter = ("category",)
    search_fields = ("name",)
    inlines = [UpgradeItemInline]


@admin.register(UpgradeItem)
class UpgradeItemAdmin(admin.ModelAdmin):
    list_display = ("label", "item_id", "price", "input_type", "unit", "budget_trade", "sort_order")
    list_filter = ("input_type", "budget_trade")
    search_fields = ("label", "item_id")


# ═══════════════════════════════════════════════════════
# FLOOR PLAN MODELS — seed_models
# ═══════════════════════════════════════════════════════

class SlabAreaPresetInline(admin.TabularInline):
    model = SlabAreaPreset
    extra = 0
    fields = ("area_name", "sqft", "sort_order")


class RoofAreaPresetInline(admin.TabularInline):
    model = RoofAreaPreset
    extra = 0
    fields = ("area_name", "sqft", "sort_order")


class CraftsmanPresetInline(admin.TabularInline):
    model = CraftsmanPreset
    extra = 0
    fields = ("area", "paint_cost", "stain_cost")


class PlanMetricInline(admin.TabularInline):
    model = PlanMetric
    extra = 0
    fields = ("key", "value")


@admin.register(FloorPlanModel)
class FloorPlanModelAdmin(admin.ModelAdmin):
    list_display = ("name", "stories", "p10_material", "int_contract", "cabinetry_lf_num", "is_custom")
    list_filter = ("stories", "is_custom")
    search_fields = ("name",)
    inlines = [SlabAreaPresetInline, RoofAreaPresetInline, CraftsmanPresetInline, PlanMetricInline]


# ═══════════════════════════════════════════════════════
# JOBS & DRAWS — live contract data
# ═══════════════════════════════════════════════════════

class JobDrawInline(admin.TabularInline):
    model = JobDraw
    extra = 0
    fields = ("draw_number", "label", "amount", "status", "paid_date")


class JobTradeBudgetInline(admin.TabularInline):
    model = JobTradeBudget
    extra = 0
    fields = ("trade_name", "budgeted", "actual", "sort_order")


class JobSlabRowInline(admin.TabularInline):
    model = JobSlabRow
    extra = 0
    fields = ("area_name", "sqft", "tg_ceiling", "sort_order")


class JobRoofRowInline(admin.TabularInline):
    model = JobRoofRow
    extra = 0
    fields = ("area_name", "roof_type", "steep", "sqft", "sort_order")


class JobCustomChargeInline(admin.TabularInline):
    model = JobCustomCharge
    extra = 0
    fields = ("charge_type", "description", "rate", "unit", "qty")


class JobBudgetLineInline(admin.TabularInline):
    model = JobBudgetLine
    extra = 0
    fields = ("trade", "base_cost", "upgrade_adder", "credit_reduction", "total_budgeted")
    readonly_fields = ("trade", "total_budgeted")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name", "job_mode", "current_phase",
        "p10_material", "branch", "sales_rep", "order_number",
    )
    list_filter = ("job_mode", "current_phase", "branch")
    search_fields = ("customer_name", "customer_addr", "sales_rep", "order_number")
    readonly_fields = ("id",)
    fieldsets = (
        ("Customer", {
            "fields": ("customer_name", "customer_addr", "sales_rep", "order_number"),
        }),
        ("Project", {
            "fields": ("branch", "floor_plan", "job_mode", "current_phase"),
        }),
        ("Contract Amounts", {
            "fields": ("p10_material", "adjusted_int_contract", "budget_total_amount", "collected_amount"),
        }),
    )
    inlines = [JobDrawInline, JobTradeBudgetInline, JobSlabRowInline, JobRoofRowInline, JobCustomChargeInline, JobBudgetLineInline]


@admin.register(JobDraw)
class JobDrawAdmin(admin.ModelAdmin):
    list_display = ("job", "draw_number", "label", "amount", "status", "paid_date")
    list_filter = ("status",)
    search_fields = ("job__customer_name", "label")


@admin.register(JobTradeBudget)
class JobTradeBudgetAdmin(admin.ModelAdmin):
    list_display = ("job", "trade_name", "budgeted", "actual", "sort_order")
    list_filter = ("trade_name",)
    search_fields = ("job__customer_name", "trade_name")

    
