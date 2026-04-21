import re
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
    JobDraw,
    JobTradeBudget,
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
    if phase_code in {"framing", "roughin", "siding", "roofing"}:
        return "success"
    if phase_code == "estimate":
        return "muted"
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
    jobs = list(
        Job.objects.select_related("floor_plan")
        .prefetch_related("demo_trade_budgets", "demo_draws")
        .order_by("order_number")[:12]
    )

    projects = []
    contract_total = 0
    collected_total = 0
    awaiting_total = 0
    budget_health_scores = []

    for job in jobs:
        name = job.customer_name or f"Build #{job.id}"
        model_name = job.floor_plan.name if job.floor_plan else "Custom"
        customer_display = job.customer_addr or name
        pm_name = job.sales_rep or "P. Olson"
        phase = job.current_phase

        # Trade budgets from DB
        bg = {}
        ac = {}
        for tb in job.demo_trade_budgets.all():
            bg[tb.trade_name] = int(tb.budgeted)
            ac[tb.trade_name] = int(tb.actual)

        budget_total = sum(bg.values()) if bg else _to_number(job.budget_total_amount)
        budget_spent = sum(ac.values()) if ac else _to_number(job.budget_spent_amount)

        # Draw schedule from DB
        dr = []
        for draw in job.demo_draws.all():
            dr.append({
                "n": draw.draw_number,
                "l": draw.label,
                "a": int(draw.amount),
                "s": draw.status,
                "t": draw.paid_date,
            })

        # Contract total = sum of all draws
        contract = int(sum(d["a"] for d in dr)) if dr else _to_number(_estimate_job_contract(job))
        collected = int(sum(d["a"] for d in dr if d["s"] == "p")) if dr else _to_number(job.collected_amount)

        if budget_total > 0:
            utilization = (budget_spent / budget_total) * 100
            score = _clamp(100 - max(0, utilization - 100), 0, 100)
            budget_health_scores.append(score)

        contract_total += contract
        collected_total += collected
        awaiting_total += max(0, contract - collected)

        projects.append({
            "id": job.id,
            "nm": name,
            "md": model_name,
            "cu": customer_display,
            "ph": phase,
            "pm": pm_name,
            "ct": contract,
            "bg": bg,
            "ac": ac,
            "dr": dr,
        })

    active_builds = sum(1 for p in projects if p["ph"] != "closed")
    # Recalculate totals from active projects only
    contract_total = sum(p["ct"] for p in projects if p["ph"] != "closed")
    collected_total = sum(sum(d["a"] for d in p["dr"] if d["s"] == "p") for p in projects if p["ph"] != "closed")
    awaiting_total = sum(max(0, p["ct"] - sum(d["a"] for d in p["dr"] if d["s"] == "p")) for p in projects if p["ph"] != "closed")
    avg_budget_health = (sum(budget_health_scores) / len(budget_health_scores)) if budget_health_scores else 0
    draws_pending = sum(
        1 for p in projects if any(d["s"] == "c" for d in p["dr"])
    )
    budget_health_pct = int(round(avg_budget_health, 0))
    if budget_health_pct >= 80:
        budget_health_label = "On Track"
        budget_health_tone = "success"
    elif budget_health_pct >= 50:
        budget_health_label = "At Risk"
        budget_health_tone = "warning"
    else:
        budget_health_label = "Over Budget"
        budget_health_tone = "danger"

    # Build notifications from current draws
    notifications = []
    for p in projects[:3]:
        cur_draw = next((d for d in p["dr"] if d["s"] == "c"), None)
        if cur_draw:
            notifications.append({
                "title": "Draw ready",
                "message": f"{p['nm']}: {cur_draw['l']} ready — {_format_money(cur_draw['a'])}.",
                "tone": "brand",
            })

    manager = {
        "kpis": [
            {"label": "My builds", "value": str(active_builds)},
            {"label": "Budget health", "value": budget_health_label, "tone": budget_health_tone, "sm": True},
            {"label": "Draws pending", "value": str(draws_pending), "tone": "warning" if draws_pending else "success"},
        ],
        "projects": projects,
    }

    owner = {
        "kpis": [
            {"label": "Active builds", "value": str(active_builds)},
            {"label": "Contract value", "value": _format_money(contract_total)},
            {"label": "Collected", "value": _format_money(collected_total), "tone": "success"},
            {"label": "Awaiting", "value": _format_money(awaiting_total), "tone": "warning"},
        ],
        "notifications": notifications if notifications else [
            {"title": "No active builds", "message": "Start a new job to populate owner dashboard data.", "tone": "brand"},
        ],
        "projects": projects,
    }

    return manager, owner


