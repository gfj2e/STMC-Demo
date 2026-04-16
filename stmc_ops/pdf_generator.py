"""
STMC Exterior Labor Module — Python PDF Generator
==================================================
Ports all pricing logic from STMC_EXT_LABOR_MODULE_V7.html to Python.
Generates three PDF types:
  - "customer"    → Customer Contract PDF (one page)
  - "contractor"  → Contractor Labor Budget PDF (one page)
  - "full"        → Full 3-page Contract PDF (customer + contractor + draw schedule)
"""

import io
import math
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT


# ═══════════════════════════════════════════════════════════════
# BRAND COLORS
# ═══════════════════════════════════════════════════════════════
RED = colors.HexColor("#B91C1C")
RED_DARK = colors.HexColor("#991B1B")
G50 = colors.HexColor("#F9FAFB")
G100 = colors.HexColor("#F3F4F6")
G200 = colors.HexColor("#E5E7EB")
G300 = colors.HexColor("#D1D5DB")
G400 = colors.HexColor("#9CA3AF")
G500 = colors.HexColor("#6B7280")
G600 = colors.HexColor("#4B5563")
G700 = colors.HexColor("#374151")
G800 = colors.HexColor("#1F2937")
G900 = colors.HexColor("#111827")
GREEN = colors.HexColor("#16A34A")
WHITE = colors.white
BLACK = colors.black


# ═══════════════════════════════════════════════════════════════
# PRICING DATABASE  (mirrors P object in JS)
# ═══════════════════════════════════════════════════════════════
P = {
    "sales": {
        "base": 12, "crawl": 3, "ssAdd": 2, "sidingAdd": 1.5,
        "steepAdd": 1.75, "stoneW": 24, "stoneO": 26, "stoneLift": 1500,
        "deck": 5, "tg": 5, "awning": 450, "cupola": 250, "bsmtWall": 10,
    },
    "ctr": {
        "fSlab": {"u": 5.5, "o": 6}, "fUp": {"u": 5.5, "o": 6},
        "fAttic": {"u": 4, "o": 4.5}, "fPorch": {"u": 5.5, "o": 6},
        "fRafter": {"u": 6, "o": 6.5}, "fBsmt": {"u": 7.5, "o": 8},
        "bsmtLf": 10, "deckRoof": {"u": 7, "o": 7.5},
        "awnU": 350, "awnO": 450,
        "r612": {"u": 1.3, "o": 1.3}, "r812": {"u": 1.5, "o": 1.5},
        "ss": {"u": 2.5, "o": 2.5}, "ss912": {"u": 2.8, "o": 2.8},
        "shing": {"u": 0.75, "o": 0.75}, "osb": 0.5,
        "mWall": {"u": 1.5, "o": 1.5}, "mCeil": {"u": 1.75, "o": 1.75},
        "bb": {"u": 3, "o": 3}, "lph": {"u": 2, "o": 2},
        "vinyl": {"u": 1.5, "o": 1.5},
        "bw": {"u": 5.5, "o": 5.5}, "sof": {"u": 5.5, "o": 5.5},
        "stone": {"u": 16, "o": 17},
        "dblD": 150, "sglD": 100, "dblW": 100, "sglW": 50,
        "s2s": 75, "s2d": 150, "cup": 125,
        "deckNR": 5.5, "trex": 1, "tgC": 2.25,
    },
    "conc": {
        "types": {
            "4fiber": {1: 5, 2: 5.25, 3: 5.25},
            "6fiber": {1: 6.25, 2: 6.5, 3: 6.5},
            "4mono": {1: 8, 2: 8.5, 3: 9},
            "6mono": {1: 8.5, 2: 9, 3: 9.5},
        },
        "minF": 3500, "minM": 5500,
        "lp": 1750, "bp": 2500,
        "wire": 0.85, "rebar": 1.25, "foam": 9,
    },
    "punch": 2500,
}

