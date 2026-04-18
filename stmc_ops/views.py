import re
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import (
    ApplianceConfig,
    AppUser,
    BudgetTrade,
    Branch,
    CraftsmanPreset,
    ExteriorRateCard,
    FloorPlanModel,
    InteriorRateCard,
    IslandAddon,
    Job,
    PlanMetric,
    RoofAreaPreset,
    SlabAreaPreset,
    UpgradeCategory,
)
from .management.commands.seed_data import (
    WIZARD_CONC_TYPES,
    WIZARD_CONCRETE_FINISH_REFERENCE_PRICING,
    WIZARD_CUSTOM_TRADE_CATS,
    WIZARD_ROOF_AREA_NAMES,
    WIZARD_ROOF_TYPES,
)
from .management.commands.seed_models import MODEL_ALIASES


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


def _model_id_from_name(name):
    value = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return value or "custom_model"


def _build_interior_trade_groups():
    groups = []
    trades = BudgetTrade.objects.filter(scope="interior").order_by("sort_order", "name")
    for trade in trades:
        rates = [
            mapping.rate_card.key
            for mapping in trade.rate_mappings.select_related("rate_card").all().order_by("rate_card__key")
        ]
        groups.append({"key": trade.key, "name": trade.name, "rates": rates})
    return groups


def _build_selection_defs():
    # Build the Step 7 config from seeded upgrade catalog rows.
    type_map = {
        "toggle": "toggle",
        "qty": "qty",
        "sf": "sf",
        "lf": "lf",
        "radio": "radio",
    }
    wanted = ["docusign", "electrical", "plumbing", "trim"]
    categories = (
        UpgradeCategory.objects.filter(key__in=wanted)
        .prefetch_related("sections__items", "sections__items__budget_trade")
        .order_by("sort_order")
    )
    by_key = {cat.key: cat for cat in categories}

    defs = {}
    for key in wanted:
        cat = by_key.get(key)
        sections = []
        if cat:
            for section in cat.sections.all():
                if section.name == "Gas Type":
                    sections.append(
                        {
                            "title": "Gas Type",
                            "type": "radio",
                            "id": "gasType",
                            "options": [
                                {"v": "", "l": "-- Not Selected --"},
                                {"v": "natural", "l": "Natural Gas"},
                                {"v": "propane", "l": "Propane"},
                            ],
                        }
                    )
                    continue

                sec = {"title": section.name, "items": []}
                for item in section.items.all():
                    row = {
                        "id": item.item_id,
                        "type": type_map.get(item.input_type, "toggle"),
                        "label": item.label,
                        "price": _to_number(item.price),
                    }
                    if item.unit:
                        row["unit"] = item.unit
                    if item.budget_trade:
                        row["trade"] = item.budget_trade.key
                    if item.has_base_addon and _to_number(item.base_addon_amount) > 0:
                        row["baseAddOn"] = _to_number(item.base_addon_amount)
                    fp = _to_number(item.adds_fixture_points)
                    if fp > 0:
                        row["fp"] = fp
                    if item.is_split_budget:
                        row["special"] = "tankless"
                    sec["items"].append(row)
                sections.append(sec)

        defs[key] = {
            "label": cat.name if cat else key.title(),
            "sections": sections,
        }

    # Keep concrete finish reference pricing available for the Trim pill.
    trim_defs = defs.get("trim", {"label": "Trim", "sections": []})
    trim_defs["sections"].append(
        {
            "title": "Concrete Floor Finishes",
            "type": "concreteFinishLines",
            "referencePricing": WIZARD_CONCRETE_FINISH_REFERENCE_PRICING,
        }
    )
    defs["trim"] = trim_defs
    return defs


def _build_custom_trade_categories():
    # Filter to seeded interior trades that actually exist.
    valid_keys = set(BudgetTrade.objects.filter(scope="interior").values_list("key", flat=True))
    return [row for row in WIZARD_CUSTOM_TRADE_CATS if row["v"] in valid_keys]


def _format_money(value):
    amount = float(_to_number(value))
    return f"${amount:,.0f}"


def _clamp(number, low, high):
    return max(low, min(high, number))