def _build_simple_rate_card():
    """Simplified exterior+interior rate card for the Sales rate card tab."""
    exterior = []
    interior = []

    # Simplified contractor exterior rates used in the estimator
    ext_keys = [
        ("ctr_fSlab_u", "Framing — Slab", "Framing", "e"),
        ("ctr_fPorch_u", "Framing — Porch", "Framing", "e"),
        ("ctr_r612_u", "Roof Metal", "Roofing", "e"),
        ("ctr_osb", "Roof Sheathing", "Roofing", "e"),
        ("ctr_mWall_u", "Wall Metal", "Siding", "e"),
        ("ctr_sof_u", "Soffit", "Ext Trim", "e"),
        ("ctr_bw_u", "Beam Wrap", "Ext Trim", "e"),
        ("ctr_sglD", "Ext Door Install", "D&W", "e"),
        ("ctr_sglW", "Window Install", "D&W", "e"),
    ]
    int_keys = [
        ("cabinets", "Cabinets", "Cabinets", "i"),
        ("countertops", "Countertops", "Cabinets", "i"),
        ("floorMat", "Flooring Material", "Flooring", "i"),
        ("floorLab", "Flooring Install", "Flooring", "i"),
        ("drywallMat", "Drywall Material", "Drywall", "i"),
        ("drywallLab", "Drywall Labor", "Drywall", "i"),
        ("paint", "Paint", "Paint", "i"),
        ("trimMat", "Trim Material", "Trim", "i"),
        ("doorMat", "Interior Doors", "Trim", "i"),
        ("trimDoorLab", "Trim Install Labor", "Trim", "i"),
        ("electrical", "Electrical", "Electrical", "i"),
        ("plumbingLab", "Plumbing", "Plumbing", "i"),
        ("insulation", "Insulation", "Insulation", "i"),
        ("hvac", "HVAC", "HVAC", "i"),
        ("permits", "Permits", "General", "i"),
        ("cleaning", "Cleaning", "General", "i"),
        ("dumpster", "Dumpster", "General", "i"),
    ]

    ext_rate_map = {r.key: r for r in ExteriorRateCard.objects.filter(
        key__in=[k[0] for k in ext_keys]
    )}
    int_rate_map = {r.key: r for r in InteriorRateCard.objects.filter(
        key__in=[k[0] for k in int_keys]
    )}

    for key, label, group, _ in ext_keys:
        rc = ext_rate_map.get(key)
        exterior.append({
            "l": label,
            "g": group,
            "r": _to_number(rc.rate) if rc else 0,
            "u": f"/{rc.unit}" if rc and rc.unit not in ("flat",) else "flat",
        })

    for key, label, group, _ in int_keys:
        rc = int_rate_map.get(key)
        interior.append({
            "l": label,
            "g": group,
            "r": _to_number(rc.rate) if rc else 0,
            "u": rc.unit if rc else "/SF",
        })

    return {"exterior": exterior, "interior": interior}


def _build_app_seed_data():
    users = _build_users_data()
    regions = _build_regions_data()
    manager, owner = _build_manager_owner_data()
    rate_card = _build_simple_rate_card()

    return {
        "users": users,
        "regions": regions,
        "sales": {
            "rateCardVersion": timezone.now().strftime("%Y-%m"),
            "models": _build_sales_model_list(),
            "rateCard": rate_card,
            "projects": manager["projects"],  # Sales reps see same jobs list
        },
        "manager": manager,
        "owner": owner,
    }


def _draw_status_pill_class(status_code):
    if status_code == JobDraw.STATUS_PAID:
        return "pill-success"
    if status_code == JobDraw.STATUS_CURRENT:
        return "pill-brand"
    return "pill-muted"