BRANCHES = {
    "summertown": {"label": "Summertown Main", "concRate": 8, "miles": 0, "zone": 1},
    "hayden_al":  {"label": "Hayden, AL",      "concRate": 8, "miles": 0, "zone": 1},
    "morristown": {"label": "Morristown",       "concRate": 9, "miles": 1, "zone": 2},
    "hopkinsville":{"label":"Hopkinsville",     "concRate": 9, "miles": 1, "zone": 3},
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def fmt(n):
    return f"${round(n):,}"

def f2(n):
    return f"${n:,.2f}"

def pn(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ═══════════════════════════════════════════════════════════════
# COMPUTED METRICS  (mirror JS helper functions)
# ═══════════════════════════════════════════════════════════════
def liv_sf(slab):
    return sum(s["sf"] for s in slab if s["n"] in ("1st Floor Living Area", "2nd Floor Area", "Bonus Room"))

def gar_sf(slab):
    return sum(s["sf"] for s in slab if s["n"] == "Garage Area")

def por_sf(slab):
    return sum(s["sf"] for s in slab if s["n"] in ("Front Porch Area", "Back Porch Area"))

def car_sf(slab):
    return sum(s["sf"] for s in slab if s["n"] == "Carport Area")

def tot_slab(slab):
    return sum(s["sf"] for s in slab)

def bon_sf(slab):
    return sum(s["sf"] for s in slab if s["n"] in ("Bonus Room", "2nd Floor Area"))

def tg_sf(slab):
    return sum(s["sf"] for s in slab if s.get("tg"))

def base_sf(slab):
    return liv_sf(slab) + gar_sf(slab) + por_sf(slab)

def tot_roof(roof):
    return sum(r["sf"] for r in roof)

def rf_metal_std(roof):
    return sum(r["sf"] for r in roof if r["type"] == "metal" and not r.get("steep"))

def rf_metal_steep(roof):
    return sum(r["sf"] for r in roof if r["type"] == "metal" and r.get("steep"))

def rf_ss_std(roof):
    return sum(r["sf"] for r in roof if r["type"] == "ss" and not r.get("steep"))

def rf_ss_steep(roof):
    return sum(r["sf"] for r in roof if r["type"] == "ss" and r.get("steep"))

def rf_ss_sf(roof):
    return sum(r["sf"] for r in roof if r["type"] == "ss")

def rf_sh_all(roof):
    return sum(r["sf"] for r in roof if r["type"] == "shingles")

def rf_steep(roof):
    return sum(r["sf"] for r in roof if r.get("steep"))

def sof_lf(slab):
    return round((liv_sf(slab) + gar_sf(slab)) * 0.11)

def c_sf(slab, crawl_sf):
    return crawl_sf if crawl_sf else liv_sf(slab)

def gross_wall_sf(wall_tuff, dbl_d, sgl_d, dbl_w, sgl_w, s2s, s2d):
    """Net ext wall + estimated opening areas (matches JS grossWallSF)."""
    return wall_tuff + (dbl_d * 45) + (sgl_d * 22) + (dbl_w * 33) + (sgl_w * 17) + (s2s * 17) + (s2d * 33)


# ═══════════════════════════════════════════════════════════════
# LINE ITEM BUILDERS  (mirrors buildCtrItems, buildSalesItems, buildConcItems)
# ═══════════════════════════════════════════════════════════════

def build_ctr_items(state):
    """
    Returns list of dicts: {key, section, label, qty, rate, cost, unit}
    Mirrors buildCtrItems() in JS.
    """
    cr = P["ctr"]
    b = "o" if state.get("miles", 0) >= 1 else "u"
    slab = state.get("slab", [])
    roof = state.get("roof", [])
    ctr_ov = state.get("ctrOv", {})
    wall_tuff = state.get("wallTuff", 0)
    wall_stone = state.get("wallStone", 0)
    wall_type = state.get("wallType", "Metal")
    stone_upg = state.get("stoneUpg", 0)
    dbl_d = state.get("dblD", 0)
    sgl_d = state.get("sglD", 0)
    dbl_w = state.get("dblW", 0)
    sgl_w = state.get("sglW", 0)
    s2s = state.get("s2s", 0)
    s2d = state.get("s2d", 0)
    awn_qty = state.get("awnQty", 0)
    cup_qty = state.get("cupQty", 0)
    found_type = state.get("foundType", "concrete")
    crawl_sf = state.get("crawlSF", 0)
    sheath = state.get("sheath", 0)
    g26 = state.get("g26", 0)
    custom_charges = state.get("customCharges", [])

    items = []

    def add(key, sec, lbl, qty, rate, unit):
        q = ctr_ov[key] if key in ctr_ov else qty
        items.append({
            "key": key, "section": sec, "label": lbl,
            "qty": q, "dflt": qty, "rate": rate,
            "cost": q * rate, "unit": unit,
        })

    slb = liv_sf(slab) + gar_sf(slab)
    bon = bon_sf(slab)

    # FRAMING
    add("fSlab",   "Framing", "Framing per sq ft of usable floor space on a slab", slb, cr["fSlab"][b], "SF")
    add("rafter",  "Framing", "Rafter roof framing per sq ft", 0, cr["fRafter"][b], "SF")
    add("fUp",     "Framing", "Framing per sq ft upstairs", bon, cr["fUp"][b], "SF")
    add("fBsmt",   "Framing", "Framing over a basement or crawlspace",
        c_sf(slab, crawl_sf) if found_type == "crawl" else 0, cr["fBsmt"][b], "SF")
    add("bsmtLf",  "Framing", "Framing rooms in basement (linear ft)", 0, cr["bsmtLf"], "LF")
    add("fAttic",  "Framing", "Open attic (no framed stairs) & carport framing", car_sf(slab), cr["fAttic"][b], "SF")
    add("fPorch",  "Framing", "Timber framed porch roof system on a slab", por_sf(slab), cr["fPorch"][b], "SF")
    add("deckRoof","Framing", "Wood framed deck incl. railing, staircase & roof system", 0, cr["deckRoof"][b], "SF")
    add("awnU",    "Framing", "Timber awnings built on site under 8' (qty)", 0, cr["awnU"], "ea")
    add("awnO",    "Framing", "Timber awnings built on site over 8' (qty)", awn_qty, cr["awnO"], "ea")

    # SHEATHING
    add("osb", "Sheathing", "OSB/Plywood sheathing on roof (sq ft)",
        base_sf(slab) if sheath else 0, cr["osb"], "SF")

    # ROOF
    std_rate = 1.5 if g26 else cr["r612"][b]
    add("rStd",    "Roof", "Roof metal 7/12 or under (sq ft)",  rf_metal_std(roof),  std_rate, "SF")
    add("rSteep",  "Roof", "Roof metal 8/12 or greater (sq ft)", rf_metal_steep(roof), cr["r812"][b], "SF")
    add("ssStd",   "Roof", "Standing seam 7/12 or under (sq ft)", rf_ss_std(roof),  cr["ss"][b], "SF")
    add("ssSteep", "Roof", "Standing seam 8/12 or greater (sq ft)", rf_ss_steep(roof), cr["ss912"][b], "SF")
    add("shingSF", "Roof", "Shingles (sq ft)", rf_sh_all(roof), cr["shing"][b], "SF")

    # WALLS
    gw = gross_wall_sf(wall_tuff, dbl_d, sgl_d, dbl_w, sgl_w, s2s, s2d)
    add("mWall",  "Walls", "Metal installation walls (sq ft of coverage)", gw, cr["mWall"][b], "SF")
    add("mCeil",  "Walls", "Metal installation ceiling (sq ft of coverage)", gar_sf(slab), cr["mCeil"][b], "SF")
    add("bb",     "Walls", "Board & Batten (per sq ft)",
        wall_tuff if wall_type == "Board and Batten" else 0, cr["bb"][b], "SF")
    add("lph",    "Walls", "LP & Hardie siding (per sq ft)",
        wall_tuff if wall_type in ("LP", "Hardie Siding") else 0, cr["lph"][b], "SF")
    add("vinyl",  "Walls", "Vinyl siding (per sq ft)",
        wall_tuff if wall_type == "Vinyl Siding" else 0, cr["vinyl"][b], "SF")
    add("bw",     "Walls", "Beam wrap (per linear ft)", 0, cr["bw"][b], "LF")
    add("sof",    "Walls", "Soffit (per linear ft)", sof_lf(slab), cr["sof"][b], "LF")

    # STONE
    add("stoneLbr", "Stone", "Stone labor (per sq ft of coverage)",
        wall_stone if stone_upg else 0, cr["stone"][b], "SF")

    # DOORS & WINDOWS
    add("dblD", "Doors & Windows", "Double door (qty)",   dbl_d, cr["dblD"], "ea")
    add("sglD", "Doors & Windows", "Single door (qty)",   sgl_d, cr["sglD"], "ea")
    add("dblW", "Doors & Windows", "Double window (qty)", dbl_w, cr["dblW"], "ea")
    add("sglW", "Doors & Windows", "Single window (qty)", sgl_w, cr["sglW"], "ea")
    add("s2s",  "Doors & Windows", "Second-story window over 12' from ground (single)", s2s, cr["s2s"], "ea")
    add("s2d",  "Doors & Windows", "Second-story window over 12' from ground (double)", s2d, cr["s2d"], "ea")

    # OTHER
    add("cup",    "Other", "Cupola installation (qty)",    cup_qty, cr["cup"], "ea")
    add("tgC",    "Other", "T&G porch ceilings (sq ft)",  tg_sf(slab), cr["tgC"], "SF")
    add("deckNR", "Other", "Wood decks without roof (sq ft)", 0, cr["deckNR"], "SF")
    add("trex",   "Other", "TREX decking (sq ft)",         0, cr["trex"], "SF")

    # CUSTOM CHARGES
    for ci, cc in enumerate(custom_charges):
        if cc.get("qty", 0) > 0 and cc.get("rate", 0) > 0:
            add(f"custom_{ci}", "Custom", cc.get("desc") or "Custom charge",
                cc["qty"], cc["rate"], cc.get("unit") or "SF")

    return items


def build_conc_items(state):
    """Returns list of {label, qty, rate, cost, unit}. Mirrors buildConcItems()."""
    c = state.get("conc", {})
    db = P["conc"]
    items = []

    def add(lbl, qty, rate, unit):
        if qty > 0 and rate > 0:
            items.append({"label": lbl, "qty": qty, "rate": rate, "cost": qty * rate, "unit": unit})

    sqft = c.get("sqft", 0)
    ctype = c.get("type", "")
    zone = c.get("zone", 1)
    if sqft > 0 and ctype and ctype in db["types"]:
        r = db["types"][ctype][zone]
        sub = sqft * r
        mono = ctype in ("4mono", "6mono")
        mn = db["minM"] if mono else db["minF"]
        fin = max(sub, mn)
        add(f"Concrete ({ctype}, Zone {zone})", sqft, r, "SF")
        if fin > sub:
            add("Minimum adjustment", 1, fin - sub, "ea")

    if c.get("lp"):
        add("Line pump", 1, db["lp"], "ea")
    if c.get("bp"):
        add("Boom pump", 1, db["bp"], "ea")
    if sqft > 0 and c.get("wire"):
        add("Wire", sqft, db["wire"], "SF")
    if sqft > 0 and c.get("rebar"):
        add("Rebar", sqft, db["rebar"], "SF")
    if c.get("foam", 0) > 0:
        add('2" foam perimeter', c["foam"], db["foam"], "LF")

    for cc in state.get("concCustomCharges", []):
        if cc.get("qty", 0) > 0 and cc.get("rate", 0) > 0:
            add(cc.get("desc") or "Concrete custom", cc["qty"], cc["rate"], cc.get("unit") or "SF")

    return items


def build_sales_items(state):
    """Returns list of {label, qty, rate, cost, unit}. Mirrors buildSalesItems()."""
    s = P["sales"]
    slab = state.get("slab", [])
    roof = state.get("roof", [])
    wall_tuff = state.get("wallTuff", 0)
    wall_stone = state.get("wallStone", 0)
    wall_type = state.get("wallType", "Metal")
    stone_upg = state.get("stoneUpg", 0)
    chim_qty = state.get("chimQty", 0)
    awn_qty = state.get("awnQty", 0)
    cup_qty = state.get("cupQty", 0)
    found_type = state.get("foundType", "concrete")
    crawl_sf = state.get("crawlSF", 0)
    miles = state.get("miles", 0)
    punch_amt = state.get("punchAmt", P["punch"])
    custom_charges = state.get("customCharges", [])

    items = []

    def add(lbl, qty, rate, unit):
        if qty > 0 and rate > 0:
            items.append({"label": lbl, "qty": qty, "rate": rate, "cost": qty * rate, "unit": unit})

    add(f"Base labor ({round(base_sf(slab)):,} SF)", base_sf(slab), s["base"], "SF")
    if found_type == "crawl":
        add("Framing over crawl/basement", c_sf(slab, crawl_sf), s["crawl"], "SF")
    if rf_steep(roof) > 0:
        add("Roof 9/12+ pitch add", rf_steep(roof), s["steepAdd"], "SF")
    if rf_ss_sf(roof) > 0:
        add("Standing seam roof add", rf_ss_sf(roof), s["ssAdd"], "SF")
    if wall_type != "Metal":
        add(f"Siding upgrade ({wall_type})", wall_tuff, s["sidingAdd"], "SF")
    if stone_upg and wall_stone > 0:
        add("Stone area", wall_stone, s["stoneO"] if miles >= 1 else s["stoneW"], "SF")
    if chim_qty > 0:
        add("Stone chimney/roofline lifts", chim_qty, s["stoneLift"], "ea")
    if tg_sf(slab) > 0:
        add("T&G porch ceilings", tg_sf(slab), s["tg"], "SF")
    if awn_qty > 0:
        add("Timber framed awnings", awn_qty, s["awning"], "ea")
    if cup_qty > 0:
        add("Cupola installation", cup_qty, s["cupola"], "ea")

    # Concrete items
    conc_items = build_conc_items(state)
    items.extend(conc_items)

    # Punch
    pa = max(P["punch"], punch_amt or 0)
    add("Punch", 1, pa, "ea")

    for cc in custom_charges:
        if cc.get("qty", 0) > 0 and cc.get("rate", 0) > 0:
            add(cc.get("desc") or "Custom charge", cc["qty"], cc["rate"], cc.get("unit") or "SF")

    return items


def sum_items(items):
    return sum(i["cost"] for i in items)


def items_by_section(items, sec):
    return [i for i in items if i["section"] == sec]


def get_sections(items):
    seen = set()
    out = []
    for i in items:
        if i["section"] not in seen:
            seen.add(i["section"])
            out.append(i["section"])
    return out


def shell_total(state, sales_items, conc_items):
    cust_labor = sum_items(sales_items) - sum_items(conc_items)
    conc_t = sum_items(conc_items)
    return (state.get("custInfo", {}).get("p10") or 0) + cust_labor + conc_t


def gen_scope(state):
    cust_name = (state.get("custInfo") or {}).get("name") or "Customer"
    model = state.get("model") or "Custom"
    slab = state.get("slab", [])
    roof = state.get("roof", [])
    found_type = state.get("foundType", "concrete")
    wall_type = state.get("wallType", "Metal")
    wall_stone = state.get("wallStone", 0)
    stone_upg = state.get("stoneUpg", 0)
    sheath = state.get("sheath", 0)
    tg = tg_sf(slab)
    awn_qty = state.get("awnQty", 0)
    cup_qty = state.get("cupQty", 0)
    chim_qty = state.get("chimQty", 0)
    conc = state.get("conc", {})
    ctype = conc.get("type", "")

    scope = f"{cust_name} \u2014 {model}.\n\n"
    if found_type == "crawl":
        scope += f"{model} on crawlspace/basement foundation."
    else:
        scope += f"{model} turnkey with exterior complete on concrete slab."

    if ctype:
        if ctype in ("4mono", "6mono"):
            scope += " Concrete to be monolithic slab, main building to get footers. All footers to get 2 runs of rebar throughout."
        thick = "4" if ctype.startswith("4") else "6"
        scope += f" Slab is {thick}\u2033 thick with fiber, with a plastic vapor barrier."

    scope += ' Framing Specs: All studs are 2x6 exterior and 2x4 interior spaced 16" O/C.'
    if sheath:
        scope += " Stud framed house sides to get 7/16 OSB sides sheeting and house wrap moisture barrier. 5/8 plywood roof."

    roof_desc = []
    metal_sf = rf_metal_std(roof) + rf_metal_steep(roof)
    if metal_sf > 0:
        roof_desc.append("standard metal roof")
    if rf_ss_sf(roof) > 0:
        names = [r["n"] for r in roof if r["type"] == "ss"]
        roof_desc.append("standing seam metal on " + ", ".join(names))
    if rf_sh_all(roof) > 0:
        names = [r["n"] for r in roof if r["type"] == "shingles"]
        roof_desc.append("shingles on " + ", ".join(names))
    if roof_desc:
        scope += " Roof: " + ", ".join(roof_desc) + "."

    if wall_type == "Metal":
        scope += " Exterior walls finished with standard Tuff Rib metal siding."
    else:
        scope += f" Exterior walls finished with {wall_type}."

    if found_type == "crawl":
        scope += " Framing over crawlspace/basement included."
    if stone_upg and wall_stone > 0:
        scope += " Stone wainscotting on exterior walls."
    if tg > 0:
        scope += " Tongue and groove porch ceilings."
    if awn_qty > 0:
        scope += f" {awn_qty} timber framed awning{'s' if awn_qty > 1 else ''}."
    if cup_qty > 0:
        scope += f" {cup_qty} cupola{'s' if cup_qty > 1 else ''}."
    if chim_qty > 0:
        scope += f" {chim_qty} stone chimney/roofline lift{'s' if chim_qty > 1 else ''}."

    scope += "\n\nCustomer is responsible for level site and gravel for concrete."
    return scope


# ═══════════════════════════════════════════════════════════════
# REPORTLAB STYLE HELPERS
# ═══════════════════════════════════════════════════════════════

def get_styles():
    base = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle("brand", fontSize=14, fontName="Helvetica-Bold",
                                textColor=RED, spaceAfter=2),
        "brand_sub": ParagraphStyle("brand_sub", fontSize=9, fontName="Helvetica",
                                    textColor=G500, spaceAfter=0),
        "meta": ParagraphStyle("meta", fontSize=8, fontName="Helvetica",
                               textColor=G600, leading=12),
        "title": ParagraphStyle("title", fontSize=11, fontName="Helvetica-Bold",
                                textColor=G800, spaceBefore=10, spaceAfter=6,
                                textTransform="uppercase", letterSpacing=0.5),
        "footer": ParagraphStyle("footer", fontSize=8, fontName="Helvetica",
                                 textColor=G400, alignment=TA_CENTER, spaceBefore=12),
        "total_label": ParagraphStyle("total_label", fontSize=13, fontName="Helvetica-Bold",
                                      textColor=G800),
        "total_value": ParagraphStyle("total_value", fontSize=13, fontName="Helvetica-Bold",
                                      textColor=RED, alignment=TA_RIGHT),
        "scope": ParagraphStyle("scope", fontSize=9, fontName="Helvetica",
                                textColor=G700, leading=14, alignment=TA_CENTER),
        "section_header": ParagraphStyle("section_hdr", fontSize=8, fontName="Helvetica-Bold",
                                         textColor=G500, textTransform="uppercase",
                                         letterSpacing=0.5),
    }
    return styles


def table_style_base():
    return TableStyle([
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  G500),
        ("BACKGROUND",  (0, 0), (-1, 0),  G50),
        ("BOTTOMPADDING",(0,0), (-1, 0),  4),
        ("TOPPADDING",  (0, 0), (-1, 0),  4),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 1), (-1, -1), G700),
        ("BOTTOMPADDING",(0,1), (-1,-1),  3),
        ("TOPPADDING",  (0, 1), (-1, -1), 3),
        ("LINEBELOW",   (0, 0), (-1, 0),  1, G300),
        ("LINEBELOW",   (0, 1), (-1, -2), 0.5, G100),
        ("GRID",        (0, 0), (-1, -1), 0, colors.transparent),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
    ])


