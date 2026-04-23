import re
import time
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

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


# ─────────────────────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────────────────────

ROLE_DASHBOARDS = {
    AppUser.ROLE_SALES: "sales_overview",
    AppUser.ROLE_PM: "manager",
    AppUser.ROLE_EXEC: "owner",
}


def _dashboard_for(user):
    return ROLE_DASHBOARDS.get(getattr(user, "role", None), "login")


def role_required(*allowed_roles):
    """Allow the listed roles. Execs always pass. Unauthenticated users go to login."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.htmx:
                    response = HttpResponse(status=401)
                    response["HX-Redirect"] = reverse("login")
                    return response
                return redirect("login")
            if request.user.role == AppUser.ROLE_EXEC or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            # Authenticated but wrong role — bounce to their own dashboard.
            return redirect(_dashboard_for(request.user))
        return _wrapped
    return decorator


def _throttle_key(request):
    # Bucket attempts by client IP so one attacker can't lock out a user from elsewhere.
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown"))
    return f"login_throttle::{ip}"


def _throttle_check(request):
    """Returns (locked, seconds_remaining). Tracks attempts in the session."""
    max_attempts = getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)
    lockout = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)
    key = _throttle_key(request)
    bucket = request.session.get(key) or {"count": 0, "until": 0}
    now = int(time.time())
    if bucket["until"] > now:
        return True, bucket["until"] - now
    if bucket["count"] >= max_attempts:
        bucket = {"count": 0, "until": 0}
        request.session[key] = bucket
    return False, 0


def _throttle_record_failure(request):
    max_attempts = getattr(settings, "LOGIN_MAX_ATTEMPTS", 5)
    lockout = getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)
    key = _throttle_key(request)
    bucket = request.session.get(key) or {"count": 0, "until": 0}
    bucket["count"] = int(bucket.get("count", 0)) + 1
    if bucket["count"] >= max_attempts:
        bucket["until"] = int(time.time()) + lockout
    request.session[key] = bucket
    request.session.modified = True


def _throttle_reset(request):
    key = _throttle_key(request)
    if key in request.session:
        del request.session[key]
        request.session.modified = True


@never_cache
def index(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_for(request.user))
    return redirect("login")


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_for(request.user))
    return render(request, "login/index.html", {})


def login_panel_view(request):
    if not request.htmx:
        return redirect("login")
    return render(request, "login/sign_in_panel.html", {})


@require_POST
@csrf_protect
@never_cache
def login_submit_view(request):
    locked, retry_in = _throttle_check(request)
    if locked:
        minutes = max(1, retry_in // 60)
        return render(
            request,
            "login/sign_in_panel.html",
            {"error": f"Too many attempts. Try again in {minutes} minute(s)."},
            status=429,
        )

    email = (request.POST.get("login") or "").strip().lower()
    password = request.POST.get("password") or ""

    user = None
    if email and password:
        user = authenticate(request, username=email, password=password)

    if user is None or not user.is_active:
        _throttle_record_failure(request)
        return render(
            request,
            "login/sign_in_panel.html",
            {
                "error": "Invalid email or password.",
                "login_value": email,
            },
            status=401,
        )

    _throttle_reset(request)
    auth_login(request, user)
    request.session.cycle_key()  # Prevent session fixation

    target = reverse(_dashboard_for(user))
    if request.htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = target
        return response
    return redirect(target)


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    if request.htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("login")
        return response
    return redirect("login")


@login_required
def sales_view(request):
    if request.user.role not in (AppUser.ROLE_SALES, AppUser.ROLE_EXEC):
        return redirect(_dashboard_for(request.user))
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
                "id": user.email,
                "name": user.name,
                "initials": user.initials,
                "role": user.role,
                "title": user.title,
            }
        )
    return users


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
        Job.objects.select_related("floor_plan", "branch")
        .prefetch_related("demo_trade_budgets", "demo_draws", "budget_lines__trade")
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

        # Fallback for contracts saved without demo trade rows:
        # use computed budget lines when present, then a single total budget row.
        if not bg:
            for line in job.budget_lines.all():
                trade_name = line.trade.name if line.trade else "Budget"
                bg[trade_name] = int(_to_number(line.total_budgeted))
                ac[trade_name] = 0

        if not bg:
            fallback_budget = int(_to_number(job.budget_total_amount))
            fallback_spent = int(_to_number(job.budget_spent_amount))
            if fallback_budget <= 0:
                fallback_budget = int(
                    sum(int(_to_number(draw.amount)) for draw in job.demo_draws.all())
                )
            if fallback_budget > 0 or fallback_spent > 0:
                bg["Total Budget"] = fallback_budget
                ac["Total Budget"] = fallback_spent

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
            "br": job.branch.label if job.branch else "Summertown",
            "ord": job.order_number or "",
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


def _branch_badge_class(branch_label):
    label = (branch_label or "").lower()
    if "morristown" in label:
        return "morristown"
    if "hopkinsville" in label:
        return "hopkinsville"
    if "hayden" in label:
        return "hayden"
    return "summertown"


def _bill_status_label(status):
    if status == "paid":
        return "Paid"
    if status == "review":
        return "Review"
    return "Pending"


def _build_project_ui_rows(projects):
    rows = []
    for project in projects:
        draws = project.get("dr", [])
        total = int(project.get("ct") or 0)
        paid = int(sum(d.get("a", 0) for d in draws if d.get("s") == JobDraw.STATUS_PAID))
        total_due = int(sum(d.get("a", 0) for d in draws))
        remaining = max(0, total - paid)
        pct = int(round((paid / total) * 100)) if total > 0 else 0
        current_draw = next((d for d in draws if d.get("s") == JobDraw.STATUS_CURRENT), None)
        branch_label = project.get("br") or "Summertown"
        raw_order_number = str(project.get("ord") or "").strip()
        if raw_order_number:
            order_number = raw_order_number
        else:
            order_number = str(project.get("id") or "")
        if order_number.isdigit():
            order_number_display = order_number.zfill(4)
        else:
            order_number_display = order_number

        draw_rows = []
        timeline_rows = []
        draw_segments = []
        for draw in draws:
            status = draw.get("s")
            amount = int(draw.get("a") or 0)
            paid_amount = amount if status == JobDraw.STATUS_PAID else 0
            date_text = draw.get("t") or ""
            status_demo = "paid" if status == JobDraw.STATUS_PAID else ("overdue" if status == JobDraw.STATUS_CURRENT else "pending")
            timeline_rows.append(_draw_timeline_row(draw))
            draw_rows.append(
                {
                    "draw_number": draw.get("n"),
                    "draw_number_display": "D" if draw.get("n") == 0 else draw.get("n"),
                    "label": draw.get("l", ""),
                    "date": date_text or "-",
                    "amount_display": _format_money(amount),
                    "due_display": _format_money(amount),
                    "paid_display": _format_money(paid_amount) if paid_amount else "-",
                    "method": "Wire" if paid_amount else "",
                    "source": f"{branch_label} draw account" if paid_amount else "",
                    "status_demo": status_demo,
                    "status_demo_label": "Paid" if status_demo == "paid" else ("Due" if status_demo == "overdue" else "Pending"),
                    "status": status,
                    "draw_num_class": _draw_num_class(status),
                    "pill_class": _draw_status_pill_class(status),
                    "status_label": _draw_status_label(status),
                    "is_placeholder_date": not bool(date_text),
                }
            )
            draw_segments.append(
                {
                    "width_pct": (amount / total_due) * 100 if total_due else 0,
                    "status_class": status_demo,
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
                    "cost_code": trade,
                    "budget_amount": budget,
                    "actual_amount": actual,
                    "remaining_amount": variance,
                    "budget_display": _format_money(budget),
                    "actual_display": _format_money(actual),
                    "variance_display": _format_money(variance),
                    "progress_pct": int(round((actual / budget) * 100)) if budget > 0 else 0,
                    "is_over": actual > budget,
                }
            )

        bills = []
        bill_seq = 1
        for trade in trade_rows:
            trade_name = trade["trade"]
            budget = trade["budget_amount"]
            actual = trade["actual_amount"]
            remaining_budget = max(0, budget - actual)
            invoice_id = f"INV-{timezone.now().year}-{project.get('id', 0):04d}-{bill_seq:03d}"

            if actual > 0:
                actual_status = "review" if actual > budget else "paid"
                bills.append(
                    {
                        "invoice_id": invoice_id,
                        "vendor": f"{trade_name} Vendor",
                        "description": f"{trade_name} actual cost entry",
                        "cost_code": trade["cost_code"],
                        "qb_account": trade_name,
                        "amount": actual,
                        "amount_display": _format_money(actual),
                        "date": current_draw.get("t") if current_draw and current_draw.get("t") else "",
                        "branch": branch_label,
                        "branch_class": _branch_badge_class(branch_label),
                        "status": actual_status,
                        "status_label": _bill_status_label(actual_status),
                    }
                )
                bill_seq += 1

            if remaining_budget > 0:
                bills.append(
                    {
                        "invoice_id": f"INV-{timezone.now().year}-{project.get('id', 0):04d}-{bill_seq:03d}",
                        "vendor": f"{trade_name} Vendor",
                        "description": f"{trade_name} budgeted remaining",
                        "cost_code": trade["cost_code"],
                        "qb_account": trade_name,
                        "amount": remaining_budget,
                        "amount_display": _format_money(remaining_budget),
                        "date": "",
                        "branch": branch_label,
                        "branch_class": _branch_badge_class(branch_label),
                        "status": "pending",
                        "status_label": _bill_status_label("pending"),
                    }
                )
                bill_seq += 1

        bills_total = sum(row["amount"] for row in bills)
        bills_paid = sum(row["amount"] for row in bills if row["status"] == "paid")
        bills_pending = sum(row["amount"] for row in bills if row["status"] != "paid")

        margin_pct = int(round(((total - total_bg) / total) * 100, 0)) if total > 0 and total_bg > 0 else 0
        margin_color = "var(--green)" if margin_pct >= 30 else ("var(--amber)" if margin_pct >= 15 else "#DC2626")
        live_margin_pct = round(((total - total_ac) / total) * 100, 1) if total > 0 else 0

        current_draw_label = ""
        if current_draw and current_draw.get("l"):
            current_draw_label = re.sub(r"^\d+\w*\s*[\u2014\-]\s*", "", current_draw.get("l") or "")

        subtitle = f"{project.get('md', '')} · {project.get('cu', '')} · PM: {project.get('pm', '')}"
        overdue_draw = any(draw.get("s") == JobDraw.STATUS_CURRENT for draw in draws)

        rows.append(
            {
                "id": project.get("id"),
                "name": project.get("nm", ""),
                "model_name": project.get("md", ""),
                "branch_label": branch_label,
                "order_number": order_number_display,
                "phase": project.get("ph", "estimate"),
                "phase_label": _phase_label(project.get("ph", "estimate")),
                "phase_pill_class": _phase_pill_class(project.get("ph", "estimate")),
                "subtitle": subtitle,
                "total_amount": total,
                "paid_amount": paid,
                "total_display": _format_money(total),
                "paid_display": _format_money(paid),
                "remaining_display": _format_money(remaining),
                "pct": max(0, min(100, pct)),
                "draws": draw_rows,
                "draw_segments": draw_segments,
                "timeline_draws": timeline_rows,
                "trades": trade_rows,
                "bills": bills,
                "bills_count": len(bills),
                "bills_total_display": _format_money(bills_total),
                "bills_paid_display": _format_money(bills_paid),
                "bills_pending_display": _format_money(bills_pending),
                "total_bg": total_bg,
                "total_ac": total_ac,
                "total_bg_display": _format_money(total_bg),
                "total_ac_display": _format_money(total_ac),
                "total_rem_display": _format_money(total_bg - total_ac),
                "total_rem_negative": (total_bg - total_ac) < 0,
                "margin_pct": margin_pct,
                "margin_color": margin_color,
                "live_margin_pct": live_margin_pct,
                "is_overdue": overdue_draw,
                "status_chip_class": "od" if overdue_draw else "act",
                "status_chip_label": "Payment Due" if overdue_draw else "Active",
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

    dashboard_jobs = active_projects
    contract_total = sum(job.get("total_amount", 0) for job in dashboard_jobs)
    collected_total = sum(job.get("paid_amount", 0) for job in dashboard_jobs)
    outstanding_total = max(0, contract_total - collected_total)
    actual_total = sum(job.get("total_ac", 0) for job in dashboard_jobs)
    budget_total = sum(job.get("total_bg", 0) for job in dashboard_jobs)
    live_margin_pct = round(((contract_total - actual_total) / contract_total) * 100, 1) if contract_total > 0 else 0

    bill_rows = [bill for job in dashboard_jobs for bill in job.get("bills", [])]
    matched_count = sum(1 for bill in bill_rows if bill.get("status") in {"paid", "review"})
    unmatched_count = sum(1 for bill in bill_rows if bill.get("status") == "review")

    dashboard_metrics = {
        "active_jobs": len(dashboard_jobs),
        "under_contract": _format_money(contract_total),
        "collected": _format_money(collected_total),
        "outstanding": _format_money(outstanding_total),
        "qb_payments": _format_money(collected_total),
        "qb_matched": f"{matched_count} / {len(bill_rows)}" if bill_rows else "0 / 0",
        "qb_unmatched": unmatched_count,
        "contract_revenue": _format_money(contract_total),
        "actual_cost": _format_money(actual_total),
        "live_margin_pct": f"{live_margin_pct:.1f}%",
        "last_pull": timezone.localtime().strftime("%b %d, %Y %I:%M %p").replace(" 0", " "),
        "is_connected": bool(dashboard_jobs),
        "budget_total": _format_money(budget_total),
    }

    return {
        "kpis": kpis,
        "owner_total": owner_total,
        "dashboard_metrics": dashboard_metrics,
        "dashboard_jobs": dashboard_jobs,
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


def _job_deposit_paid(job):
    """Deposit = JobDraw with draw_number=0 in paid status."""
    for draw in job.demo_draws.all():
        if draw.draw_number == 0:
            return draw.status == JobDraw.STATUS_PAID
    return False


def _job_loan_closed(job):
    """Loan closing = JobDraw with draw_number=1 in paid status."""
    for draw in job.demo_draws.all():
        if draw.draw_number == 1:
            return draw.status == JobDraw.STATUS_PAID
    return False


# Sales commission rate applied to P10 material. Kept as a module-level
# constant for the demo; in prod this would live on the rep's profile or
# a per-branch config row.
SALES_COMMISSION_RATE = 0.03  # 3 % of P10 material


def _contract_total_for_job(job):
    """Best-effort contract total (customer price) for a Job.

    Priority:
      1. wizard_state.turnkeyTotal (if job_mode==turnkey and value > 0)
      2. wizard_state.shellTotal   (if value > 0)
      3. job.budget_total_amount   (fallback; set on save_contract)
    """
    state = job.wizard_state or {}
    if isinstance(state, dict):
        if job.job_mode == "turnkey":
            turnkey = int(state.get("turnkeyTotal") or 0)
            if turnkey > 0:
                return turnkey
        shell = int(state.get("shellTotal") or 0)
        if shell > 0:
            return shell
    return int(_to_number(job.budget_total_amount))


def _build_sales_value_breakdown(job, p10_amount):
    """Shared contract-value block used on both In Progress and Closed rows."""
    contract_total = _contract_total_for_job(job)
    commission_amount = int(round(p10_amount * SALES_COMMISSION_RATE))
    p10_pct = round((p10_amount / contract_total) * 100, 1) if contract_total > 0 else 0.0
    return {
        "contract_total_amount": contract_total,
        "contract_total_display": _format_money(contract_total) if contract_total else "--",
        "p10_pct_display": f"{p10_pct:.1f}%" if contract_total > 0 else "--",
        "commission_amount": commission_amount,
        "commission_display": _format_money(commission_amount),
        "commission_rate_display": f"{int(SALES_COMMISSION_RATE * 100)}% of P10",
    }


def _build_sales_in_progress_row(job):
    plan_name = job.floor_plan.name if job.floor_plan else "Custom"
    p10_amount = int(_to_number(job.p10_material))
    edit_url_name = "sales_turnkey_edit" if job.job_mode == "turnkey" else "sales_shell_edit"
    row = {
        "id": job.id,
        "name": job.customer_name or f"Build #{job.id}",
        "model_name": plan_name,
        "address": job.customer_addr or "",
        "order_number": job.order_number or "",
        "p10_amount": p10_amount,
        "p10_display": _format_money(p10_amount),
        "deposit_paid": _job_deposit_paid(job),
        "loan_closed": _job_loan_closed(job),
        "edit_url": reverse(edit_url_name, args=[job.id]),
        "finalize_url": reverse("sales_finalize_contract", args=[job.id]),
        "job_mode": job.job_mode,
    }
    row.update(_build_sales_value_breakdown(job, p10_amount))
    return row


def _build_sales_lead_row(job):
    """Compact row for the Leads tab. Leads don't have wizard data yet,
    so we skip the contract/commission breakdown."""
    source_display = dict(Job.LEAD_SOURCE_CHOICES).get(job.lead_source, "")
    created_local = timezone.localtime(job.created_at) if timezone.is_aware(job.created_at) else job.created_at
    created_display = created_local.strftime("%b %d, %Y") if created_local else ""
    followup_display = job.lead_next_followup.strftime("%b %d, %Y") if job.lead_next_followup else ""
    stale = False
    if created_local:
        age_days = (timezone.now() - job.created_at).days
        stale = age_days >= 21
    return {
        "id": job.id,
        "name": job.customer_name or f"Lead #{job.id}",
        "phone": job.customer_phone or "",
        "email": job.customer_email or "",
        "address": job.customer_addr or "",
        "source_display": source_display,
        "source_key": job.lead_source or "",
        "notes": job.lead_notes or "",
        "followup_display": followup_display,
        "created_display": created_display,
        "stale": stale,
        "edit_url": reverse("sales_edit_lead", args=[job.id]),
        "convert_url": reverse("sales_convert_lead", args=[job.id]),
        "delete_url": reverse("sales_delete_lead", args=[job.id]),
    }


def _build_sales_closed_row(job):
    plan_name = job.floor_plan.name if job.floor_plan else "Custom"
    p10_amount = int(_to_number(job.p10_material))
    closed_at = job.sales_closed_at
    closed_display = ""
    if closed_at:
        local_closed = timezone.localtime(closed_at) if timezone.is_aware(closed_at) else closed_at
        closed_display = local_closed.strftime("%b %d, %Y")
    row = {
        "id": job.id,
        "name": job.customer_name or f"Build #{job.id}",
        "model_name": plan_name,
        "order_number": job.order_number or "",
        "p10_amount": p10_amount,
        "p10_display": _format_money(p10_amount),
        "closed_display": closed_display,
    }
    row.update(_build_sales_value_breakdown(job, p10_amount))
    return row


def _sales_jobs_queryset(request):
    """Jobs visible on the sales dashboard.

    Per the current demo scope, any sales user can see every job — production
    scoping (sales_rep == request.user.name) is flagged out-of-scope.
    """
    return (
        Job.objects.select_related("floor_plan", "branch")
        .prefetch_related("demo_draws")
        .order_by("-created_at")
    )


def _build_sales_ui_context(request=None):
    # Scope jobs to the current user when available; fall back to all jobs otherwise.
    if request is not None:
        base_qs = _sales_jobs_queryset(request)
    else:
        base_qs = Job.objects.select_related("floor_plan", "branch").prefetch_related("demo_draws").order_by("-created_at")

    now = timezone.now()
    # Leads: is_lead=True, not yet closed
    lead_jobs = base_qs.filter(is_lead=True, sales_closed_at__isnull=True)
    # In Progress: is_lead=False, not yet closed
    in_progress_jobs = base_qs.filter(is_lead=False, sales_closed_at__isnull=True)
    closed_this_month_jobs = base_qs.filter(
        sales_closed_at__isnull=False,
        sales_closed_at__year=now.year,
        sales_closed_at__month=now.month,
    )

    lead_rows = [_build_sales_lead_row(job) for job in lead_jobs]
    in_progress_rows = [_build_sales_in_progress_row(job) for job in in_progress_jobs]
    closed_rows = [_build_sales_closed_row(job) for job in closed_this_month_jobs]

    p10_total_amount = sum(row["p10_amount"] for row in in_progress_rows) + sum(
        row["p10_amount"] for row in closed_rows
    )

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

    month_label = now.strftime("%B %Y")

    return {
        "p10_total_display": _format_money(p10_total_amount),
        "p10_month_label": month_label,
        "kpis": [
            {
                "label": f"P10 Material — {month_label}",
                "value": _format_money(p10_total_amount),
                "value_class": "kpi-val",
            }
        ],
        "projects_in_progress": in_progress_rows,
        "projects_closed": closed_rows,
        "leads": lead_rows,
        "in_progress_count": len(in_progress_rows),
        "closed_count": len(closed_rows),
        "leads_count": len(lead_rows),
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


@login_required
@require_POST
@csrf_protect
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


@role_required(AppUser.ROLE_EXEC)
def owner_dashboard_panel_view(request):
    if not request.htmx:
        return redirect("owner")
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/dashboard.html",
        {
            "dashboard_metrics": context["dashboard_metrics"],
            "dashboard_jobs": context["dashboard_jobs"],
            "dashboard_active_count": context["dashboard_active_count"],
        },
    )


@role_required(AppUser.ROLE_EXEC)
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


@role_required(AppUser.ROLE_EXEC)
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


@role_required(AppUser.ROLE_EXEC)
@require_POST
@csrf_protect
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
                "dashboard_metrics": context["dashboard_metrics"],
                "dashboard_jobs": context["dashboard_jobs"],
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


def _load_editable_job(request, job_id):
    """Return the Job for the given id (demo scope: any sales/exec user may edit)."""
    if not job_id:
        return None
    user = request.user
    if user.role not in (AppUser.ROLE_SALES, AppUser.ROLE_EXEC):
        return None
    try:
        return Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return None


def _wizard_state_for_job(job):
    """Return a wizard-ready STATE dict for rehydrating the BuildWizard.

    For committed contracts we use the saved ``wizard_state`` verbatim.
    For leads (which never ran the wizard) we synthesize a minimal state
    pre-filling the Step-1 customer fields.
    """
    state = job.wizard_state or {}
    if job.is_lead and not state:
        return {
            "customer": {
                "name": job.customer_name or "",
                "addr": job.customer_addr or "",
                "order": job.order_number or "",
                "rep":   job.sales_rep or "",
                "p10":   0,
            },
        }
    return state


@role_required(AppUser.ROLE_SALES)
def sales_shell_view(request, job_id=None):
    existing_state = None
    existing_job_id = None
    if job_id:
        job = _load_editable_job(request, job_id)
        if job is None:
            return redirect("sales_overview")
        existing_state = _wizard_state_for_job(job)
        existing_job_id = job.id
    return render(
        request,
        "sales/shell/index.html",
        {
            "wizard_mode": "shell",
            "wizard_seed_data": _build_contract_seed_data(),
            "existing_state": existing_state,
            "existing_job_id": existing_job_id,
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_turnkey_view(request, job_id=None):
    existing_state = None
    existing_job_id = None
    if job_id:
        job = _load_editable_job(request, job_id)
        if job is None:
            return redirect("sales_overview")
        existing_state = _wizard_state_for_job(job)
        existing_job_id = job.id
    return render(
        request,
        "sales/turnkey/index.html",
        {
            "wizard_mode": "turnkey",
            "wizard_seed_data": _build_contract_seed_data(),
            "existing_state": existing_state,
            "existing_job_id": existing_job_id,
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_contract_seed_data_view(request):
    return JsonResponse(_build_contract_seed_data())


@login_required
def app_seed_data_view(request):
    return JsonResponse(_build_app_seed_data())


@role_required(AppUser.ROLE_PM)
def manager_view(request):
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/index.html",
        {
            "kpis": context["kpis"],
        },
    )


@role_required(AppUser.ROLE_PM)
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


@role_required(AppUser.ROLE_PM)
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


@role_required(AppUser.ROLE_PM)
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


@role_required(AppUser.ROLE_PM)
@require_POST
@csrf_protect
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


@role_required(AppUser.ROLE_EXEC)
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


@role_required(AppUser.ROLE_SALES)
def sales_overview_view(request):
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/index.html",
        {
            "kpis": context["kpis"],
            "p10_total_display": context["p10_total_display"],
            "p10_month_label": context["p10_month_label"],
            "leads_count": context["leads_count"],
            "in_progress_count": context["in_progress_count"],
            "closed_count": context["closed_count"],
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_in_progress_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/in_progress.html",
        {
            "projects_in_progress": context["projects_in_progress"],
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_closed_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/closed.html",
        {
            "projects_closed": context["projects_closed"],
            "p10_month_label": context["p10_month_label"],
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_header_panel_view(request):
    """HTMX partial: re-renders the header + KPI tiles (P10 total, counts)."""
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/_header.html",
        {
            "p10_total_display": context["p10_total_display"],
            "p10_month_label": context["p10_month_label"],
            "leads_count": context["leads_count"],
            "in_progress_count": context["in_progress_count"],
            "closed_count": context["closed_count"],
        },
    )


@role_required(AppUser.ROLE_SALES)
def sales_rates_panel_view(request):
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/rates.html",
        {
            "exterior_rates": context["exterior_rates"],
            "interior_rates": context["interior_rates"],
        },
    )


@role_required(AppUser.ROLE_SALES)
@require_POST
@csrf_protect
def sales_finalize_contract_view(request, job_id):
    """
    Demo handoff shortcut: marks deposit (draw 0) + loan close (draw 1) as paid,
    sets sales_closed_at=now(), then re-renders the In Progress panel so the card
    disappears from the list.
    """
    from django.db import transaction

    job = _load_editable_job(request, job_id)
    if job is None:
        return JsonResponse({"error": "Job not found or not editable"}, status=404)

    with transaction.atomic():
        job.sales_closed_at = timezone.now()
        job.save(update_fields=["sales_closed_at"])
        JobDraw.objects.filter(job=job, draw_number__in=[0, 1]).update(
            status=JobDraw.STATUS_PAID,
            paid_date=timezone.now().strftime("%b ") + str(timezone.now().day),
        )

    if request.htmx:
        context = _build_sales_ui_context(request)
        response = render(
            request,
            "sales/overview/in_progress.html",
            {"projects_in_progress": context["projects_in_progress"]},
        )
        response["HX-Trigger"] = "sales-refresh"
        return response
    return redirect("sales_overview")


# ═══════════════════════════════════════════════════════════════
# LEADS — early-stage customer contacts before a full contract
# ═══════════════════════════════════════════════════════════════


def _load_editable_lead(request, job_id):
    """Like _load_editable_job but enforces is_lead=True (prevents accidental
    contract edits through the lead routes)."""
    job = _load_editable_job(request, job_id)
    if job is None or not job.is_lead:
        return None
    return job


def _parse_lead_followup(value):
    value = (value or "").strip()
    if not value:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _render_leads_panel(request):
    """Shared helper that renders the Leads tab HTMX fragment."""
    context = _build_sales_ui_context(request)
    response = render(request, "sales/overview/leads.html", {"leads": context["leads"]})
    response["HX-Trigger"] = "sales-refresh"
    return response


@role_required(AppUser.ROLE_SALES)
def sales_leads_panel_view(request):
    """HTMX partial: the Leads tab list."""
    if not request.htmx:
        return redirect("sales_overview")
    context = _build_sales_ui_context(request)
    return render(
        request,
        "sales/overview/leads.html",
        {"leads": context["leads"]},
    )


@role_required(AppUser.ROLE_SALES)
@csrf_protect
def sales_new_lead_view(request):
    """GET renders an empty lead form; POST creates the lead."""
    if request.method == "POST":
        customer_name = (request.POST.get("customer_name") or "").strip()
        if not customer_name:
            return render(
                request,
                "sales/overview/lead_form.html",
                {
                    "mode": "new",
                    "form_action": reverse("sales_new_lead"),
                    "lead": {
                        "customer_name": customer_name,
                        "customer_phone": request.POST.get("customer_phone", ""),
                        "customer_email": request.POST.get("customer_email", ""),
                        "customer_addr": request.POST.get("customer_addr", ""),
                        "lead_source": request.POST.get("lead_source", ""),
                        "lead_notes": request.POST.get("lead_notes", ""),
                        "lead_next_followup": request.POST.get("lead_next_followup", ""),
                    },
                    "lead_source_choices": Job.LEAD_SOURCE_CHOICES,
                    "error": "Customer name is required.",
                },
            )
        Job.objects.create(
            customer_name=customer_name,
            customer_phone=(request.POST.get("customer_phone") or "").strip(),
            customer_email=(request.POST.get("customer_email") or "").strip(),
            customer_addr=(request.POST.get("customer_addr") or "").strip(),
            lead_source=(request.POST.get("lead_source") or "").strip(),
            lead_notes=(request.POST.get("lead_notes") or "").strip(),
            lead_next_followup=_parse_lead_followup(request.POST.get("lead_next_followup")),
            sales_rep=getattr(request.user, "name", "") or "",
            is_lead=True,
            current_phase="estimate",
        )
        return redirect(reverse("sales_overview") + "?tab=leads")
    # GET
    return render(
        request,
        "sales/overview/lead_form.html",
        {
            "mode": "new",
            "form_action": reverse("sales_new_lead"),
            "lead": {},
            "lead_source_choices": Job.LEAD_SOURCE_CHOICES,
        },
    )


@role_required(AppUser.ROLE_SALES)
@csrf_protect
def sales_edit_lead_view(request, job_id):
    """GET renders the lead form pre-filled; POST updates."""
    lead = _load_editable_lead(request, job_id)
    if lead is None:
        return redirect(reverse("sales_overview") + "?tab=leads")

    if request.method == "POST":
        customer_name = (request.POST.get("customer_name") or "").strip()
        if not customer_name:
            return render(
                request,
                "sales/overview/lead_form.html",
                {
                    "mode": "edit",
                    "form_action": reverse("sales_edit_lead", args=[lead.id]),
                    "lead": lead,
                    "lead_source_choices": Job.LEAD_SOURCE_CHOICES,
                    "error": "Customer name is required.",
                },
            )
        lead.customer_name = customer_name
        lead.customer_phone = (request.POST.get("customer_phone") or "").strip()
        lead.customer_email = (request.POST.get("customer_email") or "").strip()
        lead.customer_addr = (request.POST.get("customer_addr") or "").strip()
        lead.lead_source = (request.POST.get("lead_source") or "").strip()
        lead.lead_notes = (request.POST.get("lead_notes") or "").strip()
        lead.lead_next_followup = _parse_lead_followup(request.POST.get("lead_next_followup"))
        lead.save(update_fields=[
            "customer_name", "customer_phone", "customer_email", "customer_addr",
            "lead_source", "lead_notes", "lead_next_followup", "updated_at",
        ])
        return redirect(reverse("sales_overview") + "?tab=leads")

    return render(
        request,
        "sales/overview/lead_form.html",
        {
            "mode": "edit",
            "form_action": reverse("sales_edit_lead", args=[lead.id]),
            "lead": lead,
            "lead_source_choices": Job.LEAD_SOURCE_CHOICES,
        },
    )


@role_required(AppUser.ROLE_SALES)
@require_POST
@csrf_protect
def sales_delete_lead_view(request, job_id):
    """Archive (delete) a lead that didn't pan out. Only works on rows still
    flagged is_lead=True — we don't allow this route to nuke committed contracts."""
    lead = _load_editable_lead(request, job_id)
    if lead is None:
        if request.htmx:
            return _render_leads_panel(request)
        return redirect(reverse("sales_overview") + "?tab=leads")
    lead.delete()
    if request.htmx:
        return _render_leads_panel(request)
    return redirect(reverse("sales_overview") + "?tab=leads")