def _draw_status_label(status_code):
    if status_code == JobDraw.STATUS_PAID:
        return "Paid"
    if status_code == JobDraw.STATUS_CURRENT:
        return "Due"
    return "Pending"


def _draw_num_class(status_code):
    if status_code == JobDraw.STATUS_PAID:
        return "paid"
    if status_code == JobDraw.STATUS_CURRENT:
        return "current"
    return ""


def _phase_pill_class(phase_code):
    phase = (phase_code or "").lower()
    if phase in {"framing", "roughin", "roofing", "siding", "punch", "complete", "final", "closed"}:
        return "pill-success"
    if phase in {"interior", "paint"}:
        return "pill-warning"
    return "pill-muted"


def _phase_label(phase_code):
    labels = {
        "estimate": "Estimate",
        "framing": "Framing",
        "roughin": "Rough-In",
        "interior": "Interior",
        "punch": "Punch",
        "final": "Final",
        "closed": "Closed",
        "roofing": "Roofing",
        "siding": "Siding",
        "paint": "Paint",
        "complete": "Complete",
    }
    return labels.get((phase_code or "").lower(), phase_code or "Estimate")


def _draw_timeline_row(draw):
    status = draw.get("s")
    icon = "✓" if status == JobDraw.STATUS_PAID else ("►" if status == JobDraw.STATUS_CURRENT else ("D" if draw.get("n") == 0 else str(draw.get("n") or "")))
    dot_class = "pdg" if status == JobDraw.STATUS_PAID else ("pdb" if status == JobDraw.STATUS_CURRENT else "pdx")
    status_color = "var(--green)" if status == JobDraw.STATUS_PAID else ("#1D4ED8" if status == JobDraw.STATUS_CURRENT else "var(--g400)")
    status_label = "Paid" + (f" {draw.get('t')}" if draw.get("t") else "") if status == JobDraw.STATUS_PAID else ("Current" if status == JobDraw.STATUS_CURRENT else "Pending")
    return {
        "icon": icon,
        "dot_class": dot_class,
        "label": draw.get("l", ""),
        "paid_date": draw.get("t") if status == JobDraw.STATUS_PAID else "",
        "amount_display": _format_money(draw.get("a", 0)),
        "status_color": status_color,
        "status_label": status_label,
    }


def _kpi_value_class(kpi):
    tone = kpi.get("tone")
    value_class = "kpi-val"
    if kpi.get("sm"):
        value_class += " kpi-val-sm"
    if tone:
        value_class += f" tone-{tone}"
    return value_class