def build_header_table(brand_line, subtitle, info, styles):
    """Build the two-column header: brand left, meta right."""
    meta_lines = []
    if info.get("name"):
        meta_lines.append(f"<b>Customer:</b> {info['name']}")
    if info.get("addr"):
        meta_lines.append(f"<b>Address:</b> {info['addr']}")
    if info.get("order"):
        meta_lines.append(f"<b>Order #:</b> {info['order']}")
    if info.get("rep"):
        meta_lines.append(f"<b>Sales Rep:</b> {info['rep']}")
    if info.get("model"):
        meta_line = info["model"]
        if info.get("miles"):
            meta_line += f" \u2022 {info['miles']}"
        if info.get("branch_label"):
            meta_line += f" \u2022 {info['branch_label']}"
        meta_lines.append(f"<b>Model:</b> {meta_line}")
    meta_lines.append(f"<b>Date:</b> {date.today().strftime('%B %d, %Y')}")

    left = [
        Paragraph(brand_line, styles["brand"]),
        Paragraph(subtitle, styles["brand_sub"]),
    ]
    right = [Paragraph("<br/>".join(meta_lines), styles["meta"])]

    t = Table([[left, right]], colWidths=[3 * inch, 4.5 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 1, G300),
    ]))
    return t


def build_customer_table(sales_items, styles):
    """Customer line items table."""
    UPGRADE_KEYWORDS = (
        "upgrade", "Standing seam", "Stone", "T&G", "Timber", "Cupola", "pitch add"
    )
    rows = [["Description", "Calculation", "Amount"]]
    for li in sales_items:
        is_upg = any(k.lower() in li["label"].lower() for k in UPGRADE_KEYWORDS)
        label = ("\u2b06 " if is_upg else "") + li["label"]
        calc = f"{round(li['qty']):,} {li['unit']} \u00d7 {f2(li['rate'])}" if li["qty"] != 1 else ""
        rows.append([label, calc, fmt(li["cost"])])

    col_w = [3.5 * inch, 2 * inch, 2 * inch]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = table_style_base()
    for i in range(1, len(rows)):
        ts.add("ALIGN", (1, i), (2, i), "RIGHT")
    ts.add("ALIGN", (1, 0), (2, 0), "RIGHT")
    t.setStyle(ts)
    return t


