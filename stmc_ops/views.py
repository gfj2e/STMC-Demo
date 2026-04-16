import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .pdf_generator import generate_pdf


def index(request):
    return redirect("login")


def login_view(request):
    return render(request, "login/index.html")


def sales_view(request):
    return render(request, "sales/index.html")


def manager_view(request):
    return render(request, "manager/index.html")


def owner_view(request):
    return render(request, "owner/index.html")


@csrf_exempt
@require_POST
def generate_ext_labor_pdf(request):
    """
    POST endpoint that accepts JSON state and returns a PDF file.

    Body JSON fields:
      pdf_type  : "customer" | "contractor" | "full"  (default "full")
      state     : dict matching the HTML module's JS state shape

    Example minimal state:
      {
        "model": "CAJUN",
        "branch": "summertown",
        "miles": 0,
        "custInfo": {"name": "John Doe", "addr": "123 Main St", "order": "ORD-001", "rep": "Jane", "p10": 71150},
        "slab": [{"n": "1st Floor Living Area", "sf": 1800, "tg": 0}, ...],
        "roof": [{"n": "Main Roof", "type": "metal", "steep": 0, "sf": 2013}, ...],
        "wallTuff": 1731, "wallRock": 0, "wallStone": 0, "wallType": "Metal",
        "stoneUpg": 0, "dblD": 1, "sglD": 1, "dblW": 2, "sglW": 9,
        "s2s": 0, "s2d": 0, "awnQty": 0, "cupQty": 0, "chimQty": 0,
        "foundType": "concrete", "crawlSF": 0, "sheath": 0, "g26": 0,
        "punchAmt": 2500, "customCharges": [], "ctrOv": {},
        "conc": {"sqft": 3510, "type": "4fiber", "zone": 1, "lp": false, "bp": false,
                 "wire": false, "rebar": false, "foam": 0},
        "concCustomCharges": []
      }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return JsonResponse({"error": f"Invalid JSON: {exc}"}, status=400)

    pdf_type = body.get("pdf_type", "full")
    if pdf_type not in ("customer", "contractor", "full"):
        return JsonResponse({"error": "pdf_type must be 'customer', 'contractor', or 'full'"}, status=400)

    state = body.get("state", body)  # allow state to be top-level or nested under "state"

    try:
        pdf_bytes = generate_pdf(state, pdf_type=pdf_type)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    type_labels = {
        "customer": "Customer_Contract",
        "contractor": "Contractor_Labor",
        "full": "Full_Contract",
    }
    model_slug = (state.get("model") or "STMC").replace(" ", "_")
    filename = f"STMC_{model_slug}_{type_labels[pdf_type]}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response