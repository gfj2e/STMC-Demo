import re
import time
from decimal import Decimal
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    AppUser,
    Branch,
    FloorPlanModel,
    InteriorRateCard,
    Job,
    JobChangeOrder,
    JobDraw,
    JobTradeBudget,
)


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
    return redirect("sales_turnkey")


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
        int_part = _to_number(job.adjusted_int_contract)
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
        .prefetch_related(
            "demo_trade_budgets", "demo_draws", "budget_lines__trade", "change_orders",
        )
        .order_by("-created_at")[:80]
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

        # Trade budgets from DB. `lk` (locked) tracks rows where a paid Bill
        # has been pulled from QB -- the manager template renders these as
        # "Paid" pills instead of the dim "$0 / $budgeted" pair.
        bg = {}
        ac = {}
        lk = {}
        for tb in job.demo_trade_budgets.all():
            bg[tb.trade_name] = int(tb.budgeted)
            ac[tb.trade_name] = int(tb.actual)
            lk[tb.trade_name] = bool(tb.is_complete)

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

        # Per-job signed contract change orders. Surfaced on the PM's My
        # Builds card; PM-created via the change-order modal.
        co = []
        for co_row in job.change_orders.all():
            co.append({
                "id": co_row.id,
                "n": co_row.number,
                "desc": co_row.description,
                "amt": int(_to_number(co_row.price_change)),
                "new_total": int(_to_number(co_row.new_contract_total)),
                "timing": co_row.get_payment_timing_display(),
                "created": timezone.localtime(co_row.created_at).strftime("%b %d, %Y"),
            })

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
            "lk": lk,
            "dr": dr,
            "co": co,
            "closed_at": job.sales_closed_at,
            # Loan-closing draw (#1) paid? Gates PM change-order creation —
            # change orders can only be authored once the sales rep has closed
            # the loan, since the contract isn't legally finalized until then.
            "loan_closed": _job_loan_closed(job),
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
    """Interior-only rate card for the Sales rate card tab."""
    interior = []
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

    int_rate_map = {r.key: r for r in InteriorRateCard.objects.filter(
        key__in=[k[0] for k in int_keys]
    )}

    for key, label, group, _ in int_keys:
        rc = int_rate_map.get(key)
        interior.append({
            "l": label,
            "g": group,
            "r": _to_number(rc.rate) if rc else 0,
            "u": rc.unit if rc else "/SF",
        })

    return {"exterior": [], "interior": interior}


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
    # INVOICED = PM marked complete, QB Invoice DueDate=today, awaiting bank
    # Payment. Amber ("warning") signals "action expected from another party".
    if status_code == JobDraw.STATUS_INVOICED:
        return "pill-warning"
    if status_code == JobDraw.STATUS_CURRENT:
        return "pill-brand"
    return "pill-muted"


def _draw_status_label(status_code):
    if status_code == JobDraw.STATUS_PAID:
        return "Paid"
    if status_code == JobDraw.STATUS_INVOICED:
        return "Due"
    if status_code == JobDraw.STATUS_CURRENT:
        return "Current"
    return "Pending"