def _build_project_ui_rows(projects):
    rows = []
    for project in projects:
        draws = project.get("dr", [])
        total = int(project.get("ct") or 0)
        paid = int(sum(d.get("a", 0) for d in draws if d.get("s") == JobDraw.STATUS_PAID))
        remaining = max(0, total - paid)
        pct = int(round((paid / total) * 100)) if total > 0 else 0
        current_draw = next((d for d in draws if d.get("s") == JobDraw.STATUS_CURRENT), None)

        draw_rows = []
        timeline_rows = []
        for draw in draws:
            status = draw.get("s")
            timeline_rows.append(_draw_timeline_row(draw))
            draw_rows.append(
                {
                    "draw_number": draw.get("n"),
                    "draw_number_display": "D" if draw.get("n") == 0 else draw.get("n"),
                    "label": draw.get("l", ""),
                    "date": draw.get("t") or "-",
                    "amount_display": _format_money(draw.get("a", 0)),
                    "status": status,
                    "draw_num_class": _draw_num_class(status),
                    "pill_class": _draw_status_pill_class(status),
                    "status_label": _draw_status_label(status),
                    "is_placeholder_date": not bool(draw.get("t")),
                }
            )

        trades = list((project.get("bg") or {}).keys())
        trade_rows = []
        total_bg = 0
        total_ac = 0
        for trade in trades:
            budget = int((project.get("bg") or {}).get(trade, 0) or 0)
            actual = int((project.get("ac") or {}).get(trade, 0) or 0)
            variance = budget - actual
            total_bg += budget
            total_ac += actual
            trade_rows.append(
                {
                    "trade": trade,
                    "budget_display": _format_money(budget),
                    "actual_display": _format_money(actual),
                    "variance_display": _format_money(variance),
                    "is_over": actual > budget,
                }
            )

        margin_pct = int(round(((total - total_bg) / total) * 100, 0)) if total > 0 and total_bg > 0 else 0
        margin_color = "var(--green)" if margin_pct >= 30 else ("var(--amber)" if margin_pct >= 15 else "#DC2626")

        current_draw_label = ""
        if current_draw and current_draw.get("l"):
            current_draw_label = re.sub(r"^\d+\w*\s*[\u2014\-]\s*", "", current_draw.get("l") or "")

        subtitle = f"{project.get('md', '')} · {project.get('cu', '')} · PM: {project.get('pm', '')}"

        rows.append(
            {
                "id": project.get("id"),
                "name": project.get("nm", ""),
                "phase": project.get("ph", "estimate"),
                "phase_label": _phase_label(project.get("ph", "estimate")),
                "phase_pill_class": _phase_pill_class(project.get("ph", "estimate")),
                "subtitle": subtitle,
                "total_amount": total,
                "total_display": _format_money(total),
                "paid_display": _format_money(paid),
                "remaining_display": _format_money(remaining),
                "pct": max(0, min(100, pct)),
                "draws": draw_rows,
                "timeline_draws": timeline_rows,
                "trades": trade_rows,
                "total_bg": total_bg,
                "total_ac": total_ac,
                "total_bg_display": _format_money(total_bg),
                "total_ac_display": _format_money(total_ac),
                "total_rem_display": _format_money(total_bg - total_ac),
                "total_rem_negative": (total_bg - total_ac) < 0,
                "margin_pct": margin_pct,
                "margin_color": margin_color,
                "current_draw": {
                    "label": current_draw.get("l") if current_draw else "",
                    "step_label": current_draw_label,
                    "number": current_draw.get("n") if current_draw else None,
                }
                if current_draw
                else None,
            }
        )
    return rows


def _build_owner_ui_context():
    _, owner = _build_manager_owner_data()
    projects = owner.get("projects", [])
    rows = _build_project_ui_rows(projects)

    active_projects = [p for p in rows if p["phase"] != "closed"]
    closed_projects = [p for p in rows if p["phase"] == "closed"]

    notif_tone_class = {"brand": "", "success": "tone-success", "warning": "tone-warning"}
    notifications = []
    for notif in owner.get("notifications", []):
        tone = notif.get("tone", "brand")
        tone_class = notif_tone_class.get(tone, "")
        notifications.append(
            {
                "title": notif.get("title", ""),
                "message": notif.get("message", ""),
                "time": notif.get("time", ""),
                "tone_class": tone_class,
            }
        )

    kpis = []
    owner_total = "—"
    for kpi in owner.get("kpis", []):
        kpis.append({
            "label": kpi.get("label", ""),
            "value": kpi.get("value", ""),
            "value_class": _kpi_value_class(kpi),
        })
        if kpi.get("label") == "Contract value":
            owner_total = kpi.get("value", "—")

    return {
        "kpis": kpis,
        "owner_total": owner_total,
        "notifications": notifications,
        "notif_count": len(notifications),
        "dashboard_active_projects": active_projects,
        "dashboard_closed_projects": closed_projects,
        "dashboard_active_count": len(active_projects),
        "all_projects_active": active_projects,
        "all_projects_closed": closed_projects,
        "active_projects": active_projects,
        "closed_projects": closed_projects,
    }


def _build_manager_ui_context():
    manager, _ = _build_manager_owner_data()
    rows = _build_project_ui_rows(manager.get("projects", []))
    active_projects = [p for p in rows if p["phase"] != "closed"]
    closed_projects = [p for p in rows if p["phase"] == "closed"]

    kpis = []
    for kpi in manager.get("kpis", []):
        kpis.append(
            {
                "label": kpi.get("label", ""),
                "value": kpi.get("value", ""),
                "value_class": _kpi_value_class(kpi),
            }
        )

    return {
        "kpis": kpis,
        "builds_active": active_projects,
        "builds_closed": closed_projects,
        "budgets_active": active_projects,
        "budgets_closed": closed_projects,
        "draws_active": active_projects,
        "draws_closed": closed_projects,
    }


