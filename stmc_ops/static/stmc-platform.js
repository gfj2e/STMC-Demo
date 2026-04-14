// STMC Operations Demo - core data/state/utilities.
// UI rendering functions live in stmc-platform-templates.js.

function model(s, mft, mt, lb, cn, ts, ta) {
  return {
    s: s,
    mft: mft,
    mt: mt,
    lb: lb,
    cn: cn,
    ts: ts,
    ta: ta
  };
}

function region(nm, lm, cm, tp) {
  return {
    nm: nm,
    lm: lm,
    cm: cm,
    tp: tp
  };
}

function rate(k, r, u, d, l, g, c) {
  return {
    k: k,
    r: r,
    u: u,
    d: d,
    l: l,
    g: g,
    c: c
  };
}

function draw(n, l, a, s, t) {
  return {
    n: n,
    l: l,
    a: a,
    s: s,
    t: t || ""
  };
}

var MD = {
  "Brookside": model(1200, 0.15, 36950, 20528, 11712, 87.5, 105000),
  "Bluewater": model(1232, 0.15, 43775, 19600, 10528, 87.5, 107800),
  "Timber Crest": model(1284, 0.15, 63325, 28700, 13440, 87.5, 112350),
  "Willow Creek": model(1428, 0.15, 52130, 25200, 15200, 87.5, 124950),
  "Buffalo Run": model(1464, 0.15, 81750, 32000, 17912, 100, 146400),
  "East Fork Deluxe": model(1560, 0.15, 75550, 33200, 20500, 87.5, 136500),
  "The Berkley": model(1560, 0.15, 72000, 49500, 19200, 95, 148200),
  "Piney Creek": model(1672, 0.15, 79550, 33260, 23000, 90, 150480),
  "Huntley": model(1680, 0.15, 59500, 27000, 17024, 90, 151200),
  "Huntley 2.0": model(1680, 0.15, 63075, 30724, 18816, 90, 151200),
  "Johnson": model(1710, 0.15, 74000, 44500, 23000, 90, 153900),
  "Cajun": model(1800, 0.15, 71150, 43315, 28080, 90, 162000),
  "Arrowhead Lodge": model(1827, 0.15, 156100, 63500, 32056, 110, 200970),
  "Riverview Cottage": model(1863, 0.15, 71100, 31500, 14664, 90, 167670),
  "Woodside Special": model(1920, 0.15, 92000, 44000, 23000, 90, 172800),
  "Creekside Special": model(1920, 0.15, 87050, 41380, 25920, 90, 172800),
  "Northview Lodge": model(1920, 0.15, 87350, 37500, 23040, 90, 172800),
  "Cottonwood Bend": model(1962, 0.15, 110500, 44500, 26700, 95, 186390),
  "Whispering Pines": model(2000, 0.20, 79000, 44800, 28480, 90, 180000),
  "Martin Lodge": model(2016, 0.20, 94050, 49500, 31400, 105, 211680),
  "Mini Pettus": model(2046, 0.20, 100750, 48700, 29104, 100, 204600),
  "Meadows End": model(2203, 0.20, 99750, 46120, 28160, 100, 220300),
  "Southern Monitor": model(2230, 0.20, 103150, 38800, 22400, 95, 211850),
  "Robertson Deluxe": model(2250, 0.20, 113750, 49500, 28560, 100, 225000),
  "Robertson": model(2250, 0.20, 97996, 46300, 28560, 90, 202500),
  "Rocky Top": model(2328, 0.20, 137000, 55060, 30144, 98, 228144),
  "Thompson": model(2400, 0.20, 109000, 50800, 31500, 95, 228000),
  "Fox Run": model(2400, 0.20, 203500, 83000, 51000, 115, 276000),
  "Ridgecrest": model(2540, 0.22, 138150, 69200, 32600, 94, 238760),
  "Pettus": model(2688, 0.22, 124500, 59847, 38208, 92, 247296),
  "Daugherty": model(2694, 0.22, 184250, 83500, 46288, 102, 274788),
  "Maple Grove": model(3012, 0.22, 126800, 69500, 31000, 100, 301200),
  "Franks Barndominium": model(3016, 0.22, 149000, 77500, 35500, 100, 301600),
  "Cedar Ridge": model(3261, 0.22, 193500, 87000, 44000, 100, 326100),
  "The Hadley": model(3429, 0.22, 158500, 61500, 39464, 100, 342900),
  "Westview Manor": model(3610, 0.22, 193750, 82000, 33000, 98, 353780),
  "Summer Breeze": model(3658, 0.22, 151750, 78500, 38000, 100, 365800)
};

var RG = {
  summertown: region("Summertown / Hayden", 1.0, 1.0, 0),
  east_tn: region("East Tennessee", 1.05, 1.125, 4.5),
  hopkinsville: region("Hopkinsville, KY", 1.05, 1.125, 4.5)
};