@role_required(AppUser.ROLE_SALES)
def sales_convert_lead_view(request, job_id):
    """Convert a lead → full contract by opening the BuildWizard with the
    lead's customer info pre-filled. Saving the wizard flips is_lead=False
    and the row moves to In Progress.

    Same job_id flows through both routes (shell + turnkey); the rep can
    change jobMode inside the wizard if needed.
    """
    lead = _load_editable_lead(request, job_id)
    if lead is None:
        return redirect(reverse("sales_overview") + "?tab=leads")
    # Route to shell by default; the wizard's own mode toggle lets the rep switch.
    return redirect("sales_shell_edit", job_id=lead.id)


@role_required(AppUser.ROLE_SALES)
@require_POST
@csrf_protect
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
    trade_budgets_payload = body.get("tradeBudgets") or []
    budget_total_payload = int(body.get("budgetTotal") or 0)

    if not customer_name:
        return JsonResponse({"error": "customer.name is required"}, status=400)

    # ── Resolve FKs ──
    branch_obj = Branch.objects.filter(key=branch_key).first()
    plan_obj   = FloorPlanModel.objects.filter(name__iexact=model_name).first()

    contract_total = turnkey_total if job_mode == "turnkey" and turnkey_total else shell_total
    budget_total = budget_total_payload
    if budget_total <= 0 and trade_budgets_payload:
        budget_total = int(
            sum(int(row.get("budgeted") or 0) for row in trade_budgets_payload)
        )
    if budget_total <= 0:
        budget_total = int(contract_total or 0)

    # ── Create or update Job ──
    # Preferred: an explicit leadId/jobId in the payload (from lead conversion
    # or wizard Edit flow). Falls back to matching on (customer_name, order_number)
    # for brand-new contracts, keeping the existing idempotent save semantics.
    explicit_job_id = body.get("leadId") or body.get("jobId")
    job_defaults = {
        "customer_addr": customer_addr,
        "sales_rep":     sales_rep,
        "order_number":  order_number,
        "branch":        branch_obj,
        "floor_plan":    plan_obj,
        "job_mode":      job_mode if job_mode in ("shell", "turnkey") else "shell",
        "p10_material":  p10,
        "budget_total_amount": budget_total,
        "budget_spent_amount": 0,
        "current_phase": "estimate",
        # A saved wizard is never a lead — this flips the row to In Progress.
        "is_lead":       False,
    }

    if explicit_job_id:
        try:
            job = Job.objects.get(pk=int(explicit_job_id))
            for field, value in job_defaults.items():
                setattr(job, field, value)
            # customer_name is part of the lookup fields when not using explicit id,
            # so set it here too.
            job.customer_name = customer_name
            job.save()
            created = False
        except (Job.DoesNotExist, ValueError, TypeError):
            explicit_job_id = None  # fall through to update_or_create below

    if not explicit_job_id:
        lookup = {"customer_name": customer_name}
        if order_number:
            lookup["order_number"] = order_number
        job, created = Job.objects.update_or_create(
            **lookup,
            defaults=job_defaults,
        )

    # Persist the full raw wizard STATE payload for later rehydration on Edit.
    # shellTotal / turnkeyTotal are computed in saveContract() (not on STATE),
    # so we merge them into the stored snapshot here. _contract_total_for_job
    # reads these keys to show the Total Contracted Amount on sales cards.
    raw_state = body.get("rawState")
    if isinstance(raw_state, dict):
        raw_state = dict(raw_state)  # shallow copy so we don't mutate request body
        if shell_total:
            raw_state["shellTotal"] = shell_total
        if turnkey_total:
            raw_state["turnkeyTotal"] = turnkey_total
        job.wizard_state = raw_state
        job.save(update_fields=["wizard_state"])

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

    # Keep owner/manager budget tabs populated for contracts saved from the wizard.
    if trade_budgets_payload:
        job.demo_trade_budgets.all().delete()
        for idx, row in enumerate(trade_budgets_payload):
            trade_name = str(row.get("trade") or "").strip()
            if not trade_name:
                continue
            budgeted = int(row.get("budgeted") or 0)
            actual = int(row.get("actual") or 0)
            if budgeted <= 0 and actual <= 0:
                continue
            JobTradeBudget.objects.create(
                job=job,
                trade_name=trade_name,
                budgeted=budgeted,
                actual=actual,
                sort_order=idx,
            )

    return JsonResponse({"ok": True, "job_id": job.id, "created": created})