def _build_users_data():
    users = []
    for user in AppUser.objects.filter(is_active=True).order_by("sort_order", "name"):
        users.append(
            {
                "id": user.user_id,
                "name": user.name,
                "initials": user.initials,
                "role": user.role,
                "title": user.title,
            }
        )
    if users:
        return users
    return [
        {
            "id": "derek",
            "name": "Derek Stoll",
            "initials": "DS",
            "role": "sales",
            "title": "Sales Rep",
        },
        {
            "id": "phillip",
            "name": "Phillip Olson",
            "initials": "PO",
            "role": "pm",
            "title": "Project Manager",
        },
        {
            "id": "matt",
            "name": "Matt Stoll",
            "initials": "MS",
            "role": "exec",
            "title": "Executive / Owner",
        },
    ]


def _build_regions_data():
    branches = Branch.objects.all().order_by("label")
    regions = []
    for branch in branches:
        regions.append(
            {
                "id": branch.key,
                "name": branch.label,
                "laborMultiplier": 1.0,
                "concreteMultiplier": 1.0,
                "turnkeyPremium": 0,
            }
        )
    return regions


def _build_sales_model_list():
    plans = FloorPlanModel.objects.prefetch_related("plan_metrics").all()
    model_rows = []
    for plan in plans:
        model_id = _model_id_from_name(plan.name)
        metrics = {metric.key: _to_number(metric.value) for metric in plan.plan_metrics.all()}
        living_sf = _to_number(metrics.get("Total Living SF", 0))
        turnkey_rate = round((_to_number(plan.int_contract) / living_sf), 1) if living_sf else 0
        model_rows.append(
            {
                "id": model_id,
                "name": plan.name,
                "livingSf": int(living_sf) if living_sf else 0,
                "materialTotal": _to_number(plan.p10_material),
                "laborBudget": _to_number(round(_to_number(plan.p10_material) * 0.42, 2)),
                "concreteBudget": _to_number(round((living_sf or 0) * 8.0, 2)),
                "turnkeyRate": _to_number(turnkey_rate),
            }
        )
    return model_rows


def _estimate_job_contract(job):
    material = _to_number(job.p10_material)
    if not material and job.floor_plan:
        material = _to_number(job.floor_plan.p10_material)

    int_part = 0
    if job.job_mode == "turnkey":
        int_part = _to_number(job.adjusted_int_contract) or _to_number(job.int_contract)
        if not int_part and job.floor_plan:
            int_part = _to_number(job.floor_plan.int_contract)
    return material + int_part


def _phase_tone(phase_code):
    if phase_code in {"punch", "final", "closed"}:
        return "success"
    if phase_code == "estimate":
        return "warning"
    return "warning"


def _draw_status_tone(status_code):
    if status_code in {"paid", "closed"}:
        return "success"
    if status_code == "hold":
        return "danger"
    return "warning"


def _progress_from_fields(job, budget_total, budget_spent):
    explicit = _to_number(job.progress_percent)
    if explicit > 0:
        return int(_clamp(round(explicit), 0, 100))
    if budget_total > 0:
        return int(_clamp(round((budget_spent / budget_total) * 100), 0, 100))
    return 0