def _build_sales_ui_context():
    manager, _ = _build_manager_owner_data()
    project_rows = _build_project_ui_rows(manager.get("projects", []))
    active_projects = [p for p in project_rows if p["phase"] != "closed"]
    closed_projects = [p for p in project_rows if p["phase"] == "closed"]

    models = []
    for model in _build_sales_model_list():
        material_total = int(_to_number(model.get("materialTotal", 0)))
        labor_budget = int(_to_number(model.get("laborBudget", 0)))
        concrete_budget = int(_to_number(model.get("concreteBudget", 0)))
        living_sf = int(_to_number(model.get("livingSf", 0)))
        total = material_total + labor_budget + concrete_budget
        per_sf = int(round(total / living_sf, 0)) if living_sf > 0 else 0
        models.append(
            {
                "name": model.get("name", ""),
                "living_sf": living_sf,
                "total_display": _format_money(total),
                "per_sf_display": f"${per_sf}/SF",
            }
        )
    models.sort(key=lambda row: row["living_sf"])

    rate_card = _build_simple_rate_card()
    exterior_rates = []
    for rate in rate_card.get("exterior", []):
        exterior_rates.append(
            {
                "group": rate.get("g", ""),
                "label": rate.get("l", ""),
                "rate_display": "--"
                if not rate.get("r")
                else f"${float(rate.get('r', 0)):,.2f}",
                "unit": rate.get("u", "--"),
            }
        )

    interior_rates = []
    for rate in rate_card.get("interior", []):
        interior_rates.append(
            {
                "group": rate.get("g", ""),
                "label": rate.get("l", ""),
                "rate_display": "--"
                if not rate.get("r")
                else f"${float(rate.get('r', 0)):,.2f}",
                "unit": rate.get("u", "--"),
            }
        )

    active_contract_total = sum(project.get("total_amount", 0) for project in active_projects)

    return {
        "sales_total": _format_money(active_contract_total),
        "kpis": [
            {
                "label": "Active builds",
                "value": str(len(active_projects)),
                "value_class": "kpi-val",
            }
        ],
        "projects_active": active_projects,
        "projects_closed": closed_projects,
        "models": models,
        "exterior_rates": exterior_rates,
        "interior_rates": interior_rates,
    }


def _mark_draw_complete(job_id, draw_number):
    draw = JobDraw.objects.get(job_id=job_id, draw_number=draw_number)

    dt = timezone.now()
    today = dt.strftime("%b ") + str(dt.day)

    draw.status = JobDraw.STATUS_PAID
    draw.paid_date = today
    draw.save(update_fields=["status", "paid_date"])

    next_draw = JobDraw.objects.filter(
        job_id=job_id, status=JobDraw.STATUS_PENDING
    ).order_by("draw_number").first()

    DRAW_PHASE_MAP = {
        1: "framing",
        2: "framing",
        3: "roughin",
        4: "interior",
        5: "punch",
        6: "final",
    }

    if next_draw:
        next_draw.status = JobDraw.STATUS_CURRENT
        next_draw.save(update_fields=["status"])
        new_phase = DRAW_PHASE_MAP.get(next_draw.draw_number)
    else:
        new_phase = "closed"

    if new_phase:
        Job.objects.filter(pk=job_id).update(current_phase=new_phase)

    return today


