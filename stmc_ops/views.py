import re
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import (
    ApplianceConfig,
    Branch,
    CraftsmanPreset,
    ExteriorRateCard,
    FloorPlanModel,
    InteriorRateCard,
    IslandAddon,
    PlanMetric,
    RoofAreaPreset,
    SlabAreaPreset,
)


def index(request):
    return redirect("login")


def login_view(request):
    return render(request, "login/index.html")


def sales_view(request):
    return redirect("sales_shell")


def _to_number(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        value = float(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if number.is_integer():
        return int(number)
    return round(number, 4)


def _build_seed_rates():
    sales = {
        "base": 12,
        "crawl": 3,
        "ssAdd": 2,
        "sidingAdd": 1.5,
        "steepAdd": 1.75,
        "stoneW": 24,
        "stoneO": 26,
        "stoneLift": 1500,
        "deck": 5,
        "tg": 5,
        "awning": 450,
        "cupola": 250,
        "bsmtWall": 10,
    }
    ctr = {
        "fSlab": {"u": 5.5, "o": 6},
        "fUp": {"u": 5.5, "o": 6},
        "fAttic": {"u": 4, "o": 4.5},
        "fPorch": {"u": 5.5, "o": 6},
        "fRafter": {"u": 6, "o": 6.5},
        "fBsmt": {"u": 7.5, "o": 8},
        "bsmtLf": 10,
        "deckRoof": {"u": 7, "o": 7.5},
        "awnU": 350,
        "awnO": 450,
        "r612": {"u": 1.3, "o": 1.3},
        "r812": {"u": 1.5, "o": 1.5},
        "ss": {"u": 2.5, "o": 2.5},
        "ss912": {"u": 2.8, "o": 2.8},
        "shing": {"u": 0.75, "o": 0.75},
        "osb": 0.5,
        "mWall": {"u": 1.5, "o": 1.5},
        "mCeil": {"u": 1.75, "o": 1.75},
        "bb": {"u": 3, "o": 3},
        "lph": {"u": 2, "o": 2},
        "vinyl": {"u": 1.5, "o": 1.5},
        "bw": {"u": 5.5, "o": 5.5},
        "sof": {"u": 5.5, "o": 5.5},
        "stone": {"u": 16, "o": 17},
        "dblD": 150,
        "sglD": 100,
        "dblW": 100,
        "sglW": 50,
        "s2s": 75,
        "s2d": 150,
        "cup": 125,
        "deckNR": 5.5,
        "trex": 1,
        "tgC": 2.25,
    }
    conc = {
        "types": {
            "4fiber": {1: 5, 2: 5.25, 3: 5.25},
            "6fiber": {1: 6.25, 2: 6.5, 3: 6.5},
            "4mono": {1: 8, 2: 8.5, 3: 9},
            "6mono": {1: 8.5, 2: 9, 3: 9.5},
        },
        "minF": 3500,
        "minM": 5500,
        "lp": 1750,
        "bp": 2500,
        "wire": 0.85,
        "rebar": 1.25,
        "foam": 9,
    }
    punch = 2500

    for rate in ExteriorRateCard.objects.all():
        key = rate.key
        value = _to_number(rate.rate)
        if key.startswith("sales_"):
            sales[key[6:]] = value
            continue
        if key.startswith("ctr_"):
            suffix = key[4:]
            if suffix.endswith("_u") or suffix.endswith("_o"):
                base_key, tier = suffix.rsplit("_", 1)
                if base_key not in ctr or not isinstance(ctr.get(base_key), dict):
                    ctr[base_key] = {}
                ctr[base_key][tier] = value
            else:
                ctr[suffix] = value
            continue
        if not key.startswith("conc_"):
            continue

        suffix = key[5:]
        type_match = re.match(r"^(4fiber|6fiber|4mono|6mono)_z([123])$", suffix)
        if type_match:
            conc_type = type_match.group(1)
            zone = int(type_match.group(2))
            conc.setdefault("types", {}).setdefault(conc_type, {})[zone] = value
            continue
        if suffix == "minF":
            conc["minF"] = value
        elif suffix == "minM":
            conc["minM"] = value
        elif suffix == "lp":
            conc["lp"] = value
        elif suffix == "bp":
            conc["bp"] = value
        elif suffix == "wire":
            conc["wire"] = value
        elif suffix == "rebar":
            conc["rebar"] = value
        elif suffix == "foam":
            conc["foam"] = value
        elif suffix == "punch":
            punch = value

    interior_rate_card = {}
    for rate in InteriorRateCard.objects.all():
        interior_rate_card[rate.key] = {
            "rate": _to_number(rate.rate),
            "unit": rate.unit,
            "driver": rate.driver,
            "label": rate.label,
        }

    return {
        "P": {"sales": sales, "ctr": ctr, "conc": conc, "punch": punch},
        "INT_RC": interior_rate_card,
    }


def _build_contract_seed_data():
    base = _build_seed_rates()

    slab_area_options = [
        "1st Floor Living Area",
        "2nd Floor Area",
        "Bonus Room",
        "Garage Area",
        "Carport Area",
        "Front Porch Area",
        "Back Porch Area",
        "Custom",
    ]

    branches = {}
    for branch in Branch.objects.all():
        branches[branch.key] = {
            "label": branch.label,
            "concRate": _to_number(branch.conc_rate),
            "miles": int(branch.default_miles),
            "zone": int(branch.zone),
        }

    plans = FloorPlanModel.objects.prefetch_related(
        "slab_presets",
        "roof_presets",
        "craftsman_presets",
        "plan_metrics",
    ).all()

    pm = {}
    md = {}
    rd = {}
    p10 = {}
    plan_metrics = {}
    int_contract = {}
    base_costs = {}
    models = {}
    pdf_files = {}
    craftsman = {}

    for plan in plans:
        name = plan.name
        slabs = list(plan.slab_presets.all())
        roofs = list(plan.roof_presets.all())

        pm[name] = {
            "st": _to_number(plan.stories),
            "ew": int(plan.ext_wall_sf),
            "dd": int(plan.dbl_doors),
            "sd": int(plan.sgl_doors),
            "dw": int(plan.dbl_windows),
            "sw": int(plan.sgl_windows),
        }
        md[name] = {
            "sqft": [{"n": row.area_name, "sf": int(row.sqft)} for row in slabs],
        }
        rd[name] = [{"n": row.area_name, "sf": int(row.sqft)} for row in roofs]
        p10[name] = _to_number(plan.p10_material)
        int_contract[name] = {"t": _to_number(plan.int_contract)}
        base_costs[name] = {
            "topLine": _to_number(plan.cabinet_top_line),
            "intContract": _to_number(plan.int_contract),
        }

        island_depth = _to_number(plan.island_depth)
        island_width = _to_number(plan.island_width)
        island_label = plan.island_label or f"{island_depth}' x {island_width}'"
        models[name] = {
            "pages": int(plan.pdf_pages),
            "cabinetryLF": plan.cabinetry_lf_display,
            "cabinetryLFNum": _to_number(plan.cabinetry_lf_num),
            "sqft": [{"area": int(row.sqft), "name": row.area_name} for row in slabs],
            "island": {
                "depth": island_depth,
                "width": island_width,
                "label": island_label,
            },
            "isCustom": bool(plan.is_custom),
        }
        if plan.pdf_filename:
            pdf_files[name] = plan.pdf_filename

        craft_entry = {"paint": {}, "stain": {}}
        for row in plan.craftsman_presets.all():
            craft_entry["paint"][row.area] = _to_number(row.paint_cost)
            craft_entry["stain"][row.area] = _to_number(row.stain_cost)
        craftsman[name] = craft_entry

        metric_entry = {}
        for metric in plan.plan_metrics.all():
            metric_value = _to_number(metric.value)
            if metric.key.startswith("Has ") or metric.key == "Power to Island":
                metric_entry[metric.key] = "Yes" if metric_value >= 1 else "No"
            else:
                metric_entry[metric.key] = metric_value
        plan_metrics[name] = metric_entry

    appliance_labels = {}
    appliance_costs = {}
    for item in ApplianceConfig.objects.all():
        appliance_labels[item.key] = item.label
        appliance_costs[item.key] = _to_number(item.cost)

    island_addon_labels = {}
    for addon in IslandAddon.objects.all():
        island_addon_labels[addon.key] = addon.label

    return {
        **base,
        "SA": slab_area_options,
        "PM": pm,
        "MD": md,
        "RD": rd,
        "P10": p10,
        "BRANCHES": branches,
        "PLAN_METRICS": plan_metrics,
        "INT_CONTRACT": int_contract,
        "BASE_COSTS": base_costs,
        "MODELS": models,
        "PDF_FILES": pdf_files,
        "CRAFTSMAN": craftsman,
        "APPLIANCE_LABELS": appliance_labels,
        "APPLIANCE_COSTS": appliance_costs,
        "ISLAND_ADDON_LABELS": island_addon_labels,
    }


def sales_shell_view(request):
    return render(
        request,
        "sales/shell/index.html",
        {
            "wizard_mode": "shell",
            "wizard_seed_data": _build_contract_seed_data(),
        },
    )


def sales_turnkey_view(request):
    return render(
        request,
        "sales/turnkey/index.html",
        {
            "wizard_mode": "turnkey",
            "wizard_seed_data": _build_contract_seed_data(),
        },
    )


def sales_contract_seed_data_view(request):
    return JsonResponse(_build_contract_seed_data())


def manager_view(request):
    return render(request, "manager/index.html")


def owner_view(request):
    return render(request, "owner/index.html")