def _build_manager_owner_data():
    jobs = list(Job.objects.select_related("floor_plan").order_by("-updated_at", "-created_at")[:12])

    pipeline = []
    budgets = []
    draws = []
    owner_projects = []
    owner_payments = []
    notifications = []

    contract_total = 0
    collected_total = 0
    awaiting_total = 0
    budget_health_scores = []

    for job in jobs:
        name = job.customer_name or f"Build #{job.id}"
        model = job.floor_plan.name if job.floor_plan else "Custom"
        contract = _estimate_job_contract(job)

        budget_total = _to_number(job.budget_total_amount)
        if budget_total <= 0:
            budget_total = _to_number(job.int_true_cost)
        if budget_total <= 0 and contract > 0:
            budget_total = round(contract * 0.48, 2)

        spent = _to_number(job.budget_spent_amount)
        if spent <= 0 and budget_total > 0 and _to_number(job.progress_percent) > 0:
            spent = round((budget_total * _to_number(job.progress_percent)) / 100.0, 2)
        spent = _clamp(spent, 0, budget_total) if budget_total > 0 else max(0, spent)

        progress = _progress_from_fields(job, budget_total, spent)
        remaining = max(0, round(budget_total - spent, 2))

        phase_code = job.current_phase or "estimate"
        phase = job.get_current_phase_display()
        phase_tone = _phase_tone(phase_code)

        draw_stage = job.get_draw_stage_display()
        draw_status = job.get_draw_status_display()
        draw_status_tone = _draw_status_tone(job.draw_status)
        draw_amount = _to_number(job.current_draw_amount)
        if draw_amount <= 0 and contract > 0:
            draw_amount = round(contract * 0.15, 2)

        collected = _to_number(job.collected_amount)
        if collected <= 0 and contract > 0 and progress > 0:
            collected = round((contract * progress) / 100.0, 2)
        collected = _clamp(collected, 0, contract) if contract > 0 else max(0, collected)

        margin = ((contract - budget_total) / contract * 100) if contract > 0 and budget_total > 0 else 0
        margin_pct = _to_number(round(margin, 1))
        margin_tone = "success" if margin >= 30 else ("warning" if margin >= 15 else "danger")
        collected_pct = int(_clamp(round((collected / contract) * 100), 0, 100)) if contract > 0 else 0

        if budget_total > 0:
            utilization = (spent / budget_total) * 100
            score = _clamp(100 - max(0, utilization - 100), 0, 100)
            budget_health_scores.append(score)

        contract_total += contract
        collected_total += collected
        awaiting_total += max(0, contract - collected)

        pipeline.append(
            {
                "build": name,
                "model": model,
                "phase": phase,
                "phaseTone": phase_tone,
                "contract": _format_money(contract),
            }
        )
        budgets.append(
            {
                "build": name,
                "spent": _format_money(spent),
                "total": _format_money(budget_total),
                "remaining": _format_money(remaining),
                "progress": progress,
            }
        )

        draws.append(
            {
                "build": name,
                "currentDraw": draw_stage,
                "status": draw_status,
                "statusTone": draw_status_tone,
                "amount": _format_money(draw_amount),
            }
        )

        owner_projects.append(
            {
                "project": name,
                "pm": "P. Olson",
                "contract": _format_money(contract),
                "margin": f"{_to_number(margin_pct)}%",
                "marginTone": margin_tone,
            }
        )
        owner_payments.append(
            {
                "project": name,
                "collectedPercent": collected_pct,
            }
        )
        notifications.append(
            {
                "title": "Draw update",
                "message": f"{name}: {draw_stage} is {draw_status.lower()}.",
                "tone": draw_status_tone,
            }
        )

    active_builds = len(jobs)
    avg_budget_health = (sum(budget_health_scores) / len(budget_health_scores)) if budget_health_scores else 0
    draws_pending = sum(1 for item in draws if item["status"] == "Current")
    budget_health = _to_number(round(avg_budget_health, 0))

    manager = {
        "kpis": [
            {"label": "My builds", "value": str(active_builds), "mono": True},
            {
                "label": "Budget health",
                "value": f"{int(budget_health)}%",
                "tone": "success" if budget_health >= 70 else "warning",
            },
            {"label": "Draws pending", "value": str(draws_pending), "tone": "warning" if draws_pending else "success"},
        ],
        "pipeline": pipeline,
        "budgets": budgets,
        "draws": draws,
    }

    owner = {
        "kpis": [
            {"label": "Active builds", "value": str(active_builds), "mono": True},
            {"label": "Contract value", "value": _format_money(contract_total), "mono": True},
            {"label": "Collected", "value": _format_money(collected_total), "mono": True, "tone": "success"},
            {"label": "Awaiting", "value": _format_money(awaiting_total), "mono": True, "tone": "warning"},
        ],
        "notifications": notifications[:3] if notifications else [
            {"title": "No active builds", "message": "Start a new job to populate owner dashboard data.", "tone": "brand"}
        ],
        "projects": owner_projects,
        "payments": owner_payments,
    }

    return manager, owner


def _build_app_seed_data():
    users = _build_users_data()
    regions = _build_regions_data()
    manager, owner = _build_manager_owner_data()

    return {
        "users": users,
        "regions": regions,
        "sales": {
            "rateCardVersion": timezone.now().strftime("%Y-%m"),
            "wizard": {
                "models": _build_sales_model_list(),
            },
        },
        "manager": manager,
        "owner": owner,
    }


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
        "MODEL_ALIASES": MODEL_ALIASES,
        "ROOF_AREA_NAMES": WIZARD_ROOF_AREA_NAMES,
        "ROOF_TYPES": WIZARD_ROOF_TYPES,
        "CONC_TYPES": WIZARD_CONC_TYPES,
        "INT_TRADE_GROUPS": _build_interior_trade_groups(),
        "SEL_DEFS": _build_selection_defs(),
        "CUSTOM_TRADE_CATS": _build_custom_trade_categories(),
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


def app_seed_data_view(request):
    return JsonResponse(_build_app_seed_data())


def manager_view(request):
    return render(request, "manager/index.html")


def owner_view(request):
    return render(request, "owner/index.html")