def _draw_num_class(status_code):
    if status_code == JobDraw.STATUS_PAID:
        return "paid"
    if status_code == JobDraw.STATUS_INVOICED:
        return "invoiced"
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
    if status == JobDraw.STATUS_PAID:
        icon, dot_class, status_color = "✓", "pdg", "var(--green)"
        status_label = "Paid" + (f" {draw.get('t')}" if draw.get("t") else "")
    elif status == JobDraw.STATUS_INVOICED:
        icon, dot_class, status_color = "$", "pdy", "var(--amber-dark)"
        status_label = "Due"
    elif status == JobDraw.STATUS_CURRENT:
        icon, dot_class, status_color = "►", "pdb", "#1D4ED8"
        status_label = "Current"
    else:
        icon = "D" if draw.get("n") == 0 else str(draw.get("n") or "")
        dot_class, status_color, status_label = "pdx", "var(--g400)", "Pending"
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
        locked_map = project.get("lk") or {}
        for trade in trades:
            budget = int((project.get("bg") or {}).get(trade, 0) or 0)
            actual = int((project.get("ac") or {}).get(trade, 0) or 0)
            variance = budget - actual
            total_bg += budget
            total_ac += actual
            is_paid = bool(locked_map.get(trade))
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
                    # Phase 2: True once a paid Bill in QB has stamped this row.
                    # Template renders a "Paid" pill instead of the dim
                    # "$0 / $budgeted" pair when set.
                    "is_paid": is_paid,
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

        change_order_rows = []
        for co_row in project.get("co", []) or []:
            amt = int(co_row.get("amt") or 0)
            is_credit = amt < 0
            display_amt = _format_money(abs(amt))
            change_order_rows.append({
                "id": co_row.get("id"),
                "number": co_row.get("n"),
                "description": co_row.get("desc", ""),
                "amount_raw": amt,
                # Show credits as "-$4,145" with a minus sign; charges as "+$2,000".
                "amount_display": ("-" if is_credit else "+") + display_amt,
                "is_credit": is_credit,
                "new_total_display": _format_money(co_row.get("new_total") or 0)
                    if (co_row.get("new_total") or 0) > 0 else "",
                "timing": co_row.get("timing", ""),
                "created": co_row.get("created", ""),
            })

        rows.append(
            {
                "id": project.get("id"),
                "name": project.get("nm", ""),
                "model_name": project.get("md", ""),
                "customer_display": project.get("cu", ""),
                "pm_name": project.get("pm", ""),
                "branch_label": branch_label,
                "order_number": order_number_display,
                "phase": project.get("ph", "estimate"),
                "phase_label": _phase_label(project.get("ph", "estimate")),
                "phase_pill_class": _phase_pill_class(project.get("ph", "estimate")),
                "closed_at": project.get("closed_at"),
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
                "change_orders": change_order_rows,
                "change_order_count": len(change_order_rows),
                "loan_closed": bool(project.get("loan_closed")),
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


def _group_projects_by_branch(projects):
    grouped = {}
    for project in projects:
        branch = (project.get("branch_label") or "Unassigned").strip() or "Unassigned"
        grouped.setdefault(branch, []).append(project)
    return [
        {
            "label": branch,
            "projects": grouped[branch],
            "count": len(grouped[branch]),
        }
        for branch in sorted(grouped.keys())
    ]


def _group_projects_by_closed_month(projects):
    grouped = {}
    for project in projects:
        closed_at = project.get("closed_at")
        if closed_at:
            local_closed = timezone.localtime(closed_at) if timezone.is_aware(closed_at) else closed_at
            label = local_closed.strftime("%B %Y")
            sort_key = (local_closed.year, local_closed.month)
        else:
            label = "Unknown Close Month"
            sort_key = (0, 0)

        if label not in grouped:
            grouped[label] = {"label": label, "sort_key": sort_key, "projects": []}
        grouped[label]["projects"].append(project)

    buckets = sorted(grouped.values(), key=lambda b: b["sort_key"], reverse=True)
    for bucket in buckets:
        bucket["count"] = len(bucket["projects"])
    return buckets


def _build_owner_ui_context():
    _, owner = _build_manager_owner_data()
    projects = owner.get("projects", [])
    rows = _build_project_ui_rows(projects)

    active_projects = [p for p in rows if p["phase"] != "closed"]
    closed_projects = [p for p in rows if p["phase"] == "closed"]
    active_projects_by_branch = _group_projects_by_branch(active_projects)
    closed_projects_by_month = _group_projects_by_closed_month(closed_projects)

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

    # ── QuickBooks Sync tile ─────────────────────────────────────
    # `qb_payments` and `last_pull` are now driven by the real QbSyncSnapshot
    # (populated via the "Refresh from QuickBooks" button on the dashboard,
    # which calls qb_pull.refresh_snapshot). The other qb_* fields remain
    # mocked for now — those pull paths (Bills/matching) aren't implemented.
    # `is_connected` reflects the real OAuth connection, not "do we have jobs."
    from . import qb_client as _qb_client
    from . import qb_pull as _qb_pull
    qb_conn = _qb_client.get_connection()
    qb_snapshot = _qb_pull.get_snapshot()

    if qb_snapshot and qb_snapshot.fetched_at:
        qb_payments_display = _format_money(int(qb_snapshot.payments_this_month))
        last_pull_display = timezone.localtime(qb_snapshot.fetched_at).strftime(
            "%b %d, %Y %I:%M %p"
        ).replace(" 0", " ")
    else:
        qb_payments_display = "—"
        last_pull_display = "Never"

    qb_sync_status = qb_snapshot.status if qb_snapshot else "offline"
    qb_sync_error = qb_snapshot.last_error if qb_snapshot else ""

    dashboard_metrics = {
        "active_jobs": len(dashboard_jobs),
        "under_contract": _format_money(contract_total),
        "collected": _format_money(collected_total),
        "outstanding": _format_money(outstanding_total),
        "qb_payments": qb_payments_display,       # real: from snapshot
        "qb_matched": f"{matched_count} / {len(bill_rows)}" if bill_rows else "0 / 0",
        "qb_unmatched": unmatched_count,
        "contract_revenue": _format_money(contract_total),
        "actual_cost": _format_money(actual_total),
        "live_margin_pct": f"{live_margin_pct:.1f}%",
        "last_pull": last_pull_display,           # real: from snapshot.fetched_at
        "is_connected": qb_conn is not None,      # real: from QbConnection row
        "qb_sync_status": qb_sync_status,         # "ok" / "stale" / "offline"
        "qb_sync_error": qb_sync_error,
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
        "all_projects_active_by_branch": active_projects_by_branch,
        "all_projects_closed_by_month": closed_projects_by_month,
        "active_projects": active_projects,
        "closed_projects": closed_projects,
    }


def _build_manager_ui_context():
    manager, _ = _build_manager_owner_data()
    rows = _build_project_ui_rows(manager.get("projects", []))
    active_projects = [p for p in rows if p["phase"] != "closed"]
    closed_projects = [p for p in rows if p["phase"] == "closed"]
    active_projects_by_branch = _group_projects_by_branch(active_projects)
    closed_projects_by_month = _group_projects_by_closed_month(closed_projects)

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
        "builds_active_by_branch": active_projects_by_branch,
        "builds_closed_by_month": closed_projects_by_month,
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


def _sales_in_progress_phase_label(deposit_paid, loan_closed):
    """Lightweight pseudo-phase used by the phase filter on the sales pipeline.

    The "real" phase model (estimate/framing/...) doesn't apply yet — these
    contracts are all pre-handoff. What sales actually filters on is where
    they are in the pre-handoff funnel."""
    if deposit_paid and loan_closed:
        return "Ready to Finalize"
    if deposit_paid:
        return "Awaiting Loan Close"
    return "Awaiting Deposit"


def _job_display_address(job):
    """Best-effort customer/site address for display in lists.

    The wizard saves to TWO separate address representations:
      - `customer_addr` — legacy single-line field (Step 1 "Address")
      - `site_street/city/state/zip` and `bill_street/city/state/zip` —
        structured V10 fields (filled in on the wizard's Customer step)

    Wizard-created contracts often have `customer_addr` blank but the
    structured site/bill fields populated. Fall back to those so the
    table/card row still shows an address.
    """
    if job.customer_addr:
        return job.customer_addr
    parts = []
    if job.site_street:
        parts.append(job.site_street)
    site_locality = ", ".join(p for p in (job.site_city, job.site_state) if p)
    if site_locality:
        parts.append(site_locality)
    if job.site_zip:
        parts.append(job.site_zip)
    if not parts:
        # No site address either — fall back to billing address.
        if job.bill_street:
            parts.append(job.bill_street)
        bill_locality = ", ".join(p for p in (job.bill_city, job.bill_state) if p)
        if bill_locality:
            parts.append(bill_locality)
        if job.bill_zip:
            parts.append(job.bill_zip)
    return " ".join(parts).strip()


def _build_sales_in_progress_row(job):
    plan_name = job.floor_plan.name if job.floor_plan else "Custom"
    branch_label = job.branch.label if job.branch else "Unassigned"
    p10_amount = int(_to_number(job.p10_material))
    edit_url_name = "sales_turnkey_edit" if job.job_mode == "turnkey" else "sales_shell_edit"
    deposit_paid = _job_deposit_paid(job)
    loan_closed = _job_loan_closed(job)
    phase_label = _sales_in_progress_phase_label(deposit_paid, loan_closed)
    address = _job_display_address(job)
    subtitle_parts = [plan_name]
    if address:
        subtitle_parts.append(address)
    if job.order_number:
        subtitle_parts.append(f"#{job.order_number}")
    row = {
        "id": job.id,
        "name": job.customer_name or f"Build #{job.id}",
        "model_name": plan_name,
        "branch_label": branch_label,
        "phase_label": phase_label,
        "subtitle": " · ".join(subtitle_parts),
        "created_at": job.created_at,
        "address": address,
        "order_number": job.order_number or "",
        "p10_amount": p10_amount,
        "p10_display": _format_money(p10_amount),
        "deposit_paid": deposit_paid,
        "loan_closed": loan_closed,
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
    branch_label = job.branch.label if job.branch else "Unassigned"
    phase_label = "Stale Lead" if stale else "Active Lead"
    address = _job_display_address(job)
    subtitle_parts = []
    if source_display:
        subtitle_parts.append(source_display)
    if address:
        subtitle_parts.append(address)
    if created_display:
        subtitle_parts.append(f"Added {created_display}")
    return {
        "id": job.id,
        "name": job.customer_name or f"Lead #{job.id}",
        "phone": job.customer_phone or "",
        "email": job.customer_email or "",
        "address": address,
        "branch_label": branch_label,
        "phase_label": phase_label,
        "subtitle": " · ".join(subtitle_parts),
        "created_at": job.created_at,
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
    branch_label = job.branch.label if job.branch else "Unassigned"
    p10_amount = int(_to_number(job.p10_material))
    closed_at = job.sales_closed_at
    closed_display = ""
    if closed_at:
        local_closed = timezone.localtime(closed_at) if timezone.is_aware(closed_at) else closed_at
        closed_display = local_closed.strftime("%b %d, %Y")
    address = _job_display_address(job)
    subtitle_parts = [plan_name]
    if address:
        subtitle_parts.append(address)
    if job.order_number:
        subtitle_parts.append(f"#{job.order_number}")
    if closed_display:
        subtitle_parts.append(f"Closed {closed_display}")
    row = {
        "id": job.id,
        "name": job.customer_name or f"Build #{job.id}",
        "model_name": plan_name,
        "branch_label": branch_label,
        "phase_label": "Closed",
        "subtitle": " · ".join(subtitle_parts),
        "address": address,
        "closed_at": closed_at,
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

    lead_rows_by_branch = _group_projects_by_branch(lead_rows)
    in_progress_rows_by_branch = _group_projects_by_branch(in_progress_rows)
    closed_rows_by_month = _group_projects_by_closed_month(closed_rows)

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
        "projects_in_progress_by_branch": in_progress_rows_by_branch,
        "projects_closed": closed_rows,
        "projects_closed_by_month": closed_rows_by_month,
        "leads": lead_rows,
        "leads_by_branch": lead_rows_by_branch,
        "in_progress_count": len(in_progress_rows),
        "closed_count": len(closed_rows),
        "leads_count": len(lead_rows),
        "exterior_rates": exterior_rates,
        "interior_rates": interior_rates,
    }


def _mark_draw_complete(job_id, draw_number):
    """Mark the specified draw as INVOICED ("due to be paid"), advance the
    next pending draw to CURRENT, and update the corresponding QB Invoice's
    DueDate to today.

    Phase 4 lifecycle:
      CURRENT  -- waiting for PM action
        |  PM clicks Mark Complete  (this function)
        v
      INVOICED -- "due to be paid"; QB Invoice DueDate=today
        |  Accountant records Payment in QB; next qb_pull observes Balance=0
        v
      PAID     -- bank funds received; flipped by qb_pull, NOT here

    Idempotent and race-safe. If the draw is already INVOICED or PAID, the
    SQL UPDATE filters on STATUS_CURRENT only, so a second click is a no-op.

    Returns `(today, event)` -- `event` is the QbInvoiceEvent row (the one
    created at sales_finalize_contract_view time, now stamped with
    qb_due_marked_at). Callers attach it to HTMX response headers so the
    manager-side toast can display invoice details.
    """
    from .models import QbInvoiceEvent

    draw = JobDraw.objects.get(job_id=job_id, draw_number=draw_number)
    job = draw.job

    dt = timezone.now()
    today = dt.strftime("%b ") + str(dt.day)

    # Atomic conditional update: flip status to INVOICED only if currently
    # CURRENT. Spam clicks or concurrent tabs lose the race silently.
    won_race = JobDraw.objects.filter(
        pk=draw.pk,
        status=JobDraw.STATUS_CURRENT,
    ).update(
        status=JobDraw.STATUS_INVOICED,
    )

    if not won_race:
        # Already advanced past CURRENT -- another tab beat us. Return
        # the most recent event for the HTMX header; no QB writes.
        existing = (
            QbInvoiceEvent.objects.filter(draw_id=draw.pk)
            .order_by("-created_at")
            .first()
        )
        if existing is not None:
            return today, existing
        from . import qb_invoice as _qi
        synthetic = _qi._record_fallback_event(
            job, draw, _qi._phase_label_for(draw),
            draw.amount or 0,
            "Draw was already advanced; no QB write was performed.",
        )
        return today, synthetic

    # We won the race -- promote the next PENDING draw to CURRENT so the
    # PM dashboard's "Mark Complete" button always has a target.
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

    # Phase 4: PM "Mark Complete" is a LOCAL status change only -- no
    # synchronous QB write. The corresponding QB Invoice already exists
    # (created at sales-finalize via push_draw_schedule_for_job). The
    # accountant decides when to pay that Invoice in QB; qb_pull's
    # refresh_draw_invoices_for_job is the path that flips the draw to
    # PAID once Balance == 0.
    #
    # Why no DueDate update here? It would add 3-4 seconds of QB API
    # round-trip to the HTMX response, which the user perceives as a
    # "stuck loading" spinner. The accountant doesn't need a DueDate
    # signal to know which invoice to pay -- they get that out-of-band
    # from the PM (or by seeing the local manager dashboard show "Due").
    #
    # Surface the existing QbInvoiceEvent for the manager-toast HX-Trigger.
    # If somehow no event exists (legacy finalize before Phase 4 wired
    # up + no backfill yet), record a synthetic fallback so the toast
    # still has something to render.
    event = (
        QbInvoiceEvent.objects
        .filter(job=job, draw=draw, status=QbInvoiceEvent.STATUS_SENT)
        .order_by("-created_at")
        .first()
    )
    if event is None:
        # No QbInvoiceEvent for this draw -- record a local fallback for the
        # toast/bell. The actual QB write (creating the Invoice) is deferred
        # to the next time qb_pull or finalize runs.
        from . import qb_invoice as _qi
        event = _qi._record_fallback_event(
            job, draw, _qi._phase_label_for(draw),
            draw.amount or 0,
            "Draw marked complete locally; QB invoice will sync on next refresh.",
        )
    # Best-effort timestamp: stamp qb_due_marked_at on the existing event so
    # the manager dashboard knows when the PM clicked Mark Complete, even
    # though we didn't touch QB. (No QB API call -- pure DB UPDATE.)
    elif not event.qb_due_marked_at:
        event.qb_due_marked_at = dt
        event.save(update_fields=["qb_due_marked_at"])

    return today, event


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

    today, event = _mark_draw_complete(job_id, draw_number)

    return JsonResponse({
        "ok": True,
        "paid_date": today,
        "invoice": {
            "number": event.display_invoice_number,
            "team": event.team_name,
            "amount": f"{event.amount:,.0f}",
            "status": event.status,
            "url": event.qb_invoice_url,
        },
    })


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
def owner_closed_projects_panel_view(request):
    if not request.htmx:
        return redirect("owner")
    context = _build_owner_ui_context()
    return render(
        request,
        "owner/closed_projects.html",
        {
            "all_projects_closed": context["all_projects_closed"],
            "all_projects_closed_by_month": context["all_projects_closed_by_month"],
        },
    )


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


@role_required(AppUser.ROLE_SALES)
@xframe_options_sameorigin
def sales_floor_plan_pdf_view(request, filename):
    safe_name = Path((filename or "").strip()).name
    if not safe_name or not safe_name.lower().endswith(".pdf"):
        raise Http404("PDF not found")

    pdf_root = (settings.BASE_DIR / "pdf-plans").resolve()
    pdf_path = (pdf_root / safe_name).resolve()
    if pdf_root not in pdf_path.parents or not pdf_path.is_file():
        raise Http404("PDF not found")

    response = FileResponse(pdf_path.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return response


def _wizard_state_for_job(job):
    """Return a wizard-ready STATE dict for rehydrating the BuildWizard.

    For committed contracts we use the saved ``wizard_state`` verbatim.
    For leads (which never ran the wizard) we synthesize a minimal state
    pre-filling the Step-1 customer fields the V10 wizard expects.
    """
    state = job.wizard_state or {}
    if job.is_lead and not state:
        return {
            "customer": {
                "name":  job.customer_name or "",
                "addr":  job.customer_addr or "",
                "order": job.order_number or "",
                "rep":   job.sales_rep or "",
                "p10":   0,
                "email": job.customer_email or "",
                "phone": job.customer_phone or "",
            },
        }
    return state


@role_required(AppUser.ROLE_SALES)
def sales_turnkey_view(request, job_id=None):
    """Render the unified Interior Contract Wizard. URL name kept for
    backward-compat with the old turnkey-only route; the wizard is now
    interior-only regardless of how it's reached."""
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
            "existing_state": existing_state,
            "existing_job_id": existing_job_id,
        },
    )


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
def manager_builds_active_panel_view(request):
    if not request.htmx:
        return redirect("manager")
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/active_builds.html",
        {
            "builds_active": context["builds_active"],
            "builds_active_by_branch": context["builds_active_by_branch"],
        },
    )


@role_required(AppUser.ROLE_PM)
def manager_builds_closed_panel_view(request):
    if not request.htmx:
        return redirect("manager")
    context = _build_manager_ui_context()
    return render(
        request,
        "manager/closed_builds.html",
        {
            "builds_closed": context["builds_closed"],
            "builds_closed_by_month": context["builds_closed_by_month"],
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
def manager_qb_draws_refresh_view(request):
    """Pull draw-invoice paid status from QuickBooks, then re-render the
    Draws panel.

    Phase 4 lifecycle: PM clicks Mark Complete -> draw is INVOICED.
    Accountant records a Payment in the QB sandbox. THIS endpoint walks
    every INVOICED draw across active jobs, queries the corresponding
    QB Invoice's Balance, and flips draws to PAID where QB shows
    Balance == 0. Then returns the refreshed Draws panel HTML so the
    PM can see updates without leaving their dashboard.

    Focused (only INVOICED draws) so it's fast (~1-2s for a typical
    sandbox), unlike the full owner-dashboard refresh which also pulls
    Bills + Payments aggregates.
    """
    if not request.htmx:
        return redirect("manager")

    from . import qb_client, qb_pull
    totals = {"paid_now": 0, "still_open": 0, "skipped": 0}
    error_msg = ""

    connection = qb_client.get_connection()
    if connection is None:
        error_msg = "QuickBooks is not connected. Have an exec connect via the owner dashboard."
    else:
        try:
            with qb_client.with_qb_client() as qb:
                # Active jobs with a cached QB Customer mapping. Bound the loop
                # so a sandbox with hundreds of jobs doesn't burn the request.
                active_jobs = (
                    Job.objects
                    .exclude(current_phase="closed")
                    .filter(qb_customer_map__isnull=False)
                    .select_related("qb_customer_map")[:50]
                )
                for job in active_jobs:
                    try:
                        counts = qb_pull.refresh_draw_invoices_for_job(qb, job)
                        for k, v in counts.items():
                            totals[k] += v
                    except Exception as job_exc:  # noqa: BLE001
                        # One job's failure shouldn't kill the whole refresh.
                        import logging
                        logging.getLogger(__name__).warning(
                            "manager_qb_draws_refresh_view: job=%s error: %s",
                            job.pk, job_exc,
                        )
        except qb_client.QbNotConnected as exc:
            error_msg = str(exc)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).exception("manager_qb_draws_refresh_view failed")
            error_msg = f"{type(exc).__name__}: {exc}"

    # Re-render Draws panel with the updated state.
    context = _build_manager_ui_context()
    response = render(
        request,
        "manager/draws.html",
        {
            "draws_active": context["draws_active"],
            "draws_closed": context["draws_closed"],
        },
    )

    # Toast feedback via HX-Trigger. Picked up by manager.js's existing
    # qb-invoice-sent listener (we reuse it to avoid adding a new listener).
    if error_msg:
        toast = f"Refresh failed: {error_msg}"
    elif totals["paid_now"] > 0:
        n = totals["paid_now"]
        toast = f"{n} draw{'s' if n != 1 else ''} marked Paid from QuickBooks"
    else:
        toast = "Refresh complete -- no new payments in QuickBooks"
    import json as _json
    response["HX-Trigger"] = _json.dumps({
        "manager-refresh": {},
        "qb-invoice-sent": {
            "invoice_number": "",
            "team": "",
            "amount": "",
            "status": "sent" if not error_msg else "failed_fallback",
            "url": "",
            "message": toast,
        },
    })
    return response


@role_required(AppUser.ROLE_PM)
def manager_change_order_modal_view(request):
    """Render the Create Change Order modal form for a given job. HTMX-only —
    swapped into the modal host on the My Builds panel."""
    if not request.htmx:
        return redirect("manager")
    try:
        job_id = int(request.GET.get("job_id") or 0)
    except (TypeError, ValueError):
        return HttpResponse(status=400)
    try:
        job = Job.objects.select_related("branch", "floor_plan").prefetch_related("demo_draws").get(pk=job_id)
    except Job.DoesNotExist:
        return HttpResponse(status=404)

    # Server-side gate: change orders require a closed loan (1st Home Draw
    # paid). UI hides the button, but defend against a direct request too.
    if not _job_loan_closed(job):
        return HttpResponse(
            "Change orders are unavailable until the sales rep closes the loan.",
            status=403,
        )

    # Pre-allocate the next CO number so the modal can show it as the heading.
    next_number = (
        JobChangeOrder.objects.filter(job=job).order_by("-number").values_list("number", flat=True).first() or 0
    ) + 1
    # Match the logic used by _build_manager_owner_data: contract = sum of
    # demo draws. Avoids _estimate_job_contract, which references a Job
    # field (int_contract) that doesn't exist on the model.
    draws_total = int(sum(int(_to_number(d.amount)) for d in job.demo_draws.all()))
    contract_total = draws_total or int(_to_number(job.budget_total_amount))

    return render(
        request,
        "manager/_change_order_modal.html",
        {
            "job": job,
            "next_number": next_number,
            "contract_total": contract_total,
            "contract_total_display": _format_money(contract_total),
            # Default to the sales rep on file — closest analogue to "Project Manager".
            "default_pm": job.sales_rep or "",
            "default_customer": job.customer_name or "",
            "default_address": job.customer_addr or "",
        },
    )


@role_required(AppUser.ROLE_PM)
@require_POST
@csrf_protect
def manager_change_order_create_view(request):
    """Persist a new change order from the modal form, then re-render the
    Active Builds panel so the card immediately reflects the new entry."""
    try:
        job_id = int(request.POST.get("job_id") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid job"}, status=400)
    try:
        job = Job.objects.prefetch_related("demo_draws").get(pk=job_id)
    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    if not _job_loan_closed(job):
        return JsonResponse(
            {"error": "Loan must be closed before a change order can be created."},
            status=403,
        )

    def _decimal(name, default="0"):
        raw = (request.POST.get(name) or "").strip().replace(",", "").replace("$", "")
        if raw == "":
            raw = default
        try:
            return Decimal(raw)
        except Exception:
            return Decimal(default)

    description = (request.POST.get("description") or "").strip()
    price_change = _decimal("price_change")
    new_total = _decimal("new_contract_total")
    timing = (request.POST.get("payment_timing") or "immediately").strip()
    valid_timings = {key for key, _ in JobChangeOrder.PAYMENT_TIMING_CHOICES}
    if timing not in valid_timings:
        timing = "immediately"

    next_number = (
        JobChangeOrder.objects.filter(job=job).order_by("-number").values_list("number", flat=True).first() or 0
    ) + 1

    JobChangeOrder.objects.create(
        job=job,
        number=next_number,
        customer_name=(request.POST.get("customer_name") or job.customer_name or "")[:200],
        project_address=(request.POST.get("project_address") or job.customer_addr or "")[:300],
        project_manager=(request.POST.get("project_manager") or job.sales_rep or "")[:120],
        description=description,
        price_change=price_change,
        new_contract_total=new_total,
        payment_timing=timing,
    )

    if request.htmx:
        context = _build_manager_ui_context()
        response = render(
            request,
            "manager/active_builds.html",
            {
                "builds_active": context["builds_active"],
                "builds_active_by_branch": context["builds_active_by_branch"],
            },
        )
        # Closes the modal on the client and shows a confirmation toast.
        import json as _json
        response["HX-Trigger"] = _json.dumps({
            "change-order-created": {
                "number": next_number,
                "customer": job.customer_name or f"Build #{job.id}",
                "amount": f"{price_change:,.2f}",
            },
            "manager-refresh": {},
        })
        return response
    return redirect("manager")


@role_required(AppUser.ROLE_PM)
def manager_mark_complete_modal_view(request):
    """Render the Cancel/Confirm modal for Mark Complete. HTMX-only — swapped
    into the modal host on the Draws panel so the PM gets a soft confirmation
    step before the QB invoice POST fires."""
    if not request.htmx:
        return redirect("manager")
    try:
        job_id = int(request.GET.get("job_id") or 0)
        draw_number = int(request.GET.get("draw_number") or 0)
    except (TypeError, ValueError):
        return HttpResponse(status=400)
    panel = (request.GET.get("panel") or "draws").strip().lower()
    if panel not in {"draws", "builds", "builds-active", "builds-closed", "budgets"}:
        panel = "draws"
    try:
        draw = JobDraw.objects.select_related("job").get(
            job_id=job_id, draw_number=draw_number
        )
    except JobDraw.DoesNotExist:
        return HttpResponse(status=404)
    return render(
        request,
        "manager/_confirm_complete_modal.html",
        {
            "job": draw.job,
            "draw": draw,
            "panel": panel,
            "amount_display": _format_money(int(_to_number(draw.amount))),
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
        _today, event = _mark_draw_complete(job_id, draw_number)
    except JobDraw.DoesNotExist:
        return JsonResponse({"error": "Draw not found"}, status=404)

    if request.htmx:
        context = _build_manager_ui_context()
        template_map = {
            "builds": "manager/my_builds.html",
            "builds-active": "manager/active_builds.html",
            "builds-closed": "manager/closed_builds.html",
            "budgets": "manager/budgets.html",
            "draws": "manager/draws.html",
        }
        template_name = template_map.get(panel, "manager/draws.html")
        partial_context = {
            "manager/my_builds.html": {
                "builds_active": context["builds_active"],
                "builds_closed": context["builds_closed"],
            },
            "manager/active_builds.html": {
                "builds_active": context["builds_active"],
                "builds_active_by_branch": context["builds_active_by_branch"],
            },
            "manager/closed_builds.html": {
                "builds_closed": context["builds_closed"],
                "builds_closed_by_month": context["builds_closed_by_month"],
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
        # JSON-form HX-Trigger fires TWO DOM CustomEvents on document.body:
        #   * "manager-refresh" — existing panel-refresh signal
        #   * "qb-invoice-sent" — new toast signal with invoice detail on
        #     event.detail. Picked up by showToast() in manager.js.
        import json as _json
        response["HX-Trigger"] = _json.dumps({
            "manager-refresh": {},
            "qb-invoice-sent": {
                "invoice_number": event.display_invoice_number,
                "team": event.team_name,
                "amount": f"{event.amount:,.0f}",
                "status": event.status,
                "url": event.qb_invoice_url,
            },
        })
        return response
    return redirect("manager")


@never_cache
@role_required(AppUser.ROLE_EXEC)
def owner_view(request):
    # @never_cache prevents the browser from restoring this page from bfcache
    # after the user logs out. Without it, hitting Back would resurrect the
    # page with its HTMX polls (notification bell, dashboard refresh) still
    # scheduled. The next poll would hit role_required against an empty
    # session, return 401 + HX-Redirect=login, and yank the user to the
    # login page seemingly out of nowhere.
    context = _build_owner_ui_context()
    # Unified QB card context — same shape as qb_status_view / qb_sync_refresh_view
    # so the {% include "owner/_qb_status.html" %} in owner/index.html hydrates
    # identically on first load and on every HTMX refresh.
    qb_ctx = _qb_status_context()
    return render(
        request,
        "owner/index.html",
        {
            "kpis": context["kpis"],
            "owner_total": context["owner_total"],
            **qb_ctx,
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
            "projects_in_progress_by_branch": context["projects_in_progress_by_branch"],
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
            "projects_closed_by_month": context["projects_closed_by_month"],
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


def _push_draw_schedule_for_job_async(job_id):
    """Best-effort background QB push after sales finalize.

    Keeps the HTMX finalize response fast so the UI updates immediately,
    even if QuickBooks is slow/unavailable.
    """
    from threading import Thread

    def _worker(target_job_id):
        from . import qb_invoice
        try:
            target_job = Job.objects.get(pk=target_job_id)
        except Job.DoesNotExist:
            return
        try:
            qb_invoice.push_draw_schedule_for_job(target_job)
        except Exception:
            # Never break sales finalize on QB transport/API errors.
            pass

    Thread(target=_worker, args=(job_id,), daemon=True).start()


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
        # Hand-off to the PM: promote the lowest-numbered non-paid draw to
        # CURRENT so the manager's "Mark Complete" button renders. Without
        # this the PM dashboard shows only PENDING rows with no action.
        next_current = (
            JobDraw.objects.filter(job=job)
            .exclude(status=JobDraw.STATUS_PAID)
            .order_by("draw_number")
            .first()
        )
        if next_current and next_current.status != JobDraw.STATUS_CURRENT:
            next_current.status = JobDraw.STATUS_CURRENT
            next_current.save(update_fields=["status"])

    # ── Phase 4: bulk-push draw schedule to QuickBooks (async) ──
    # Dispatch after commit so UI isn't blocked on QB API latency.
    transaction.on_commit(lambda: _push_draw_schedule_for_job_async(job.id))

    if request.htmx:
        context = _build_sales_ui_context(request)
        response = render(
            request,
            "sales/overview/in_progress.html",
            {
                "projects_in_progress": context["projects_in_progress"],
                "projects_in_progress_by_branch": context["projects_in_progress_by_branch"],
            },
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
    response = render(
        request,
        "sales/overview/leads.html",
        {
            "leads": context["leads"],
            "leads_by_branch": context["leads_by_branch"],
        },
    )
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
        {
            "leads": context["leads"],
            "leads_by_branch": context["leads_by_branch"],
        },
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
    customer_name  = (customer.get("name") or "").strip()
    customer_addr  = (customer.get("addr") or "").strip()
    sales_rep      = (customer.get("rep")  or "").strip()
    order_number   = (customer.get("order") or "").strip()
    customer_email = (customer.get("email") or "").strip()
    customer_phone = (customer.get("phone") or "").strip()
    model_name    = (body.get("model") or "").strip()
    branch_key    = (body.get("branch") or "").strip()
    p10           = int(body.get("p10") or 0)
    shell_total   = int(body.get("shellTotal") or 0)
    turnkey_total = int(body.get("turnkeyTotal") or 0)
    shell_contract = int(body.get("shellContract") or 0)
    concrete_budget = int(body.get("concreteBudget") or 0)
    labor_budget = int(body.get("laborBudget") or 0)
    draws_payload = body.get("draws") or []
    trade_budgets_payload = body.get("tradeBudgets") or []
    budget_total_payload = int(body.get("budgetTotal") or 0)
    contract_meta = body.get("contractMeta") or {}

    # Co-buyer + structured customer fields (V10)
    co_buyer_name  = (customer.get("coBuyerName") or "").strip()
    co_buyer_email = (customer.get("coBuyerEmail") or "").strip()
    co_buyer_phone = (customer.get("coBuyerPhone") or "").strip()
    customer_type  = (customer.get("customerType") or "individual").strip()
    bill_street    = (customer.get("billStreet") or "").strip()
    bill_city      = (customer.get("billCity") or "").strip()
    bill_state     = (customer.get("billState") or "TN").strip()
    bill_zip       = (customer.get("billZip") or "").strip()
    site_street    = (customer.get("siteStreet") or "").strip()
    site_city      = (customer.get("siteCity") or "").strip()
    site_state     = (customer.get("siteState") or "TN").strip()
    site_zip       = (customer.get("siteZip") or "").strip()
    site_same      = bool(customer.get("siteSameAsBilling"))
    bank_name      = (customer.get("bankName") or "").strip()
    sm_order_secondary = (customer.get("smOrderSecondary") or "").strip()
    contracts_rep  = (customer.get("contractsRep") or "").strip()
    custom_rep_name = (customer.get("customRepName") or "").strip()

    # contractMeta (V10) — supersedes / permit / site prep / detached shop / foundation
    foundation_type = (contract_meta.get("foundationType") or "slab").strip()
    permit_allowance = int(contract_meta.get("permitAllowance") or 2000)
    site_prep_allowance = int(contract_meta.get("sitePrepAllowance") or 0)
    det_shop_material = int(contract_meta.get("detShopMaterial") or 0)
    det_shop_conc_labor = int(contract_meta.get("detShopConcLabor") or 0)
    contract_notes = contract_meta.get("notes") or ""
    supersedes = bool(contract_meta.get("supersedes"))
    supersedes_reason = (contract_meta.get("supersedesReason") or "").strip()

    if not customer_name:
        return JsonResponse({"error": "customer.name is required"}, status=400)

    # ── Resolve FKs ──
    branch_obj = Branch.objects.filter(key=branch_key).first()
    plan_obj   = FloorPlanModel.objects.filter(name__iexact=model_name).first()

    # Interior-only tool — turnkey is the only mode now. Total contract value =
    # sales-rep-entered shell + computed interior contract.
    contract_total = turnkey_total or shell_total
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
        "customer_addr":   customer_addr,
        "customer_email":  customer_email,
        "customer_phone":  customer_phone,
        "sales_rep":       sales_rep,
        "order_number":    order_number,
        "branch":          branch_obj,
        "floor_plan":      plan_obj,
        "job_mode":        "turnkey",
        "p10_material":    p10,
        "shell_contract":  shell_contract,
        "concrete_budget": concrete_budget,
        "labor_budget":    labor_budget,
        "budget_total_amount": budget_total,
        "budget_spent_amount": 0,
        "current_phase":   "estimate",
        # New V10 customer fields
        "co_buyer_name":   co_buyer_name,
        "co_buyer_email":  co_buyer_email,
        "co_buyer_phone":  co_buyer_phone,
        "customer_type":   customer_type,
        "bill_street":     bill_street,
        "bill_city":       bill_city,
        "bill_state":      bill_state,
        "bill_zip":        bill_zip,
        "site_street":     site_street,
        "site_city":       site_city,
        "site_state":      site_state,
        "site_zip":        site_zip,
        "site_same_as_billing": site_same,
        "bank_name":       bank_name,
        "order_number_secondary": sm_order_secondary,
        "contracts_rep":   contracts_rep,
        "custom_rep_name": custom_rep_name,
        # contractMeta (V10)
        "foundation_type": foundation_type,
        "permit_allowance": permit_allowance,
        "site_prep_allowance": site_prep_allowance,
        "det_shop_material": det_shop_material,
        "det_shop_conc_labor": det_shop_conc_labor,
        "contract_notes":  contract_notes,
        "supersedes_prev_contract": supersedes,
        "supersedes_reason": supersedes_reason,
        # A saved wizard is never a lead — this flips the row to In Progress.
        "is_lead":         False,
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

    # Eager QB Customer push -- creates the QB Customer immediately so the
    # accountant can find this job in the QB sandbox by SM Order # and start
    # entering Bills against it before any draws have been pushed. Never
    # raises and never blocks the contract save (returns None on failure).
    from . import qb_invoice
    try:
        qb_invoice.ensure_qb_customer_for_job(job)
    except Exception:  # noqa: BLE001
        pass  # truly never break the save

    return JsonResponse({"ok": True, "job_id": job.id, "created": created})


# ═══════════════════════════════════════════════════════════════
# QUICKBOOKS ONLINE — OAuth connect / callback / disconnect
# ═══════════════════════════════════════════════════════════════
#
# Flow:
#   1. Exec clicks "Connect QuickBooks" on the owner dashboard.
#   2. qb_connect_view builds the Intuit authorize URL and redirects the
#      browser to it. We store a CSRF-style `state` string in the session
#      and verify it on callback (Intuit returns it unchanged).
#   3. Intuit redirects to qb_callback_view with ?code=...&state=...&realmId=...
#   4. We exchange the code for tokens, persist the QbConnection row,
#      and redirect back to the owner dashboard.
#
# Sandbox caveat: the first Connect in a new browser profile will redirect
# through Intuit's sandbox auth UI — you sign in with the same Intuit account
# that owns the developer app.


def _qb_config_missing_response():
    """Shared error response when QB_CLIENT_ID / QB_CLIENT_SECRET aren't set."""
    html = (
        "<h1>QuickBooks is not configured</h1>"
        "<p>Set <code>QB_CLIENT_ID</code> and <code>QB_CLIENT_SECRET</code> "
        "in environment variables (or in <code>stmc/settings.py</code>) and "
        "restart the server. See the comment block in settings.py for exact steps.</p>"
    )
    return HttpResponse(html, status=500)


# Namespace for our OAuth state signer — keeps these tokens from ever
# colliding with other uses of TimestampSigner in the project.
_QB_STATE_SALT = "stmc_ops.qb.oauth_state"
# State must survive the round-trip to Intuit + user authorization clicks.
# 10 minutes is generous without being so long that a captured URL stays
# exploitable for an attacker.
_QB_STATE_MAX_AGE_SECONDS = 10 * 60


def _build_qb_oauth_state(user_id: int) -> str:
    """Generate a signed, timestamped state token that also identifies the
    user who initiated the flow.

    Two jobs in one token:

    1. CSRF protection for the OAuth callback (its original purpose).
       Only holders of SECRET_KEY can mint a valid signature, and the
       embedded timestamp bounds replay to 10 minutes.
    2. Re-establish the user's session after callback. Some browsers
       (incognito, strict tracking, Safari ITP) drop the session cookie
       on the Intuit→localhost cross-site redirect. Rather than asking
       the user to log in again after every Connect flow, we embed their
       user_id in the state and use it on callback to log them back in.

    Security model: this turns the state into a short-lived login ticket
    for one specific user. It's safe because:
      - Only our server can sign a valid state (SECRET_KEY).
      - The ticket expires in 10 minutes.
      - Intuit's authorization code is single-use, so a replay of the
        full callback URL can only complete the flow once.
      - The state was issued to a user who was already authenticated
        (qb_connect_view is @role_required).
    """
    import secrets as _secrets
    from django.core.signing import TimestampSigner
    signer = TimestampSigner(salt=_QB_STATE_SALT)
    # Payload = "<user_id>:<nonce>" — nonce prevents two concurrent flows
    # for the same user from producing identical tokens.
    payload = f"{int(user_id)}:{_secrets.token_urlsafe(12)}"
    return signer.sign(payload)


def _verify_qb_oauth_state(state: str):
    """Verify the signature + age. Return the embedded user_id (int) on
    success, or None on any failure (bad signature, expired, malformed)."""
    from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
    signer = TimestampSigner(salt=_QB_STATE_SALT)
    try:
        payload = signer.unsign(state, max_age=_QB_STATE_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    user_id_str, _, _nonce = payload.partition(":")
    try:
        return int(user_id_str)
    except (TypeError, ValueError):
        return None


@role_required(AppUser.ROLE_EXEC)
def qb_connect_view(request):
    """Start the OAuth 2.0 authorization flow. Redirects the browser to
    Intuit. On success, Intuit will redirect back to qb_callback_view."""
    from . import qb_client

    try:
        auth_client = qb_client.build_auth_client()
    except qb_client.QbConfigError:
        return _qb_config_missing_response()

    # Signed `state` — proves on callback that we issued it AND carries
    # the initiating user's id so we can restore their session after
    # the round-trip even if the browser dropped the session cookie
    # (incognito / strict tracking protection / Safari ITP).
    state = _build_qb_oauth_state(request.user.id)

    authorize_url = auth_client.get_authorization_url(
        qb_client._scope_objects(),
        state_token=state,
    )
    return redirect(authorize_url)


def qb_callback_view(request):
    """OAuth redirect target. Exchanges the authorization code for tokens
    and persists a QbConnection row.

    NOT decorated with @role_required and NOT session-dependent. The OAuth
    2.0 `state` token we issued in qb_connect_view is signed with Django's
    SECRET_KEY via TimestampSigner; verifying the signature proves we
    issued it, and the embedded timestamp bounds replay attacks to a
    10-minute window. This design survives:
      * session cookie being dropped on the cross-site redirect
        (strict tracking protection, Safari ITP, incognito mode, third-
        party cookie blocking)
      * the user opening the OAuth flow in a new tab, window, or browser
      * any browser quirk around SameSite=Lax on cross-site redirects
    """
    from . import qb_client
    from intuitlib.exceptions import AuthClientError

    # Intuit may also hit us with ?error=access_denied if the user cancels.
    error = request.GET.get("error")
    if error:
        return HttpResponse(
            f"<h1>QuickBooks connection cancelled</h1><p>Intuit returned: {error}</p>"
            "<p><a href='/stmc_ops/owner/'>Back to dashboard</a></p>",
            status=400,
        )

    code = request.GET.get("code")
    realm_id = request.GET.get("realmId")
    state = request.GET.get("state")

    if not code or not realm_id:
        return HttpResponse("<h1>QuickBooks callback missing code/realmId</h1>", status=400)

    initiating_user_id = _verify_qb_oauth_state(state) if state else None
    if initiating_user_id is None:
        # Either: state missing, tampered, forged without SECRET_KEY, or
        # older than the allowed 10-minute window. Any of these = reject.
        return HttpResponse(
            "<h1>OAuth state invalid or expired</h1>"
            "<p>This callback could not be verified. Please retry the "
            "Connect QuickBooks flow — it must complete within 10 "
            "minutes of clicking the button.</p>"
            "<p><a href='/stmc_ops/owner/'>Back to dashboard</a></p>",
            status=400,
        )

    try:
        auth_client = qb_client.build_auth_client()
    except qb_client.QbConfigError:
        return _qb_config_missing_response()

    try:
        auth_client.get_bearer_token(code, realm_id=realm_id)
    except AuthClientError as exc:
        return HttpResponse(
            f"<h1>QuickBooks token exchange failed</h1><pre>{exc}</pre>",
            status=500,
        )

    # Look up the user who initiated this flow (per the signed state).
    # Used both for the audit field below and to restore their session if
    # the browser dropped the session cookie on the cross-site redirect.
    initiating_user = None
    try:
        initiating_user = AppUser.objects.filter(pk=initiating_user_id).first()
    except Exception:
        pass

    audit_email = ""
    if request.user.is_authenticated:
        audit_email = getattr(request.user, "email", "") or ""
    elif initiating_user:
        audit_email = initiating_user.email or ""

    qb_client.save_connection_from_auth_client(
        auth_client,
        realm_id=realm_id,
        connected_by_email=audit_email,
    )

    # Session restoration: if the browser didn't round-trip the session
    # cookie (common in incognito / Safari ITP), request.user will be
    # AnonymousUser at this point even though the signed state proves
    # who started the flow. Log them back in so the redirect to /owner/
    # doesn't bounce them to login.
    if not request.user.is_authenticated and initiating_user is not None:
        from django.contrib.auth import login as _auth_login
        _auth_login(request, initiating_user)

    return redirect("owner")


def _qb_status_context():
    """Build the context dict consumed by owner/_qb_status.html.

    Shared by three entry points so the merged card renders identically:
      * owner_view (initial page render)
      * qb_status_view (HTMX refresh after connect/disconnect)
      * qb_sync_refresh_view (HTMX refresh after pulling payments)
    """
    from . import qb_client
    from . import qb_pull
    connection = qb_client.get_connection()
    snapshot = qb_pull.get_snapshot()

    if snapshot and snapshot.fetched_at:
        payments_display = f"${int(snapshot.payments_this_month):,}"
        last_pull = timezone.localtime(snapshot.fetched_at).strftime(
            "%b %d, %Y %I:%M %p"
        ).replace(" 0", " ")
    else:
        payments_display = "—"
        last_pull = "Never"

    return {
        "qb_connected": connection is not None,
        "qb_connection": connection,
        "qb_environment": settings.QB_ENVIRONMENT,
        "qb_portal_url": qb_client.portal_url(connection) if connection else "",
        "qb_payments_display": payments_display,
        "qb_last_pull": last_pull,
        "qb_sync_status": snapshot.status if snapshot else "offline",
        "qb_sync_error": snapshot.last_error if snapshot else "",
    }


@role_required(AppUser.ROLE_EXEC)
@require_POST
@csrf_protect
def qb_sync_refresh_view(request):
    """Pull fresh metrics from QB (currently just month-to-date Payments)
    and re-render the unified QB card. Never 500s — if the pull fails,
    the snapshot status becomes 'stale' and the card surfaces the warning
    pill instead of crashing the page.
    """
    from . import qb_pull
    snapshot = qb_pull.refresh_snapshot()

    response = render(request, "owner/_qb_status.html", _qb_status_context())
    import json as _json
    response["HX-Trigger"] = _json.dumps({
        "qb-sync-refreshed": {
            "status": snapshot.status,
            "payments": f"{int(snapshot.payments_this_month):,}" if snapshot.payments_this_month else "0",
            "error": snapshot.last_error,
        },
        # Also refresh the dashboard panel below — Portfolio Profit doesn't
        # depend on the QB pull today, but this keeps the two in sync if
        # Actual Cost / matching metrics get wired in later.
        "owner-dashboard-refresh": {},
    })
    return response


@role_required(AppUser.ROLE_EXEC)
@require_POST
@csrf_protect
def qb_disconnect_view(request):
    """Drop the stored connection. The user can reconnect immediately; Intuit
    itself keeps the authorization alive until the refresh token expires or
    is revoked on Intuit's side (dashboard → My Apps → Disconnect)."""
    from . import qb_client
    qb_client.disconnect()
    return redirect("owner")


@role_required(AppUser.ROLE_EXEC)
def qb_status_view(request):
    """HTMX partial: renders the unified QuickBooks card.
    Used on the owner dashboard and re-fetched after connect/disconnect."""
    return render(request, "owner/_qb_status.html", _qb_status_context())


# ─────────────────────────────────────────────────────────────
# OWNER BELL NOTIFICATIONS (Phase C)
# ─────────────────────────────────────────────────────────────
#
# The bell lives in the owner nav. It:
#   * Polls every 30 seconds for the unread count.
#   * Shows a red badge when unread > 0.
#   * Click opens a dropdown listing the 10 most recent QbInvoiceEvent rows.
#   * Each row has an × button that marks that event read.
#   * "Mark all read" button in the footer clears the badge in bulk.
#   * Dismissal is global (demo simplicity — one read_at per event, not per user).
#
# Realism hook: the toast on the exec side fires when the bell-refresh poll
# brings in a new count. The JS in owner.js tracks the last-known count and
# compares on each refresh.


def _bell_context():
    """Shared context for the two bell partials. Keeps the unread count
    and the top-10 event list in sync between the button and the dropdown."""
    from .models import QbInvoiceEvent
    events = list(QbInvoiceEvent.objects.all()[:10])
    unread_count = QbInvoiceEvent.objects.filter(read_at__isnull=True).count()
    return {
        "events": events,
        "unread_count": unread_count,
    }


@role_required(AppUser.ROLE_EXEC)
def owner_notifications_bell_view(request):
    """HTMX partial — bell button + badge. Polled every 30s by owner/index.html.
    The dropdown itself is a separate fetch so we don't ship the full event
    list on every poll."""
    return render(request, "owner/_bell.html", _bell_context())


@role_required(AppUser.ROLE_EXEC)
def owner_notifications_dropdown_view(request):
    """HTMX partial — the dropdown list. Fetched on-demand when the user
    clicks the bell (not on the 30s poll)."""
    return render(request, "owner/_bell_dropdown.html", _bell_context())


@role_required(AppUser.ROLE_EXEC)
@require_POST
@csrf_protect
def owner_notification_mark_read_view(request, event_id):
    """POST — mark one event read. Returns the refreshed bell button +
    broadcasts owner-bell-refresh so any open dropdown reloads too."""
    from .models import QbInvoiceEvent
    QbInvoiceEvent.objects.filter(pk=event_id, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    response = render(request, "owner/_bell.html", _bell_context())
    response["HX-Trigger"] = "owner-bell-refresh"
    return response


@role_required(AppUser.ROLE_EXEC)
@require_POST
@csrf_protect
def owner_notifications_mark_all_read_view(request):
    """POST — bulk mark-as-read. Same response shape as single-row dismiss."""
    from .models import QbInvoiceEvent
    QbInvoiceEvent.objects.filter(read_at__isnull=True).update(
        read_at=timezone.now()
    )
    response = render(request, "owner/_bell.html", _bell_context())
    response["HX-Trigger"] = "owner-bell-refresh"
    return response