var RC = [
  rate("frmS", 6, "/SF", "slabSF", "Framing \u2014 Slab", "Framing", "e"),
  rate("frmP", 6, "/SF", "porchSF", "Framing \u2014 Porch", "Framing", "e"),
  rate("rfM", 1.5, "/SF", "roofSF", "Roof Metal", "Roofing", "e"),
  rate("rfS", 0.5, "/SF", "roofSF", "Roof Sheathing", "Roofing", "e"),
  rate("wlM", 1.5, "/SF", "extWallSF", "Wall Metal", "Siding", "e"),
  rate("sof", 5.5, "/LF", "soffitLF", "Soffit", "Ext Trim", "e"),
  rate("bm", 5.5, "/LF", "beamLF", "Beam Wrap", "Ext Trim", "e"),
  rate("gut", 897, "flat", "flat", "Gutters", "Ext Trim", "e"),
  rate("eDr", 125, "/ea", "extDoors", "Ext Door Install", "D&W", "e"),
  rate("eWn", 65, "/ea", "windows", "Window Install", "D&W", "e"),
  rate("cab", 250, "/LF", "cabLF", "Cabinets", "Cabinets", "i"),
  rate("ct", 43, "/SF", "counterSF", "Countertops", "Cabinets", "i"),
  rate("fM", 1.4, "/SF", "livingSF", "Flooring Material", "Flooring", "i"),
  rate("fL", 1, "/SF", "livingSF", "Flooring Install", "Flooring", "i"),
  rate("dw", 5.39, "/SF", "livingSF", "Drywall", "Drywall", "i"),
  rate("pt", 4, "/SF", "livingSF", "Paint", "Paint", "i"),
  rate("pE", 300, "flat", "flat", "Ext Door Paint", "Paint", "i"),
  rate("tr", 2.5, "/SF", "livingSF", "Trim Install", "Trim", "i"),
  rate("iD", 115, "/door", "intDoors", "Interior Doors", "Trim", "i"),
  rate("el", 7, "/SF", "livingSF", "Electrical", "Electrical", "i"),
  rate("pl", 600, "/fix", "fixtures", "Plumbing", "Plumbing", "i"),
  rate("in", 3.85, "/SF", "livingSF", "Insulation", "Insulation", "i"),
  rate("hv", 4000, "/ton", "hvacTons", "HVAC", "HVAC", "i"),
  rate("pm", 2000, "flat", "flat", "Permits", "General", "i"),
  rate("cl", 875, "flat", "flat", "Cleaning", "General", "i"),
  rate("du", 2500, "flat", "flat", "Dumpster", "General", "i")
];

var UU = {
  derek: { n: "Derek Stoll", i: "DS", r: "sales", rl: "Sales" },
  phillip: { n: "Phillip Olson", i: "PO", r: "pm", rl: "Project Manager" },
  matt: { n: "Matt Stoll", i: "MS", r: "exec", rl: "Executive" }
};