def build_contractor_section_table(ctr_items, styles):
    """Contractor items grouped by section."""
    sections = get_sections(ctr_items)
    rows = [["Item", "Qty", "Rate", "Amount"]]
    section_row_indices = []

    for sec in sections:
        sec_items = [i for i in ctr_items if i["section"] == sec and i["qty"] > 0]
        sec_total = sum(i["cost"] for i in sec_items)
        if sec_total <= 0:
            continue
        section_row_indices.append(len(rows))
        rows.append([sec.upper(), "", "", ""])  # section header row
        for it in sec_items:
            rows.append([
                it["label"],
                f"{round(it['qty']):,} {it['unit']}",
                f"{f2(it['rate'])}/{it['unit']}",
                fmt(it["cost"]),
            ])
        rows.append([f"{sec} Subtotal", "", "", fmt(sec_total)])

    col_w = [3.2 * inch, 1 * inch, 1.3 * inch, 2 * inch]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = table_style_base()

    # Style section header rows
    for idx in section_row_indices:
        ts.add("BACKGROUND", (0, idx), (-1, idx), G50)
        ts.add("FONTNAME",   (0, idx), (-1, idx), "Helvetica-Bold")
        ts.add("FONTSIZE",   (0, idx), (-1, idx), 8)
        ts.add("TEXTCOLOR",  (0, idx), (-1, idx), G600)
        ts.add("LINEABOVE",  (0, idx), (-1, idx), 1, G300)
        ts.add("SPAN",       (0, idx), (-1, idx))

    # Style subtotal rows (last row of each section = section_row + n_items + 1)
    for ri, row in enumerate(rows):
        if ri > 0 and "Subtotal" in str(row[0]):
            ts.add("FONTNAME", (0, ri), (-1, ri), "Helvetica-Bold")
            ts.add("LINEABOVE", (0, ri), (-1, ri), 1, G300)

    # Right-align numeric columns
    for i in range(1, len(rows)):
        ts.add("ALIGN", (1, i), (-1, i), "RIGHT")
    ts.add("ALIGN", (1, 0), (-1, 0), "RIGHT")
    t.setStyle(ts)
    return t


