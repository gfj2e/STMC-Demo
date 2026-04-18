"""
STMC Turnkey Estimator — Seed Model Presets
=============================================
Run: python manage.py seed_models

Seeds all 40 floor plan models with their complete data from:
PM, MD, RD, P10, MODELS, CRAFTSMAN, BASE_COSTS, PDF_FILES, INT_CONTRACT, PLAN_METRICS

Auto-generated from V7 HTML + INT_CONTRACTS_APP HTML source files.
"""

Yes = 1
No = 0

# Canonical alias map used by the wizard for legacy model names.
MODEL_ALIASES = {
    "BERKLEY": "THE BERKLEY",
    "DAUGHTERY": "DAUGHERTY",
    "EAST FORK": "EAST FORK DELUXE",
    "FOX RUN": "FOX RUN BARNDOMINIUM",
    "HADLEY": "THE HADLEY",
    "SHADY MEADOW": "SHADY MEADOWS",
    "THE SOUTHERN MONITOR": "SOUTHERN MONITOR",
    "TIMBERCREST": "TIMBER CREST",
    "WOODSIDE SPECIAL 2.0": "WOODSIDE SPECIAL DELUXE",
}

from django.core.management.base import BaseCommand
from stmc_ops.models import (
    FloorPlanModel, SlabAreaPreset, RoofAreaPreset, CraftsmanPreset, PlanMetric
)