var PJ = [
  {
    id: 1,
    nm: "Theiss Build",
    md: "Huntley 2.0",
    cu: "Julie Theiss",
    ph: "Framing",
    pm: "P. Olson",
    ct: 282127,
    bg: {
      Framing: 25000,
      Roofing: 8200,
      Siding: 4800,
      "Ext Trim": 6100,
      "D&W": 2900,
      Cabinets: 22140,
      Flooring: 4032,
      Drywall: 9055,
      Paint: 6720,
      Trim: 7450,
      Electrical: 11760,
      Plumbing: 7200,
      Insulation: 6468,
      HVAC: 12000,
      General: 5375
    },
    ac: {
      Framing: 23800,
      Roofing: 0,
      Siding: 0,
      "Ext Trim": 0,
      "D&W": 0,
      Cabinets: 0,
      Flooring: 0,
      Drywall: 0,
      Paint: 0,
      Trim: 0,
      Electrical: 0,
      Plumbing: 0,
      Insulation: 0,
      HVAC: 0,
      General: 2875
    },
    dr: [
      draw(0, "Deposit", 2500, "p", "Feb 17"),
      draw(1, "1st \u2014 Materials", 75333, "p", "Mar 2"),
      draw(2, "2nd \u2014 Concrete", 28400, "p", "Mar 18"),
      draw(3, "3rd \u2014 Framing", 25000, "c", ""),
      draw(4, "4th \u2014 Rough-ins", 56425, "x", ""),
      draw(5, "5th \u2014 Finishes", 56425, "x", ""),
      draw(6, "6th \u2014 Final", 38044, "x", "")
    ]
  },
  {
    id: 2,
    nm: "Henderson Build",
    md: "Cajun",
    cu: "James Henderson",
    ph: "Interior",
    pm: "P. Olson",
    ct: 318320,
    bg: {
      Framing: 28080,
      Roofing: 9600,
      Siding: 5400,
      "Ext Trim": 7200,
      "D&W": 3400,
      Cabinets: 24500,
      Flooring: 4320,
      Drywall: 9702,
      Paint: 7200,
      Trim: 8100,
      Electrical: 12600,
      Plumbing: 8400,
      Insulation: 6930,
      HVAC: 12000,
      General: 5875
    },
    ac: {
      Framing: 27500,
      Roofing: 9200,
      Siding: 5100,
      "Ext Trim": 6800,
      "D&W": 3400,
      Cabinets: 23200,
      Flooring: 4100,
      Drywall: 9500,
      Paint: 0,
      Trim: 0,
      Electrical: 12200,
      Plumbing: 8100,
      Insulation: 6800,
      HVAC: 11500,
      General: 4200
    },
    dr: [
      draw(0, "Deposit", 2500, "p", "Jan 5"),
      draw(1, "1st \u2014 Materials", 82000, "p", "Jan 12"),
      draw(2, "2nd \u2014 Concrete", 31590, "p", "Jan 28"),
      draw(3, "3rd \u2014 Framing", 45480, "p", "Feb 18"),
      draw(4, "4th \u2014 Rough-ins", 63664, "p", "Mar 15"),
      draw(5, "5th \u2014 Finishes", 63664, "c", ""),
      draw(6, "6th \u2014 Final", 29422, "x", "")
    ]
  },
  {
    id: 3,
    nm: "Cooper Ranch",
    md: "Mini Pettus",
    cu: "Sarah Cooper",
    ph: "Punch",
    pm: "P. Olson",
    ct: 399457,
    bg: {
      Framing: 32000,
      Roofing: 11200,
      Siding: 6200,
      "Ext Trim": 8400,
      "D&W": 3800,
      Cabinets: 28600,
      Flooring: 4910,
      Drywall: 11028,
      Paint: 8184,
      Trim: 9200,
      Electrical: 14322,
      Plumbing: 9600,
      Insulation: 7877,
      HVAC: 16000,
      General: 5875
    },
    ac: {
      Framing: 31200,
      Roofing: 10800,
      Siding: 6100,
      "Ext Trim": 8200,
      "D&W": 3650,
      Cabinets: 27900,
      Flooring: 4750,
      Drywall: 10800,
      Paint: 7900,
      Trim: 8900,
      Electrical: 14100,
      Plumbing: 9400,
      Insulation: 7600,
      HVAC: 15500,
      General: 5600
    },
    dr: [
      draw(0, "Deposit", 2500, "p", "Nov 1"),
      draw(1, "1st \u2014 Materials", 104000, "p", "Nov 8"),
      draw(2, "2nd \u2014 Concrete", 32742, "p", "Nov 25"),
      draw(3, "3rd \u2014 Framing", 51135, "p", "Dec 20"),
      draw(4, "4th \u2014 Rough-ins", 79891, "p", "Jan 30"),
      draw(5, "5th \u2014 Finishes", 79891, "p", "Mar 5"),
      draw(6, "6th \u2014 Final", 49298, "c", "")
    ]
  }
];

var DEMO_UPS = [
  { d: "Standing Seam Roof", a: 8240 },
  { d: "Craftsman Cabinets", a: 1200 },
  { d: "Tile Master Shower", a: 3500 },
  { d: "200 AMP Connection", a: 2500 },
  { d: "EL42 Fireplace", a: 5500 },
  { d: "LVP Flooring Upgrade", a: 2800 }
];

var U = null;
var R = null;
var SS = 0;
var NP = {
  model: null,
  cust: "",
  met: {},
  ups: [],
  p10: 0,
  _conc: 0,
  _tka: 0
};

function $(id) {
  return document.getElementById(id);
}

function F(amount) {
  return "$" + Math.round(amount).toLocaleString();
}

function P(numerator, denominator) {
  return denominator ? Math.round((numerator / denominator) * 100) : 0;
}

function toast(message) {
  var toastEl = $("TT");
  if (!toastEl) {
    return;
  }

  toastEl.textContent = message;
  toastEl.classList.add("show");

  setTimeout(function() {
    toastEl.classList.remove("show");
  }, 3500);
}

function doLogin() {
  U = UU[$("lU").value];
  R = $("lR").value;

  $("LW").style.display = "none";
  $("AW").style.display = "block";

  $("hN").textContent = U.n;
  $("hA").textContent = U.i;
  $("hR").textContent = U.rl + " \u00B7 " + RG[R].nm;

  if (typeof render === "function") {
    render();
  }
}

function doLogout() {
  $("LW").style.display = "";
  $("AW").style.display = "none";
}