def build_draw_schedule_table(shell_t, p10, conc_t, cust_labor, styles):
    """Draw schedule table — matches HTML printFullContractPDF draw schedule."""
    deposit = 2500
    draw1 = p10 - deposit if p10 > 0 else 0

    # (description_lines, amount, is_sub_row, is_highlight)
    ENTRIES = [
        (
            ['Contract \u201cGood Faith\u201d Deposit (non-refundable, paid at signing)'],
            fmt(deposit), False, False,
        ),
        (
            ['1st Home Draw at Loan Closing',
             'Total Shell Material Amount minus Prepayment'],
            fmt(draw1) if p10 > 0 else "\u2014", False, p10 > 0,
        ),
        (
            ['    1st Draw Shop/Detached Garage Portion (if applicable)',
             '    Total Shop/Detached Garage Deposit (Full Material Amount of shop/detached garage)'],
            "$0.00", True, False,
        ),
        (
            ['2nd Home Draw Upon Concrete Completion',
             'Includes remaining material, site prep allowance (if applicable), and concrete'],
            fmt(conc_t) if conc_t > 0 else "\u2014", False, conc_t > 0,
        ),
        (
            ['    2nd Draw Shop/Detached Garage Portion (if applicable)',
             '    Total Concrete and Labor Cost at Completion of Shop/Detached Garage'],
            "$0.00", True, False,
        ),
        (
            ['3rd Home Draw Upon Framing Completion',
             'Includes exterior labor'],
            fmt(cust_labor), False, True,
        ),
        (
            ['4th Home Draw',
             '20% of total contract upon completion of mechanical rough-in/electric/plumbing/HVAC'],
            "\u2014", False, False,
        ),
        (
            ['5th Home Draw',
             '20% of total contract upon completion of drywall/cabinets/countertops'],
            "\u2014", False, False,
        ),
        (
            ['6th Home Draw',
             'Final Punch/Notice of Completion or Certificate of Occupancy if necessary'],
            "\u2014", False, False,
        ),
    ]

    header_style  = ParagraphStyle("dh", fontSize=8, fontName="Helvetica-Bold",
                                   textColor=G800, leading=11)
    sub_style     = ParagraphStyle("ds", fontSize=7, fontName="Helvetica",
                                   textColor=G500, leading=10)
    sub_dim_style = ParagraphStyle("dd", fontSize=7, fontName="Helvetica",
                                   textColor=G400, leading=10)
    amt_red_style = ParagraphStyle("ar", fontSize=8, fontName="Helvetica-Bold",
                                   textColor=RED, alignment=TA_RIGHT)
    amt_dim_style = ParagraphStyle("ad", fontSize=8, fontName="Helvetica",
                                   textColor=G300, alignment=TA_RIGHT)
    amt_std_style = ParagraphStyle("as", fontSize=8, fontName="Helvetica-Bold",
                                   textColor=G700, alignment=TA_RIGHT)

    rows = [["Draw", "Amount"]]
    row_metas = [None]  # track (is_sub, is_highlight) per row

    for lines, amount, is_sub, is_highlight in ENTRIES:
        lbl_parts = []
        hs = sub_dim_style if is_sub else header_style
        ss = sub_dim_style if is_sub else sub_style
        for idx, line in enumerate(lines):
            lbl_parts.append(Paragraph(line, hs if idx == 0 else ss))
        if is_highlight and amount != "\u2014":
            amt_p = Paragraph(amount, amt_red_style)
        elif amount in ("\u2014", "$0.00"):
            amt_p = Paragraph(amount, amt_dim_style)
        else:
            amt_p = Paragraph(amount, amt_std_style)
        rows.append([lbl_parts, amt_p])
        row_metas.append((is_sub, is_highlight))

    col_w = [5.5 * inch, 2 * inch]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = table_style_base()
    # Sub-rows get dimmed background
    for i, meta in enumerate(row_metas):
        if meta is None:
            continue
        is_sub, is_highlight = meta
        if is_sub:
            ts.add("BACKGROUND", (0, i), (-1, i), G50)
        elif is_highlight:
            ts.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F0FDF4"))
    ts.add("ALIGN", (1, 0), (1, 0), "RIGHT")
    t.setStyle(ts)
    return t