@csrf_exempt
def mark_draw_complete_view(request):
    """POST {job_id, draw_number} — marks the draw paid, advances next pending draw to current."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body)
        job_id = int(body["job_id"])
        draw_number = int(body["draw_number"])
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Invalid payload"}, status=400)

    try:
        draw = JobDraw.objects.get(job_id=job_id, draw_number=draw_number)
    except JobDraw.DoesNotExist:
        return JsonResponse({"error": "Draw not found"}, status=404)

    today = _mark_draw_complete(job_id, draw_number)

    return JsonResponse({"ok": True, "paid_date": today})


def owner_dashboard_panel_view(request):
    if not request.htmx:
        return redirect("owner")
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/dashboard.html",
        {
            "notifications": context["notifications"],
            "notif_count": context["notif_count"],
            "dashboard_active_projects": context["dashboard_active_projects"],
            "dashboard_closed_projects": context["dashboard_closed_projects"],
            "dashboard_active_count": context["dashboard_active_count"],
        },
    )


def owner_all_projects_panel_view(request):
    if not request.htmx:
        return redirect("owner")
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/all_projects.html",
        {
            "all_projects_active": context["all_projects_active"],
            "all_projects_closed": context["all_projects_closed"],
        },
    )


def owner_payments_panel_view(request):
    if not request.htmx:
        return redirect("owner")
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/payments.html",
        {
            "active_projects": context["active_projects"],
            "closed_projects": context["closed_projects"],
        },
    )


@require_POST
def owner_panel_mark_complete_view(request):
    job_id = request.POST.get("job_id")
    draw_number = request.POST.get("draw_number")
    panel = (request.POST.get("panel") or "payments").strip().lower()
    try:
        job_id = int(job_id)
        draw_number = int(draw_number)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid draw payload"}, status=400)

    try:
        _mark_draw_complete(job_id, draw_number)
    except JobDraw.DoesNotExist:
        return JsonResponse({"error": "Draw not found"}, status=404)

    if request.htmx:
        context = _build_owner_ui_context()
        template_map = {
            "dashboard": "owner/dashboard.html",
            "projects": "owner/all_projects.html",
            "payments": "owner/payments.html",
        }
        template_name = template_map.get(panel, "owner/payments.html")
        partial_context = {
            "owner/dashboard.html": {
                "notifications": context["notifications"],
                "notif_count": context["notif_count"],
                "dashboard_active_projects": context["dashboard_active_projects"],
                "dashboard_closed_projects": context["dashboard_closed_projects"],
                "dashboard_active_count": context["dashboard_active_count"],
            },
            "owner/all_projects.html": {
                "all_projects_active": context["all_projects_active"],
                "all_projects_closed": context["all_projects_closed"],
            },
            "owner/payments.html": {
                "active_projects": context["active_projects"],
                "closed_projects": context["closed_projects"],
            },
        }
        response = render(request, template_name, partial_context[template_name])
        response["HX-Trigger"] = "owner-refresh"
        return response
    return redirect("owner")


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
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/index.html",
        {
            "kpis": context["kpis"],
        },
    )


def manager_builds_panel_view(request):
    if not request.htmx:
        return redirect("manager")
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/my_builds.html",
        {
            "builds_active": context["builds_active"],
            "builds_closed": context["builds_closed"],
        },
    )


def manager_budgets_panel_view(request):
    if not request.htmx:
        return redirect("manager")
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/budgets.html",
        {
            "budgets_active": context["budgets_active"],
            "budgets_closed": context["budgets_closed"],
        },
    )


def manager_draws_panel_view(request):
    if not request.htmx:
        return redirect("manager")
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/draws.html",
        {
            "draws_active": context["draws_active"],
            "draws_closed": context["draws_closed"],
        },
    )


@require_POST
def manager_panel_mark_complete_view(request):
    job_id = request.POST.get("job_id")
    draw_number = request.POST.get("draw_number")
    panel = (request.POST.get("panel") or "draws").strip().lower()
    try:
        job_id = int(job_id)
        draw_number = int(draw_number)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid draw payload"}, status=400)

    try:
        _mark_draw_complete(job_id, draw_number)
    except JobDraw.DoesNotExist:
        return JsonResponse({"error": "Draw not found"}, status=404)

    if request.htmx:
        context = _build_manager_ui_context()
        template_map = {
            "builds": "manager/my_builds.html",
            "budgets": "manager/budgets.html",
            "draws": "manager/draws.html",
        }
        template_name = template_map.get(panel, "manager/draws.html")
        partial_context = {
            "manager/my_builds.html": {
                "builds_active": context["builds_active"],
                "builds_closed": context["builds_closed"],
            },
            "manager/budgets.html": {
                "budgets_active": context["budgets_active"],
                "budgets_closed": context["budgets_closed"],
            },
            "manager/draws.html": {
                "draws_active": context["draws_active"],
                "draws_closed": context["draws_closed"],
            },
        }
        response = render(request, template_name, partial_context[template_name])
        response["HX-Trigger"] = "manager-refresh"
        return response
    return redirect("manager")


def owner_view(request):
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/index.html",
        {
            "kpis": context["kpis"],
            "owner_total": context["owner_total"],
        },
    )


def sales_overview_view(request):
    context = _build_sales_ui_context()
    return render(
        request,
        "sales/overview/index.html",
        {
            "kpis": context["kpis"],
            "sales_total": context["sales_total"],
        },
    )


def sales_projects_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context()
    return render(
        request,
        "sales/overview/projects.html",
        {
            "projects_active": context["projects_active"],
            "projects_closed": context["projects_closed"],
        },
    )


def sales_models_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context()
    return render(
        request,
        "sales/overview/models.html",
        {
            "models": context["models"],
        },
    )


def sales_rates_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context()
    return render(
        request,
        "sales/overview/rates.html",
        {
            "exterior_rates": context["exterior_rates"],
            "interior_rates": context["interior_rates"],
        },
    )


@csrf_exempt
def save_contract_view(request):
    """
    POST — creates or updates a Job + JobDraw rows from wizard STATE.

    Expected JSON body:
    {
      "customer":  { "name", "addr", "rep", "order" },
      "model":     "CAJUN",
      "branch":    "summertown",
      "jobMode":   "shell" | "turnkey",
      "p10":       95000,
      "shellTotal": 142000,
      "turnkeyTotal": 195000,   // omit / 0 for shell
      "draws": [
        { "n": 0, "l": "Good Faith Deposit", "a": 2500 },
        { "n": 1, "l": "1st Home Draw (Loan Closing)", "a": 92500 },
        ...
      ]
    }

    Returns: { "ok": true, "job_id": <int> }
    """
    import json as _json

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = _json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # ── Basic fields ──
    customer = body.get("customer") or {}
    customer_name = (customer.get("name") or "").strip()
    customer_addr = (customer.get("addr") or "").strip()
    sales_rep     = (customer.get("rep")  or "").strip()
    order_number  = (customer.get("order") or "").strip()
    model_name    = (body.get("model") or "").strip()
    branch_key    = (body.get("branch") or "").strip()
    job_mode      = body.get("jobMode") or "shell"
    p10           = int(body.get("p10") or 0)
    shell_total   = int(body.get("shellTotal") or 0)
    turnkey_total = int(body.get("turnkeyTotal") or 0)
    draws_payload = body.get("draws") or []

    if not customer_name:
        return JsonResponse({"error": "customer.name is required"}, status=400)

    # ── Resolve FKs ──
    branch_obj = Branch.objects.filter(key=branch_key).first()
    plan_obj   = FloorPlanModel.objects.filter(name__iexact=model_name).first()

    contract_total = turnkey_total if job_mode == "turnkey" and turnkey_total else shell_total

    # ── Create or update Job (match on customer_name + order_number) ──
    lookup = {"customer_name": customer_name}
    if order_number:
        lookup["order_number"] = order_number

    job, created = Job.objects.update_or_create(
        **lookup,
        defaults={
            "customer_addr": customer_addr,
            "sales_rep":     sales_rep,
            "order_number":  order_number,
            "branch":        branch_obj,
            "floor_plan":    plan_obj,
            "job_mode":      job_mode if job_mode in ("shell", "turnkey") else "shell",
            "p10_material":  p10,
            "current_phase": "estimate",
        },
    )

    # ── Rebuild draw schedule ──
    if draws_payload:
        job.demo_draws.all().delete()
        for i, d in enumerate(draws_payload):
            amount = int(d.get("a") or 0)
            if amount <= 0:
                continue
            draw_num = int(d.get("n") or i)
            status = JobDraw.STATUS_CURRENT if draw_num == 1 else JobDraw.STATUS_PENDING
            JobDraw.objects.create(
                job=job,
                draw_number=draw_num,
                label=str(d.get("l") or f"Draw {draw_num}"),
                amount=amount,
                status=status,
            )

    return JsonResponse({"ok": True, "job_id": job.id, "created": created})