class Command(BaseCommand):
    help = 'Seed all 40 floor plan model presets'

    def handle(self, *args, **options):
        self.seed_all_models()
        self.stdout.write(self.style.SUCCESS('All model presets seeded.'))

    def seed_all_models(self):
        count = 0

        # ── ARROWHEAD LODGE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="ARROWHEAD LODGE",
            defaults={
                "stories": 1.5,
                "ext_wall_sf": 2975,
                "dbl_doors": 3,
                "sgl_doors": 3,
                "dbl_windows": 0,
                "sgl_windows": 29,
                "p10_material": 156100,
                "cabinetry_lf_display": "59' - 0\"",
                "cabinetry_lf_num": 59,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 200970,
                "cabinet_top_line": 19470,
                "pdf_filename": "ARROWHEAD_LODGE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1882, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=845, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=580, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=580, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=3750, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=825, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=1112, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1011, stain_cost=1588)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=354, stain_cost=556)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=362, stain_cost=569)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2364)
        PlanMetric.objects.create(model=m, key="Stories", value=1.5)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=59)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Backsplash SF", value=30)
        PlanMetric.objects.create(model=m, key="Under-Cab Lights", value=4)
        PlanMetric.objects.create(model=m, key="Power to Island", value=Yes)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=98)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Half Bath Count", value=0)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=8)
        PlanMetric.objects.create(model=m, key="Total Closet SF", value=25)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=23)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=15)
        PlanMetric.objects.create(model=m, key="Window Openings", value=29)
        PlanMetric.objects.create(model=m, key="Window Area SF", value=455)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Loft/Bonus", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=Yes)
        PlanMetric.objects.create(model=m, key="Laundry Count", value=1)
        PlanMetric.objects.create(model=m, key="Bonus SF", value=482)
        count += 1

        # ── BLUEWATER ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="BLUEWATER",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1459,
                "dbl_doors": 0,
                "sgl_doors": 3,
                "dbl_windows": 2,
                "sgl_windows": 3,
                "p10_material": 43775,
                "cabinetry_lf_display": "33' - 6\"",
                "cabinetry_lf_num": 33.5,
                "island_depth": 3,
                "island_width": 9,
                "island_label": "3' x 9'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 107800,
                "cabinet_top_line": 11055,
                "pdf_filename": "BLUEWATER.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1232, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=84, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=140, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=1616, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=179, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=259, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1169, stain_cost=1835)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=279, stain_cost=438)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=268, stain_cost=420)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1232)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=33.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=27)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=93)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=17)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=17)
        PlanMetric.objects.create(model=m, key="Window Openings", value=5)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=12)
        count += 1

        # ── BROOKSIDE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="BROOKSIDE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1478,
                "dbl_doors": 0,
                "sgl_doors": 2,
                "dbl_windows": 0,
                "sgl_windows": 5,
                "p10_material": 36950,
                "cabinetry_lf_display": "42' - 0\"",
                "cabinetry_lf_num": 42,
                "island_depth": 3,
                "island_width": 5,
                "island_label": "3' x 5'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 105000,
                "cabinet_top_line": 13860,
                "pdf_filename": "BROOKSIDE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1200, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=240, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=24, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=1741, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=59, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=481, stain_cost=755)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=175, stain_cost=274)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=414, stain_cost=649)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1200)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=42)
        PlanMetric.objects.create(model=m, key="Island SF", value=15)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=78)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=12)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=12)
        PlanMetric.objects.create(model=m, key="Window Openings", value=5)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=8)
        count += 1

        # ── BUFFALO RUN ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="BUFFALO RUN",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2199,
                "dbl_doors": 2,
                "sgl_doors": 1,
                "dbl_windows": 3,
                "sgl_windows": 10,
                "p10_material": 81750,
                "cabinetry_lf_display": "41' - 6\"",
                "cabinetry_lf_num": 41.5,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 146400,
                "cabinet_top_line": 13695,
                "pdf_filename": "BUFFALO_RUN.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1460, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=404, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=72, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=253, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=2567, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=164, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=355, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=741, stain_cost=1163)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=157, stain_cost=247)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=214, stain_cost=336)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1460)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=41.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=15)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=65)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=40)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=17)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=12)
        PlanMetric.objects.create(model=m, key="Window Openings", value=13)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=8)
        count += 1

        # ── CAJUN ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="CAJUN",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1731,
                "dbl_doors": 1,
                "sgl_doors": 1,
                "dbl_windows": 2,
                "sgl_windows": 9,
                "p10_material": 71150,
                "cabinetry_lf_display": "44' - 0\"",
                "cabinetry_lf_num": 44,
                "island_depth": 4,
                "island_width": 8,
                "island_label": "4' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 162000,
                "cabinet_top_line": 14520,
                "pdf_filename": "CAJUN.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1800, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=480, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=750, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=480, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=2013, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=698, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=595, sort_order=2)
        RoofAreaPreset.objects.create(model=m, area_name="Carport Roof", sqft=962, sort_order=3)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=782, stain_cost=1227)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=103, stain_cost=162)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=219, stain_cost=343)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1800)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=44)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=80)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=15)
        PlanMetric.objects.create(model=m, key="Window Openings", value=11)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=10)
        count += 1

        # ── CEDAR RIDGE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="CEDAR RIDGE",
            defaults={
                "stories": 2,
                "ext_wall_sf": 4923,
                "dbl_doors": 2,
                "sgl_doors": 4,
                "dbl_windows": 0,
                "sgl_windows": 32,
                "p10_material": 193500,
                "cabinetry_lf_display": "65' - 3\"",
                "cabinetry_lf_num": 65.25,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 326100,
                "cabinet_top_line": 21533,
                "pdf_filename": "CEDAR_RIDGE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1976, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=1285, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=1200, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=2290, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2672, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=2743, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Garage Roof", sqft=1693, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=980, stain_cost=1538)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=238, stain_cost=374)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=428, stain_cost=672)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=777, stain_cost=1220)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=3261)
        PlanMetric.objects.create(model=m, key="Stories", value=2)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=65.25)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=5)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=216)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=80)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=29)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=20)
        PlanMetric.objects.create(model=m, key="Window Openings", value=34)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=28)
        PlanMetric.objects.create(model=m, key="Bonus SF", value=1285)
        count += 1

        # ── COTTONWOOD BEND ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="COTTONWOOD BEND",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2112,
                "dbl_doors": 2,
                "sgl_doors": 2,
                "dbl_windows": 2,
                "sgl_windows": 10,
                "p10_material": 110500,
                "cabinetry_lf_display": "36' - 7\"",
                "cabinetry_lf_num": 36.58,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 186390,
                "cabinet_top_line": 12071,
                "pdf_filename": "COTTONWOOD_BEND.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1962, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=720, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=655, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=3615, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=509, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=482, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=619, stain_cost=973)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=265, stain_cost=417)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1962)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=36.58)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=150)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=110)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=19)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=14)
        PlanMetric.objects.create(model=m, key="Window Openings", value=12)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=10)
        count += 1

        # ── CREEKSIDE SPECIAL ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="CREEKSIDE SPECIAL",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2556,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 0,
                "sgl_windows": 10,
                "p10_material": 87050,
                "cabinetry_lf_display": "53' - 0\"",
                "cabinetry_lf_num": 53,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 172800,
                "cabinet_top_line": 17490,
                "pdf_filename": "CREEKSIDE_SPECIAL.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1920, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=720, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=480, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=120, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2151, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Carport Roof", sqft=988, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=761, sort_order=2)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=275, sort_order=3)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=865, stain_cost=1358)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=115, stain_cost=180)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=364, stain_cost=572)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1920)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=53)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=15)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=13)
        PlanMetric.objects.create(model=m, key="Window Openings", value=10)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=10)
        count += 1

        # ── DAUGHERTY ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="DAUGHERTY",
            defaults={
                "stories": 2,
                "ext_wall_sf": 4516,
                "dbl_doors": 2,
                "sgl_doors": 5,
                "dbl_windows": 0,
                "sgl_windows": 19,
                "p10_material": 184250,
                "cabinetry_lf_display": "58' - 6\"",
                "cabinetry_lf_num": 58.5,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 274788,
                "cabinet_top_line": 19305,
                "pdf_filename": "DAUGHTERY.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1600, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=1005, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=2000, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=1092, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Porch & Garage", sqft=4420, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=1395, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Side Shed", sqft=819, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1180, stain_cost=1853)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=77, stain_cost=121)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=356, stain_cost=559)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=439, stain_cost=689)
        count += 1

        # ── EAST FORK DELUXE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="EAST FORK DELUXE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1636,
                "dbl_doors": 0,
                "sgl_doors": 2,
                "dbl_windows": 5,
                "sgl_windows": 3,
                "p10_material": 75550,
                "cabinetry_lf_display": "45' - 6\"",
                "cabinetry_lf_num": 45.5,
                "island_depth": 3,
                "island_width": 7,
                "island_label": "3' x 7'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 136500,
                "cabinet_top_line": 15015,
                "pdf_filename": "EAST_FORK.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1560, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=576, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=416, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=1903, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=556, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=679, stain_cost=1067)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=71, stain_cost=111)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=221, stain_cost=347)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1560)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=45.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=15)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=70)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=15)
        PlanMetric.objects.create(model=m, key="Window Openings", value=8)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=8)
        count += 1

        # ── FOX RUN BARNDOMINIUM ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="FOX RUN BARNDOMINIUM",
            defaults={
                "stories": 1,
                "ext_wall_sf": 0,
                "dbl_doors": 0,
                "sgl_doors": 0,
                "dbl_windows": 0,
                "sgl_windows": 0,
                "p10_material": 203500,
                "cabinetry_lf_display": "55' - 6\"",
                "cabinetry_lf_num": 55.5,
                "island_depth": 3,
                "island_width": 10,
                "island_label": "3' x 10'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 301600,
                "cabinet_top_line": 18315,
                "pdf_filename": "FOX_RUN.pdf",
            }
        )
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1459, stain_cost=2291)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=495, stain_cost=777)
        count += 1

        # ── FRANKS BARNDOMINIUM ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="FRANKS BARNDOMINIUM",
            defaults={
                "stories": 1.5,
                "ext_wall_sf": 4049,
                "dbl_doors": 2,
                "sgl_doors": 1,
                "dbl_windows": 6,
                "sgl_windows": 7,
                "p10_material": 149000,
                "cabinetry_lf_display": "64' - 0\"",
                "cabinetry_lf_num": 64,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 301600,
                "cabinet_top_line": 21120,
                "pdf_filename": "FRANKS_BARNDOMINIUM.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2495, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Bonus Room", sqft=521, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=700, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=1213, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=4872, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=1776, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1608, stain_cost=2525)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=238, stain_cost=374)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=1113, stain_cost=1748)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=3016)
        PlanMetric.objects.create(model=m, key="Stories", value=1.5)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=64)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=4)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=218)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=100)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=31)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=25)
        PlanMetric.objects.create(model=m, key="Window Openings", value=19)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=34)
        count += 1

        # ── HUNTLEY ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="HUNTLEY",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1737,
                "dbl_doors": 0,
                "sgl_doors": 2,
                "dbl_windows": 2,
                "sgl_windows": 8,
                "p10_material": 59500,
                "cabinetry_lf_display": "68' - 9\"",
                "cabinetry_lf_num": 68.75,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 151200,
                "cabinet_top_line": 22688,
                "pdf_filename": "HUNTLEY.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1680, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=448, sort_order=1)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=1949, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=701, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1201, stain_cost=1885)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=739, stain_cost=1160)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=531, stain_cost=833)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1680)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=68.75)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=110)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=14)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=15)
        PlanMetric.objects.create(model=m, key="Window Openings", value=10)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=18)
        count += 1

        # ── HUNTLEY 2.0 ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="HUNTLEY 2.0",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1539,
                "dbl_doors": 2,
                "sgl_doors": 1,
                "dbl_windows": 2,
                "sgl_windows": 8,
                "p10_material": 63075,
                "cabinetry_lf_display": "57' - 9\"",
                "cabinetry_lf_num": 57.75,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 151200,
                "cabinet_top_line": 19058,
                "pdf_filename": "HUNTLEY_2_0.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1680, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=448, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=448, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=2024, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=584, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=286, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=950, stain_cost=1491)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=548, stain_cost=860)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=295, stain_cost=464)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1680)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=57.75)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=93)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=15)
        PlanMetric.objects.create(model=m, key="Window Openings", value=10)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=10)
        count += 1

        # ── JOHNSON ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="JOHNSON",
            defaults={
                "stories": 2,
                "ext_wall_sf": 1774,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 3,
                "sgl_windows": 9,
                "p10_material": 74000,
                "cabinetry_lf_display": "53' - 3\"",
                "cabinetry_lf_num": 53.25,
                "island_depth": 0,
                "island_width": 0,
                "island_label": "No Island",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 153900,
                "cabinet_top_line": 17573,
                "pdf_filename": "JOHNSON.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1292, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=478, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=1560, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=1785, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=1888, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1449, stain_cost=2274)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=378, stain_cost=594)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1770)
        PlanMetric.objects.create(model=m, key="Stories", value=2)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=53.25)
        PlanMetric.objects.create(model=m, key="Island SF", value=0)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=108)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=12)
        PlanMetric.objects.create(model=m, key="Window Openings", value=12)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=18)
        count += 1

        # ── MAPLE GROVE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="MAPLE GROVE",
            defaults={
                "stories": 1.5,
                "ext_wall_sf": 3933,
                "dbl_doors": 2,
                "sgl_doors": 2,
                "dbl_windows": 5,
                "sgl_windows": 6,
                "p10_material": 126800,
                "cabinetry_lf_display": "55' - 6\"",
                "cabinetry_lf_num": 55.5,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 301200,
                "cabinet_top_line": 18315,
                "pdf_filename": "MAPLE_GROVE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2391, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Bonus Room", sqft=621, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=680, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=242, sort_order=3)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=552, sort_order=4)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=5701, sort_order=0)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=960, stain_cost=1507)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=705, stain_cost=1107)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=3012)
        PlanMetric.objects.create(model=m, key="Stories", value=1.5)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=55.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=130)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=70)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=27)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=26)
        PlanMetric.objects.create(model=m, key="Window Openings", value=20)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=Yes)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=28)
        count += 1

        # ── MARTIN LODGE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="MARTIN LODGE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2224,
                "dbl_doors": 1,
                "sgl_doors": 3,
                "dbl_windows": 2,
                "sgl_windows": 12,
                "p10_material": 94050,
                "cabinetry_lf_display": "74' - 0\"",
                "cabinetry_lf_num": 74,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 211680,
                "cabinet_top_line": 24420,
                "pdf_filename": "MARTIN_LODGE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2016, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=886, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=448, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=560, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House", sqft=3502, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=625, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=674, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1045, stain_cost=1641)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=557, stain_cost=875)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=235, stain_cost=369)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2016)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=74)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=112)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=18)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=11)
        PlanMetric.objects.create(model=m, key="Window Openings", value=14)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=12)
        count += 1

        # ── MEADOWS END ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="MEADOWS END",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2120,
                "dbl_doors": 2,
                "sgl_doors": 2,
                "dbl_windows": 2,
                "sgl_windows": 15,
                "p10_material": 99750,
                "cabinetry_lf_display": "73' - 6\"",
                "cabinetry_lf_num": 73.5,
                "island_depth": 3,
                "island_width": 9,
                "island_label": "3' x 9'",
                "pdf_pages": 1,
                "is_custom": False,
                "int_contract": 220300,
                "cabinet_top_line": 24255,
                "pdf_filename": "MEADOWS_END.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2130, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=570, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=200, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=560, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=3419, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=387, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=889, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1493, stain_cost=2344)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=234, stain_cost=368)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=1056, stain_cost=1657)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=404, stain_cost=636)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2130)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=73.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=27)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=167)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=110)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=19)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=14)
        PlanMetric.objects.create(model=m, key="Window Openings", value=17)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=15)
        count += 1

        # ── MINI PETTUS ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="MINI PETTUS",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2840,
                "dbl_doors": 3,
                "sgl_doors": 1,
                "dbl_windows": 5,
                "sgl_windows": 7,
                "p10_material": 100750,
                "cabinetry_lf_display": "66' - 7\"",
                "cabinetry_lf_num": 66.58,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 204600,
                "cabinet_top_line": 21971,
                "pdf_filename": "MINI_PETTUS.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2052, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=722, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=192, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=672, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=3758, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=330, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=872, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=698, stain_cost=1096)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=175, stain_cost=275)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=278, stain_cost=436)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=414, stain_cost=651)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2052)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=66.58)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=120)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=22)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=17)
        PlanMetric.objects.create(model=m, key="Window Openings", value=12)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=10)
        count += 1

        # ── NORTHVIEW LODGE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="NORTHVIEW LODGE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2794,
                "dbl_doors": 0,
                "sgl_doors": 3,
                "dbl_windows": 0,
                "sgl_windows": 16,
                "p10_material": 87350,
                "cabinetry_lf_display": "50' - 6\"",
                "cabinetry_lf_num": 50.5,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 172800,
                "cabinet_top_line": 16665,
                "pdf_filename": "NORTHVIEW_LODGE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1920, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=960, sort_order=1)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2432, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=593, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=577, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=953, stain_cost=1496)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=186, stain_cost=292)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=364, stain_cost=572)
        CraftsmanPreset.objects.create(model=m, area="other", paint_cost=941, stain_cost=1477)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1920)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=50.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=128)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=70)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=15)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=14)
        PlanMetric.objects.create(model=m, key="Window Openings", value=16)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=20)
        count += 1

        # ── PETTUS ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="PETTUS",
            defaults={
                "stories": 1,
                "ext_wall_sf": 3399,
                "dbl_doors": 1,
                "sgl_doors": 3,
                "dbl_windows": 1,
                "sgl_windows": 15,
                "p10_material": 124500,
                "cabinetry_lf_display": "115' - 9\"",
                "cabinetry_lf_num": 115.75,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 247296,
                "cabinet_top_line": 38198,
                "pdf_filename": "PETTUS.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2695, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=893, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=228, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=900, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=4639, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=434, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=1132, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1768, stain_cost=2776)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=1056, stain_cost=1657)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=877, stain_cost=1377)
        CraftsmanPreset.objects.create(model=m, area="other", paint_cost=117, stain_cost=184)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2695)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=115.75)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=188)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=158)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=19)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=16)
        PlanMetric.objects.create(model=m, key="Window Openings", value=16)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=28)
        count += 1

        # ── PINEY CREEK ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="PINEY CREEK",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1997,
                "dbl_doors": 1,
                "sgl_doors": 1,
                "dbl_windows": 6,
                "sgl_windows": 9,
                "p10_material": 79550,
                "cabinetry_lf_display": "62' - 3\"",
                "cabinetry_lf_num": 62.25,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 150480,
                "cabinet_top_line": 20543,
                "pdf_filename": "PINEY_CREEK.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1672, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=432, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=455, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House", sqft=2504, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=226, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=455, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=823, stain_cost=1292)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=238, stain_cost=374)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=377, stain_cost=591)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=264, stain_cost=415)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1672)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=62.25)
        PlanMetric.objects.create(model=m, key="Island SF", value=18)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=110)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=70)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=15)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=14)
        PlanMetric.objects.create(model=m, key="Window Openings", value=17)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=18)
        count += 1

        # ── RIDGECREST ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="RIDGECREST",
            defaults={
                "stories": 1,
                "ext_wall_sf": 0,
                "dbl_doors": 0,
                "sgl_doors": 0,
                "dbl_windows": 0,
                "sgl_windows": 0,
                "p10_material": 138150,
                "cabinetry_lf_display": "",
                "cabinetry_lf_num": 0,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 0,
                "cabinet_top_line": 0,
                "pdf_filename": "",
            }
        )
        count += 1

        # ── RIVERVIEW COTTAGE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="RIVERVIEW COTTAGE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 0,
                "dbl_doors": 0,
                "sgl_doors": 0,
                "dbl_windows": 0,
                "sgl_windows": 0,
                "p10_material": 71100,
                "cabinetry_lf_display": "18' - 6\"",
                "cabinetry_lf_num": 18.5,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 167670,
                "cabinet_top_line": 6105,
                "pdf_filename": "RIVERVIEW_COTTAGE.pdf",
            }
        )
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=651, stain_cost=1022)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=175, stain_cost=274)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=294, stain_cost=461)
        count += 1

        # ── ROBERTSON ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="ROBERTSON",
            defaults={
                "stories": 1,
                "ext_wall_sf": 3373,
                "dbl_doors": 2,
                "sgl_doors": 2,
                "dbl_windows": 0,
                "sgl_windows": 16,
                "p10_material": 112750,
                "cabinetry_lf_display": "43' - 3\"",
                "cabinetry_lf_num": 43.25,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 202500,
                "cabinet_top_line": 14273,
                "pdf_filename": "ROBERTSON.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2250, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=900, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=368, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=300, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=2775, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=521, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=360, sort_order=2)
        RoofAreaPreset.objects.create(model=m, area_name="Carport", sqft=1429, sort_order=3)
        RoofAreaPreset.objects.create(model=m, area_name="Dormers", sqft=138, sort_order=4)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=736, stain_cost=1156)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=210, stain_cost=329)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2250)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=43.25)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=128)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=27)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=16)
        PlanMetric.objects.create(model=m, key="Window Openings", value=16)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=26)
        count += 1

        # ── ROBERTSON DELUXE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="ROBERTSON DELUXE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 0,
                "dbl_doors": 0,
                "sgl_doors": 0,
                "dbl_windows": 0,
                "sgl_windows": 0,
                "p10_material": 113750,
                "cabinetry_lf_display": "",
                "cabinetry_lf_num": 0,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 0,
                "cabinet_top_line": 0,
                "pdf_filename": "",
            }
        )
        count += 1

        # ── ROCKY TOP ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="ROCKY TOP",
            defaults={
                "stories": 2,
                "ext_wall_sf": 3815,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 1,
                "sgl_windows": 14,
                "p10_material": 137000,
                "cabinetry_lf_display": "49' - 9\"",
                "cabinetry_lf_num": 49.75,
                "island_depth": 0,
                "island_width": 0,
                "island_label": "No Island",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 228144,
                "cabinet_top_line": 16418,
                "pdf_filename": "ROCKY_TOP.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1800, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=605, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=840, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=560, sort_order=3)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=224, sort_order=4)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=3732, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=886, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1392, stain_cost=2186)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=333, stain_cost=523)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2405)
        PlanMetric.objects.create(model=m, key="Stories", value=2)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=49.75)
        PlanMetric.objects.create(model=m, key="Island SF", value=0)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=98)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=8)
        PlanMetric.objects.create(model=m, key="Window Openings", value=21)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=14)
        PlanMetric.objects.create(model=m, key="Bonus SF", value=605)
        count += 1

        # ── SHADY MEADOWS ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="SHADY MEADOWS",
            defaults={
                "stories": 1,
                "ext_wall_sf": 0,
                "dbl_doors": 0,
                "sgl_doors": 2,
                "dbl_windows": 0,
                "sgl_windows": 4,
                "p10_material": 50625,
                "cabinetry_lf_display": "38' - 0\"",
                "cabinetry_lf_num": 38,
                "island_depth": 0,
                "island_width": 0,
                "island_label": "No Island",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 105000,
                "cabinet_top_line": 12540,
                "pdf_filename": "SHADY_MEADOW.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1200, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=576, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=240, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=24, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=1419, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=376, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Carport Roof", sqft=693, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=651, stain_cost=1022)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=175, stain_cost=274)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=294, stain_cost=461)
        count += 1

        # ── SOUTHERN MONITOR ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="SOUTHERN MONITOR",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2753,
                "dbl_doors": 1,
                "sgl_doors": 5,
                "dbl_windows": 6,
                "sgl_windows": 14,
                "p10_material": 103150,
                "cabinetry_lf_display": "90' - 6\"",
                "cabinetry_lf_num": 90.5,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 211850,
                "cabinet_top_line": 29865,
                "pdf_filename": "THE_SOUTHERN_MONITOR.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2235, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=200, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=365, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=3416, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=334, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1273, stain_cost=1999)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=1382, stain_cost=2169)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=531, stain_cost=833)
        count += 1

        # ── SUMMER BREEZE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="SUMMER BREEZE",
            defaults={
                "stories": 1.5,
                "ext_wall_sf": 4764,
                "dbl_doors": 2,
                "sgl_doors": 1,
                "dbl_windows": 3,
                "sgl_windows": 18,
                "p10_material": 151750,
                "cabinetry_lf_display": "77' - 11\"",
                "cabinetry_lf_num": 77.92,
                "island_depth": 3,
                "island_width": 7,
                "island_label": "3' x 7'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 365800,
                "cabinet_top_line": 25714,
                "pdf_filename": "SUMMER_BREEZE.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2891, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Bonus Room", sqft=767, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=768, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=477, sort_order=3)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=483, sort_order=4)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main House", sqft=4958, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=594, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Garage", sqft=1006, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1167, stain_cost=1833)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=408, stain_cost=640)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=597, stain_cost=937)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=706, stain_cost=1109)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=3658)
        PlanMetric.objects.create(model=m, key="Stories", value=1.5)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=77.92)
        PlanMetric.objects.create(model=m, key="Island SF", value=21)
        PlanMetric.objects.create(model=m, key="Bath Count", value=4)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=188)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=100)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=30)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=21)
        PlanMetric.objects.create(model=m, key="Window Openings", value=21)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=Yes)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=32)
        count += 1

        # ── THE BERKLEY ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="THE BERKLEY",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2079,
                "dbl_doors": 1,
                "sgl_doors": 3,
                "dbl_windows": 2,
                "sgl_windows": 4,
                "p10_material": 72000,
                "cabinetry_lf_display": "38' - 3\"",
                "cabinetry_lf_num": 38.25,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 148200,
                "cabinet_top_line": 12623,
                "pdf_filename": "BERKLEY.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1560, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=420, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=416, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2451, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=561, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=876, stain_cost=1375)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=238, stain_cost=374)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=265, stain_cost=417)
        count += 1

        # ── THE HADLEY ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="THE HADLEY",
            defaults={
                "stories": 2,
                "ext_wall_sf": 3768,
                "dbl_doors": 3,
                "sgl_doors": 2,
                "dbl_windows": 8,
                "sgl_windows": 8,
                "p10_material": 158500,
                "cabinetry_lf_display": "81' - 4\"",
                "cabinetry_lf_num": 81.33,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 342900,
                "cabinet_top_line": 26839,
                "pdf_filename": "HADLEY.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1911, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=1093, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=688, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=277, sort_order=3)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=624, sort_order=4)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=3985, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=266, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=1016, sort_order=2)
        RoofAreaPreset.objects.create(model=m, area_name="Side Entry", sqft=49, sort_order=3)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1411, stain_cost=2215)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=297, stain_cost=466)
        count += 1

        # ── THOMPSON ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="THOMPSON",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2930,
                "dbl_doors": 2,
                "sgl_doors": 1,
                "dbl_windows": 0,
                "sgl_windows": 14,
                "p10_material": 109000,
                "cabinetry_lf_display": "78' - 11\"",
                "cabinetry_lf_num": 78.92,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 228000,
                "cabinet_top_line": 26044,
                "pdf_filename": "THOMPSON.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2400, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=624, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=480, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=360, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=2897, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=714, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=644, sort_order=2)
        RoofAreaPreset.objects.create(model=m, area_name="Garage", sqft=855, sort_order=3)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=763, stain_cost=1198)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=109, stain_cost=171)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=245, stain_cost=385)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=510, stain_cost=801)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2400)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=78.92)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=3)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=131)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=60)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=21)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=18)
        PlanMetric.objects.create(model=m, key="Window Openings", value=14)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=20)
        count += 1

        # ── TIMBER CREST ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="TIMBER CREST",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1560,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 1,
                "sgl_windows": 12,
                "p10_material": 63325,
                "cabinetry_lf_display": "44' - 7\"",
                "cabinetry_lf_num": 44.58,
                "island_depth": 3,
                "island_width": 6,
                "island_label": "3' x 6'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 112350,
                "cabinet_top_line": 14711,
                "pdf_filename": "TIMBERCREST.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1284, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=180, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=216, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=1607, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=514, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=514, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=962, stain_cost=1510)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=234, stain_cost=368)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=277, stain_cost=434)
        count += 1

        # ── WESTVIEW MANOR ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="WESTVIEW MANOR",
            defaults={
                "stories": 2,
                "ext_wall_sf": 5059,
                "dbl_doors": 2,
                "sgl_doors": 3,
                "dbl_windows": 11,
                "sgl_windows": 17,
                "p10_material": 193750,
                "cabinetry_lf_display": "69' - 3\"",
                "cabinetry_lf_num": 69.25,
                "island_depth": 3,
                "island_width": 12,
                "island_label": "3' x 12'",
                "pdf_pages": 3,
                "is_custom": False,
                "int_contract": 353780,
                "cabinet_top_line": 22853,
                "pdf_filename": "WESTVIEW_MANOR.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1862, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="2nd Floor Area", sqft=1816, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Garage Area", sqft=638, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=1450, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=4039, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Porch Roof", sqft=1858, sort_order=1)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=586, stain_cost=920)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=172, stain_cost=270)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=105, stain_cost=164)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=654, stain_cost=1026)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=3678)
        PlanMetric.objects.create(model=m, key="Stories", value=2)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=69.25)
        PlanMetric.objects.create(model=m, key="Island SF", value=36)
        PlanMetric.objects.create(model=m, key="Bath Count", value=4)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=224)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=80)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=31)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=27)
        PlanMetric.objects.create(model=m, key="Window Openings", value=32)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=Yes)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=32)
        PlanMetric.objects.create(model=m, key="Bonus SF", value=1816)
        count += 1

        # ── WHISPERING PINES ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="WHISPERING PINES",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2095,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 0,
                "sgl_windows": 10,
                "p10_material": 79000,
                "cabinetry_lf_display": "53' - 9\"",
                "cabinetry_lf_num": 53.75,
                "island_depth": 3,
                "island_width": 5,
                "island_label": "3' x 5'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 180000,
                "cabinet_top_line": 17738,
                "pdf_filename": "WHISPERING_PINES.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=2000, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=128, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=900, sort_order=2)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=500, sort_order=3)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=3419, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=361, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=605, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1153, stain_cost=1810)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=194, stain_cost=304)
        CraftsmanPreset.objects.create(model=m, area="laundry", paint_cost=350, stain_cost=549)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=244, stain_cost=383)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=2000)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=53.75)
        PlanMetric.objects.create(model=m, key="Island SF", value=15)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=98)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=14)
        PlanMetric.objects.create(model=m, key="Window Openings", value=10)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=18)
        count += 1

        # ── WILLOW CREEK ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="WILLOW CREEK",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1706,
                "dbl_doors": 0,
                "sgl_doors": 3,
                "dbl_windows": 4,
                "sgl_windows": 3,
                "p10_material": 52130,
                "cabinetry_lf_display": "34' - 0\"",
                "cabinetry_lf_num": 34,
                "island_depth": 3,
                "island_width": 5,
                "island_label": "3' x 5'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 124950,
                "cabinet_top_line": 11220,
                "pdf_filename": "WILLOW_CREEK.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1428, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=128, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Carport Area", sqft=336, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="Main Roof", sqft=1759, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=240, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Carport Roof", sqft=437, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=651, stain_cost=1022)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=175, stain_cost=274)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=294, stain_cost=461)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1428)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=34)
        PlanMetric.objects.create(model=m, key="Island SF", value=12)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=78)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=16)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=12)
        PlanMetric.objects.create(model=m, key="Window Openings", value=7)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=8)
        count += 1

        # ── WOODSIDE SPECIAL ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="WOODSIDE SPECIAL",
            defaults={
                "stories": 1,
                "ext_wall_sf": 2499,
                "dbl_doors": 1,
                "sgl_doors": 1,
                "dbl_windows": 0,
                "sgl_windows": 16,
                "p10_material": 92000,
                "cabinetry_lf_display": "65' - 6\"",
                "cabinetry_lf_num": 65.5,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "3' x 8'",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 172800,
                "cabinet_top_line": 21615,
                "pdf_filename": "WOODSIDE_SPECIAL.pdf",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1920, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=480, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=480, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2427, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=587, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=567, sort_order=2)
        m.craftsman_presets.all().delete()
        CraftsmanPreset.objects.create(model=m, area="kitchen", paint_cost=1533, stain_cost=2407)
        CraftsmanPreset.objects.create(model=m, area="island", paint_cost=181, stain_cost=284)
        CraftsmanPreset.objects.create(model=m, area="baths", paint_cost=430, stain_cost=675)
        m.plan_metrics.all().delete()
        PlanMetric.objects.create(model=m, key="Total Living SF", value=1920)
        PlanMetric.objects.create(model=m, key="Stories", value=1)
        PlanMetric.objects.create(model=m, key="Cabinetry LF", value=65.5)
        PlanMetric.objects.create(model=m, key="Island SF", value=24)
        PlanMetric.objects.create(model=m, key="Bath Count", value=2)
        PlanMetric.objects.create(model=m, key="Bath Floor SF", value=115)
        PlanMetric.objects.create(model=m, key="Shower Wall SF", value=50)
        PlanMetric.objects.create(model=m, key="Total Door Openings", value=13)
        PlanMetric.objects.create(model=m, key="Interior Slabs", value=12)
        PlanMetric.objects.create(model=m, key="Window Openings", value=16)
        PlanMetric.objects.create(model=m, key="Has Stairs", value=No)
        PlanMetric.objects.create(model=m, key="Has Fireplace", value=No)
        PlanMetric.objects.create(model=m, key="Closet Shelving LF", value=14)
        count += 1

        # ── WOODSIDE SPECIAL DELUXE ──
        m, _ = FloorPlanModel.objects.update_or_create(
            name="WOODSIDE SPECIAL DELUXE",
            defaults={
                "stories": 1,
                "ext_wall_sf": 1740,
                "dbl_doors": 1,
                "sgl_doors": 2,
                "dbl_windows": 6,
                "sgl_windows": 10,
                "p10_material": 103000,
                "cabinetry_lf_display": "",
                "cabinetry_lf_num": 0,
                "island_depth": 3,
                "island_width": 8,
                "island_label": "",
                "pdf_pages": 2,
                "is_custom": False,
                "int_contract": 0,
                "cabinet_top_line": 0,
                "pdf_filename": "",
            }
        )
        m.slab_presets.all().delete()
        SlabAreaPreset.objects.create(model=m, area_name="1st Floor Living Area", sqft=1920, sort_order=0)
        SlabAreaPreset.objects.create(model=m, area_name="Front Porch Area", sqft=480, sort_order=1)
        SlabAreaPreset.objects.create(model=m, area_name="Back Porch Area", sqft=480, sort_order=2)
        m.roof_presets.all().delete()
        RoofAreaPreset.objects.create(model=m, area_name="House Roof", sqft=2427, sort_order=0)
        RoofAreaPreset.objects.create(model=m, area_name="Front Porch", sqft=587, sort_order=1)
        RoofAreaPreset.objects.create(model=m, area_name="Back Porch", sqft=567, sort_order=2)
        count += 1

        self.stdout.write(f"  Models seeded: {count}")