def build_margin_summary(cust_ext_labor, ctr_total, styles):
    """Margin summary rows below contractor table."""
    profit = cust_ext_labor - ctr_total
    profit_color = GREEN if profit >= 0 else colors.HexColor("#DC2626")
    rows = [
        ["Customer Ext. Labor:", fmt(cust_ext_labor)],
        ["Contractor Total:", fmt(ctr_total)],
        ["Estimated Profit:", fmt(profit)],
    ]
    col_w = [5 * inch, 2.5 * inch]
    t = Table(rows, colWidths=col_w)
    ts = TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  G600),
        ("TEXTCOLOR",   (1, 0), (1, 0),   RED),
        ("FONTNAME",    (1, 0), (1, 0),   "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 1), (-1, 1),  G700),
        ("FONTNAME",    (0, 2), (-1, 2),  "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 2), (0, 2),   G800),
        ("TEXTCOLOR",   (1, 2), (1, 2),   profit_color),
        ("ALIGN",       (1, 0), (1, -1),  "RIGHT"),
        ("LINEABOVE",   (0, 2), (-1, 2),  1, G300),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",(0, 0), (-1, -1), 0),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1),  4),
    ])
    t.setStyle(ts)
    return t


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def generate_pdf(state: dict, pdf_type: str = "full") -> bytes:
    """
    Generate a PDF and return its bytes.

    Parameters
    ----------
    state : dict
        All UI state fields. Expected keys mirror the HTML JS state:
          model, miles, sheath, g26, foundType, bsmtFrame, stories,
          slab (list of {n, sf, tg}), roof (list of {n, type, steep, sf}),
          wallTuff, wallRock, wallStone, wallType, stoneUpg, wainscotUpg,
          dblD, sglD, dblW, sglW, s2s, s2d, deckShown, win12,
          awnQty, cupQty, chimQty, crawlSF, punchAmt,
          customCharges (list), ctrOv (dict),
          conc ({sqft, type, zone, lp, bp, wire, rebar, foam}),
          concCustomCharges (list),
          custInfo ({name, addr, order, rep, p10}),
          branch,
          scopeText (optional override), scopeWindows, scopeDoors
    pdf_type : "customer" | "contractor" | "full"

    Returns
    -------
    bytes : raw PDF bytes
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.6 * inch,
        title="STMC Exterior Labor Estimate",
        author="Summertown Metals Contracting",
    )

    styles = get_styles()
    story = []

    # Build shared computed data
    sales_items = build_sales_items(state)
    ctr_items = build_ctr_items(state)
    conc_items = build_conc_items(state)
    s_total = sum_items(sales_items)
    ctr_total = sum_items([i for i in ctr_items if i["qty"] > 0])
    conc_total = sum_items(conc_items)
    cust_labor = s_total - conc_total
    shell_t = shell_total(state, sales_items, conc_items)

    cust_info = state.get("custInfo") or {}
    model = state.get("model") or ""
    branch_key = state.get("branch", "summertown")
    branch_info = BRANCHES.get(branch_key, BRANCHES["summertown"])
    miles_label = "Over 100 mi" if state.get("miles", 0) >= 1 else "Under 100 mi"
    p10 = pn(cust_info.get("p10", 0))
    punch_t = max(P["punch"], state.get("punchAmt") or 0)
    slab = state.get("slab", [])
    liv = liv_sf(slab)
    shell_psf = shell_t / liv if liv > 0 else 0

    info = {
        "name": cust_info.get("name", ""),
        "addr": cust_info.get("addr", ""),
        "order": cust_info.get("order", ""),
        "rep": cust_info.get("rep", ""),
        "model": model,
        "miles": miles_label,
        "branch_label": branch_info["label"],
    }

    def spacer(h=8):
        story.append(Spacer(1, h))

    def divider():
        story.append(HRFlowable(width="100%", thickness=1, color=G200, spaceAfter=6))

    def total_row(label, value, value_color=RED):
        t = Table([[label, value]], colWidths=[5 * inch, 2.5 * inch])
        t.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 11),
            ("TEXTCOLOR",   (0, 0), (0, 0),  G800),
            ("TEXTCOLOR",   (1, 0), (1, 0),  value_color),
            ("ALIGN",       (1, 0), (1, 0),  "RIGHT"),
            ("LINEABOVE",   (0, 0), (-1, 0), 2, G800),
            ("TOPPADDING",  (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",(0, 0), (-1, -1), 0),
        ]))
        story.append(t)

    # ───────────────────────────────────────────────────────────
    # CUSTOMER CONTRACT PAGE
    # ───────────────────────────────────────────────────────────
    if pdf_type in ("customer", "full"):
        story.append(build_header_table(
            "Summertown Metals Contracting",
            "Exterior Labor Estimate" if pdf_type == "customer" else "Exterior Shell Contract",
            info, styles))
        spacer(10)

        if pdf_type == "full":
            # Contract Summary table
            story.append(Paragraph("Contract Summary", styles["title"]))
            sum_rows = [
                ["P10 Material Total",        fmt(p10)],
                ["Customer Labor Cost",        fmt(cust_labor)],
                ["Concrete Total",             fmt(conc_total)],
                ["Punch",                      fmt(punch_t)],
                ["Total Exterior Shell Package", fmt(shell_t)],
                ["Shell Price per SQFT (Living)", f2(shell_psf) + "/SF"],
            ]
            t = Table(sum_rows, colWidths=[5 * inch, 2.5 * inch])
            ts = table_style_base()
            ts.add("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold")
            ts.add("TEXTCOLOR", (1, 4), (1, 4), RED)
            ts.add("FONTSIZE",  (0, 4), (-1, 4), 9)
            ts.add("LINEABOVE", (0, 4), (-1, 4), 2, G300)
            for i in range(len(sum_rows)):
                ts.add("ALIGN", (1, i), (1, i), "RIGHT")
            t.setStyle(ts)
            story.append(t)
            spacer(12)
            story.append(Paragraph("Customer Line Items", styles["title"]))

        story.append(build_customer_table(sales_items, styles))
        spacer(4)
        total_row(
            "Customer Total:" if pdf_type == "customer" else "Labor and Concrete Total:",
            fmt(s_total)
        )
        divider()
        story.append(Paragraph(
            f"Summertown Metals Contracting \u2022 {date.today().strftime('%B %d, %Y')} "
            "\u2022 This estimate is valid for 30 days.",
            styles["footer"]
        ))

    # ───────────────────────────────────────────────────────────
    # CONTRACTOR LABOR PAGE
    # ───────────────────────────────────────────────────────────
    if pdf_type in ("contractor", "full"):
        if pdf_type == "full":
            story.append(PageBreak())
        story.append(build_header_table(
            "Summertown Metals Contracting",
            "Contractor Labor Budget",
            info, styles))
        spacer(10)
        story.append(Paragraph("Contractor Labor Breakdown", styles["title"]))
        story.append(build_contractor_section_table(ctr_items, styles))
        spacer(4)
        total_row("Contractor Total:", fmt(ctr_total))
        spacer(8)

        # Margin summary
        story.append(build_margin_summary(cust_labor, ctr_total, styles))
        divider()
        story.append(Paragraph(
            f"Summertown Metals Contracting \u2022 Contractor Labor Budget \u2022 "
            f"{date.today().strftime('%B %d, %Y')}",
            styles["footer"]
        ))

    # ───────────────────────────────────────────────────────────
    # DRAW SCHEDULE + SCOPE OF WORK PAGE (full only)
    # ───────────────────────────────────────────────────────────
    if pdf_type == "full":
        story.append(PageBreak())
        story.append(build_header_table(
            "Summertown Metals Contracting",
            "Draw Schedule & Scope of Work",
            info, styles))
        spacer(10)
        story.append(Paragraph(f"Draw Schedule \u2014 {fmt(shell_t)}", styles["title"]))
        story.append(build_draw_schedule_table(shell_t, p10, conc_total, cust_labor, styles))
        spacer(4)
        story.append(Paragraph(
            "<b>Note:</b> Progress in construction shall not proceed to the next step "
            "until the draw is received on the completed work up to that point.",
            ParagraphStyle("note", fontSize=8, textColor=G600, alignment=TA_CENTER,
                           spaceAfter=10)
        ))
        spacer(10)

        # Scope of Work
        story.append(Paragraph("Scope of Work", styles["title"]))
        scope = state.get("scopeText") or gen_scope(state)
        story.append(Paragraph(scope.replace("\n", "<br/>"), styles["scope"]))
        spacer(8)

        # Windows / Doors
        scope_windows = state.get("scopeWindows", "")
        scope_doors = state.get("scopeDoors", "")
        if scope_windows or scope_doors:
            story.append(Paragraph("Materials", styles["title"]))
            if scope_windows:
                story.append(Paragraph("<b>WINDOWS:</b>", styles["scope"]))
                story.append(Paragraph(scope_windows.replace("\n", "<br/>"), styles["scope"]))
                spacer(4)
            if scope_doors:
                story.append(Paragraph("<b>DOORS:</b>", styles["scope"]))
                story.append(Paragraph(scope_doors.replace("\n", "<br/>"), styles["scope"]))

        divider()
        story.append(Paragraph(
            f"Summertown Metals Contracting \u2022 Exterior Shell Contract \u2022 "
            f"{date.today().strftime('%B %d, %Y')} \u2022 Valid for 30 days.",
            styles["footer"]
        ))

    doc.build(story)
    return buf.getvalue()
