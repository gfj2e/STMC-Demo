// STMC Ops – Turnkey Wizard (turnkey.js)
// Requires script.js (window.STMC) loaded first.

(function () {
  "use strict";
  var S = window.STMC;

  // ── Concrete zone rates (per SF) ──────────────────────────────────────────
  var ZONE_RATES = { "1": 7.50, "2": 8.25, "3": 8.75 };
  var SLAB_TYPE_ADDER = { "4fiber": 0, "6fiber": 0.55, "4mono": 0.75, "6mono": 1.10 };

  // Cabinet line rates per LF
  var CAB_RATES = { standard: 0, mid: 220, premium: 420, custom: 0 };
  var COUNTER_RATES = { laminate: 0, granite: 42, quartz: 55, butcher: 38, custom: 0 };

  // Selection adders (flat amounts)
  var SEL_ADDERS = {
    hardwood: 3.50, tile: 2.00, carpet: -0.50, mix: 0,   // flooring per SF vs LVP base
    fireplace: 4200,
    tile_shower: 1800,
    deck: 6500
  };

  // Lighting package adder (flat)
  var LIGHT_ADDERS = { standard: 0, upgraded: 1800, premium: 3600 };
  var TRIM_ADDERS  = { standard: 0, craftsman: 900, farmhouse: 1600 };

  // ── Wizard state ──────────────────────────────────────────────────────────
  var STEP_LABELS = [
    "Metrics", "Concrete", "Exterior", "Interior",
    "Cabinets", "Selections", "P10 & Upgrades", "Contract", "Budget"
  ];
  var STEP_IDS = [
    "tk-step-0", "tk-step-1", "tk-step-2", "tk-step-3",
    "tk-step-4", "tk-step-5", "tk-step-6", "tk-step-7", "tk-step-8"
  ];
  var TOTAL_STEPS = STEP_LABELS.length;

  var state = null;   // see initState()

  function initMetrics(model) {
    var sf = S.parseNumber(model && model.livingSf);
    var m = {
      livingSF:  sf,
      garageSF:  Math.round(sf * 0.35),
      porchSF:   Math.round(sf * 0.18),
      roofSF:    Math.round(sf * 1.8),
      extWallSF: Math.round(sf * 0.85),
      soffitLF:  Math.round(Math.sqrt(Math.max(sf, 1)) * 5.2),
      beamLF:    0,
      cabLF:     Math.round(sf * 0.02 + 12),
      intDoors:  Math.round(sf / 120),
      extDoors:  3,
      windows:   Math.round(sf / 150 + 3),
      fixtures:  Math.round(sf / 200 + 4)
    };
    return recomputeMetrics(m);
  }

  function recomputeMetrics(m) {
    m.slabSF    = (m.livingSF || 0) + (m.garageSF || 0) + (m.porchSF || 0);
    m.counterSF = Math.round((m.cabLF || 0) * 2);
    m.hvacTons  = Math.max(2, Math.round((m.livingSF || 0) / 500));
    return m;
  }

  function initState(data) {
    var models = getModels(data);
    var def    = models[0] || null;
    var cust   = loadCustomer();
    return {
      step:         0,
      customerName: cust.customerName || "",
      modelId:      def ? def.id : "",
      regionId:     S.getSession().regionId,
      metrics:      initMetrics(def),
      // concrete
      concreteArea: 0, concreteType: "4fiber", concreteZone: "1",
      cLp: false, cBp: false, cWire: false, cRebar: false,
      cFoamLF: 0, cDriveSF: 0, cWalkSF: 0,
      // slab/foundation
      slabArea: 0, slabType: "4fiber", slabZone: "1", pierBeam: 0,
      // cabinets
      cabLine: "standard", cabDoor: "shaker", cabFinish: "white",
      cabLF: 0, cabCtSF: 0, cabCounter: "laminate", cabIsland: false,
      // selections
      selFloor: "lvp", selFloorSF: 0, selBathTile: "standard",
      selPaint: "standard", selTrim: "standard", selLighting: "standard",
      selFireplace: false, selTileShower: false, selDeck: false,
      // budget
      p10: def ? Math.round(S.parseNumber(def.materialTotal) * 1.1) : 0,
      upgrades: []
    };
  }

  function loadCustomer() {
    try {
      return JSON.parse(localStorage.getItem("stmc_customer") || "{}");
    } catch (e) { return {}; }
  }

  function getModels(data) {
    return (data && data.sales && data.sales.wizard && data.sales.wizard.models) || [];
  }

  function getRateCard(data) {
    return (data && data.sales && data.sales.wizard && data.sales.wizard.rateCard) || [];
  }

  // ── Calculations ──────────────────────────────────────────────────────────
  function calcSlabCost() {
    var area = state.slabArea || state.metrics.slabSF || 0;
    var rate = ZONE_RATES[state.slabZone] || 7.50;
    var adder = SLAB_TYPE_ADDER[state.slabType] || 0;
    return Math.round(area * (rate + adder));
  }

  function calcConcrete() {
    var area  = state.concreteArea || 0;
    var zone  = state.concreteZone || "1";
    var rate  = ZONE_RATES[zone] || 7.50;
    var adder = SLAB_TYPE_ADDER[state.concreteType] || 0;
    var slab  = Math.round(area * (rate + adder));
    var extras = 0;
    if (state.cLp)  extras += 1750;
    if (state.cBp)  extras += 2500;
    if (state.cWire)  extras += Math.round(area * 0.85);
    if (state.cRebar) extras += Math.round(area * 1.25);
    var foam  = Math.round((state.cFoamLF || 0) * 9);
    var drive = Math.round((state.cDriveSF || 0) * rate);
    var walk  = Math.round((state.cWalkSF  || 0) * (rate * 0.9));
    return { slab: slab, extras: extras, foam: foam, drive: drive, walk: walk,
             total: slab + extras + foam + drive + walk };
  }

  function calcExterior(data) {
    var rateCard = getRateCard(data);
    var region   = getRegion(data);
    var mult     = S.parseNumber(region.laborMultiplier) || 1;
    var lines = [], total = 0;
    rateCard.forEach(function (item) {
      if (item.category !== "exterior") return;
      var qty  = item.metric === "flat" ? 1 : S.parseNumber(state.metrics[item.metric]);
      var cost = Math.round(qty * S.parseNumber(item.rate) * mult);
      if (cost > 0) {
        lines.push({ label: item.label, quantity: qty, rate: S.parseNumber(item.rate), cost: cost, unit: item.unit || "" });
        total += cost;
      }
    });
    var custPrice = Math.round(S.parseNumber(state.metrics.slabSF) * 12);
    var margin    = custPrice ? Math.round((1 - total / custPrice) * 100) : 0;
    return { lines: lines, total: total, customerPrice: custPrice, margin: margin };
  }

  function calcInterior(data) {
    var rateCard = getRateCard(data);
    var region   = getRegion(data);
    var model    = getModel(data);
    var byGroup  = {}, trueCost = 0;
    rateCard.forEach(function (item) {
      if (item.category !== "interior") return;
      var qty  = item.metric === "flat" ? 1 : S.parseNumber(state.metrics[item.metric]);
      var cost = Math.round(qty * S.parseNumber(item.rate));
      trueCost += cost;
      if (item.group) byGroup[item.group] = (byGroup[item.group] || 0) + cost;
    });
    var turnkeyRate = S.parseNumber(model && model.turnkeyRate);
    var premium     = S.parseNumber(region.turnkeyPremium);
    var livingSf    = S.parseNumber(model && model.livingSf);
    var contract    = Math.round(livingSf * (turnkeyRate + premium));
    var margin      = contract ? Math.round((1 - trueCost / contract) * 100) : 0;
    return { byGroup: byGroup, trueCost: trueCost, contract: contract, margin: margin };
  }

  function calcCabinets() {
    var lf   = state.cabLF || state.metrics.cabLF || 0;
    var ctSF = state.cabCtSF || state.metrics.counterSF || 0;
    var pkg  = Math.round(lf * (CAB_RATES[state.cabLine] || 0));
    var ctr  = Math.round(ctSF * (COUNTER_RATES[state.cabCounter] || 0));
    var island = state.cabIsland ? 1200 : 0;
    return { package: pkg, counter: ctr, island: island, total: pkg + ctr + island };
  }

  function calcSelections() {
    var sf    = state.selFloorSF || state.metrics.livingSF || 0;
    var adder = (SEL_ADDERS[state.selFloor] || 0);
    var floor = Math.round(sf * Math.max(0, adder));
    var fp    = state.selFireplace  ? SEL_ADDERS.fireplace  : 0;
    var ts    = state.selTileShower ? SEL_ADDERS.tile_shower : 0;
    var deck  = state.selDeck       ? SEL_ADDERS.deck        : 0;
    var light = LIGHT_ADDERS[state.selLighting] || 0;
    var trim  = TRIM_ADDERS[state.selTrim]      || 0;
    var total = floor + fp + ts + deck + light + trim;
    return { floor: floor, fireplace: fp, tileShower: ts, deck: deck, light: light, trim: trim, total: total };
  }

  function calcUpgradesTotal() {
    return state.upgrades.reduce(function (t, u) { return t + S.parseNumber(u.amount); }, 0);
  }

  function calcContract(data) {
    var slab     = calcSlabCost();
    var concrete = calcConcrete();
    var exterior = calcExterior(data);
    var interior = calcInterior(data);
    var cabinets = calcCabinets();
    var sel      = calcSelections();
    var upgTotal = calcUpgradesTotal();
    var p10      = S.parseNumber(state.p10);

    var total = p10 + slab + concrete.total + exterior.customerPrice +
                interior.contract + cabinets.total + sel.total + upgTotal;

    var deposit = 2500;
    var d1 = Math.max(p10 - deposit, 0);
    var d2 = slab;
    var d3 = concrete.total;
    var d4 = exterior.customerPrice;
    var d5 = Math.round((interior.contract + cabinets.total) / 2);
    var d6 = total - deposit - d1 - d2 - d3 - d4 - d5;

    return {
      p10: p10, slab: slab, concrete: concrete.total,
      exterior: exterior.customerPrice,
      interior: interior.contract,
      cabinets: cabinets.total,
      upgrades: sel.total + upgTotal,
      total: total,
      exterior_obj: exterior, interior_obj: interior,
      draws: [deposit, d1, d2, d3, d4, d5, d6]
    };
  }

  function getRegion(data) {
    var regions = (data && data.regions) || [];
    var sid     = S.getSession().regionId;
    return regions.find(function (r) { return r.id === sid; }) || regions[0] || {};
  }

  function getModel(data) {
    var models = getModels(data);
    return models.find(function (m) { return m.id === state.modelId; }) || models[0] || null;
  }

  // ── Progress bar ──────────────────────────────────────────────────────────
  function buildProgressBar() {
    var bar = document.getElementById("tk-progress-bar");
    if (!bar) return;
    var html = "";
    STEP_LABELS.forEach(function (label, i) {
      if (i > 0) html += "<div class=\"wiz-prog-sep\" id=\"tk-sep-" + (i - 1) + "\"></div>";
      html += "<button class=\"wiz-prog-step\" id=\"tk-prog-" + i + "\" type=\"button\">" +
        "<div class=\"wiz-prog-num\" id=\"tk-pnum-" + i + "\">" + (i + 1) + "</div>" +
        "<div class=\"wiz-prog-label\">" + label + "</div>" +
        "</button>";
    });
    bar.innerHTML = html;
  }

  function updateProgressBar() {
    STEP_LABELS.forEach(function (_, i) {
      var btn  = document.getElementById("tk-prog-"  + i);
      var pnum = document.getElementById("tk-pnum-"  + i);
      var sep  = document.getElementById("tk-sep-"   + (i - 1));
      if (!btn) return;
      btn.classList.remove("active", "done");
      if (i < state.step)      { btn.classList.add("done");   pnum.textContent = "✓"; }
      else if (i === state.step) { btn.classList.add("active"); pnum.textContent = String(i + 1); }
      else                       { pnum.textContent = String(i + 1); }
      if (sep) sep.classList.toggle("done", i <= state.step);
    });
    var st = document.getElementById("tk-status");
    if (st) st.textContent = "Step " + (state.step + 1) + " of " + TOTAL_STEPS;
  }

  // ── Step panels ───────────────────────────────────────────────────────────
  function showStep() {
    STEP_IDS.forEach(function (id, i) {
      var el = document.getElementById(id);
      if (el) el.style.display = i === state.step ? "" : "none";
    });
    var prev = document.getElementById("tk-prev");
    var next = document.getElementById("tk-next");
    if (prev) prev.disabled = (state.step === 0);
    if (next) {
      next.textContent = (state.step === TOTAL_STEPS - 1) ? "Finish" : "Next →";
      next.disabled = false;
    }
  }

  // ── Fill helpers ──────────────────────────────────────────────────────────
  function fillMetrics() {
    var editable = ["livingSF","garageSF","porchSF","roofSF","extWallSF",
                    "soffitLF","beamLF","cabLF","intDoors","extDoors","windows","fixtures"];
    editable.forEach(function (k) {
      var el = document.getElementById("m-" + k);
      if (el) el.value = Math.round(S.parseNumber(state.metrics[k]));
    });
    S.setText("m-slabSF",    S.formatCount(state.metrics.slabSF));
    S.setText("m-counterSF", S.formatCount(state.metrics.counterSF));
    S.setText("m-hvacTons",  String(state.metrics.hvacTons));
    var hint = document.getElementById("tk-slab-area-hint");
    if (hint) hint.textContent = "Slab: " + S.formatCount(state.metrics.slabSF) + " SF";
    var slabEl = document.getElementById("tk-slab-area");
    if (slabEl && !slabEl.value) slabEl.value = Math.round(state.metrics.slabSF);
    var slabCost = calcSlabCost();
    S.setText("tk-slab-cost",  S.formatMoney(slabCost));
    S.setText("tk-slab-total", S.formatMoney(slabCost + S.parseNumber(state.pierBeam)));
  }

  function fillConcrete() {
    var c = calcConcrete();
    var hint = document.getElementById("c-area-hint");
    if (hint) hint.textContent = "Slab: " + S.formatCount(state.metrics.slabSF) + " SF";
    S.setText("c-lp-cost",    state.cLp    ? "$1,750" : "—");
    S.setText("c-bp-cost",    state.cBp    ? "$2,500" : "—");
    S.setText("c-wire-cost",  state.cWire  ? S.formatMoney(Math.round((state.concreteArea || 0) * 0.85)) : "—");
    S.setText("c-rebar-cost", state.cRebar ? S.formatMoney(Math.round((state.concreteArea || 0) * 1.25)) : "—");
    S.setText("c-foam-cost",  S.formatMoney(Math.round((state.cFoamLF  || 0) * 9)));
    S.setText("c-drive-cost", S.formatMoney(c.drive));
    S.setText("c-walk-cost",  S.formatMoney(c.walk));
    S.setText("c-slab-cost",  S.formatMoney(c.slab));
    S.setText("c-total",      S.formatMoney(c.total));
  }

  function fillExterior(data) {
    var ext  = calcExterior(data);
    var body = document.getElementById("ext-lines-body");
    if (body) {
      body.innerHTML = ext.lines.map(function (line) {
        return "<div class=\"rw\">" +
          "<span class=\"rl\">" + S.escapeHtml(line.label) + "</span>" +
          "<span class=\"rd\">" + S.formatCount(line.quantity) + " × $" + line.rate + "</span>" +
          "<span class=\"rv\">" + S.formatMoney(line.cost) + "</span></div>";
      }).join("") +
      "<div class=\"rw rt\"><span class=\"rl\">True cost</span>" +
      "<span class=\"rv\">" + S.formatMoney(ext.total) + "</span></div>";
    }
    S.setText("ext-cust-price",        S.formatMoney(ext.customerPrice));
    S.setText("ext-cust-slab-detail",  S.formatCount(state.metrics.slabSF) + " SF × $12");
    S.setText("ext-cust-total",        S.formatMoney(ext.customerPrice));
    S.setText("ext-true-cost",         S.formatMoney(ext.total));
    S.setText("ext-kpi-customer",      S.formatMoney(ext.customerPrice));
    S.setText("ext-kpi-truecost",      S.formatMoney(ext.total));
    var mEl = document.getElementById("ext-kpi-margin");
    if (mEl) { mEl.textContent = ext.margin + "%"; mEl.style.color = ext.margin >= 20 ? "var(--green)" : "var(--red)"; }
  }

  function fillInterior(data) {
    var int_ = calcInterior(data);
    var body = document.getElementById("int-groups-body");
    if (body) {
      body.innerHTML = Object.keys(int_.byGroup)
        .sort(function (a, b) { return int_.byGroup[b] - int_.byGroup[a]; })
        .map(function (g) {
          return "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(g) + "</span>" +
            "<span class=\"rv\">" + S.formatMoney(int_.byGroup[g]) + "</span></div>";
        }).join("") +
        "<div class=\"rw rt\"><span class=\"rl\">Total true cost</span>" +
        "<span class=\"rv\">" + S.formatMoney(int_.trueCost) + "</span></div>";
    }
    var model  = getModel(data);
    var region = getRegion(data);
    var tk     = S.parseNumber(model && model.turnkeyRate) + S.parseNumber(region.turnkeyPremium);
    var lsf    = S.parseNumber(model && model.livingSf);
    S.setText("int-sf-detail",    S.formatCount(lsf) + " SF × $" + tk.toFixed(2));
    S.setText("int-contract",     S.formatMoney(int_.contract));
    S.setText("int-contract-row", S.formatMoney(int_.contract));
    S.setText("int-true-cost",    S.formatMoney(int_.trueCost));
    S.setText("int-kpi-contract", S.formatMoney(int_.contract));
    S.setText("int-kpi-truecost", S.formatMoney(int_.trueCost));
    var mEl = document.getElementById("int-kpi-margin");
    if (mEl) { mEl.textContent = int_.margin + "%"; mEl.style.color = int_.margin >= 20 ? "var(--green)" : "var(--red)"; }
  }

  function fillCabinets() {
    var cabLF = state.cabLF || state.metrics.cabLF || 0;
    var cabCtSF = state.cabCtSF || state.metrics.counterSF || 0;
    var el;
    el = document.getElementById("cab-lf");  if (el && !el.value) el.value = Math.round(cabLF);
    el = document.getElementById("cab-ct");  if (el && !el.value) el.value = Math.round(cabCtSF);
    var hint = document.getElementById("cab-lf-hint"); if (hint) hint.textContent = "From metrics: " + Math.round(state.metrics.cabLF) + " LF";
    var cht  = document.getElementById("cab-ct-hint"); if (cht)  cht.textContent  = "Auto: " + Math.round(state.metrics.counterSF) + " SF";
    var c = calcCabinets();
    S.setText("cab-kpi-package", S.formatMoney(c.package));
    S.setText("cab-kpi-counter", S.formatMoney(c.counter));
    S.setText("cab-island-cost", state.cabIsland ? "$1,200" : "—");
  }

  function fillSelections() {
    var el = document.getElementById("sel-floor-sf");
    if (el && !el.value) el.value = Math.round(state.metrics.livingSF || 0);
    var sel = calcSelections();
    S.setText("sel-floor-cost",       S.formatMoney(sel.floor));
    S.setText("sel-fireplace-cost",   state.selFireplace  ? S.formatMoney(SEL_ADDERS.fireplace)  : "—");
    S.setText("sel-tile-shower-cost", state.selTileShower ? S.formatMoney(SEL_ADDERS.tile_shower) : "—");
    S.setText("sel-deck-cost",        state.selDeck        ? S.formatMoney(SEL_ADDERS.deck)       : "—");
    S.setText("sel-kpi-adder",        S.formatMoney(sel.total));
    S.setText("sel-kpi-floor",        S.formatMoney(sel.floor));
  }

  function fillBudget() {
    var el = document.getElementById("tk-p10");
    if (el) el.value = Math.round(S.parseNumber(state.p10));
    var total = calcUpgradesTotal();
    S.setText("tk-upgrades-total", S.formatMoney(total));
    var body = document.getElementById("tk-upgrades-body");
    if (body) {
      if (state.upgrades.length) {
        body.innerHTML = state.upgrades.map(function (u, idx) {
          return "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(u.description) + "</span>" +
            "<span class=\"rv\" style=\"display:flex;align-items:center;gap:8px\">" +
            S.formatMoney(u.amount) +
            "<button data-idx=\"" + idx + "\" class=\"tk-upg-del\" style=\"font-size:10px;border:none;background:none;cursor:pointer;color:var(--red);padding:0\">✕</button></span></div>";
        }).join("");
        // bind delete buttons
        body.querySelectorAll(".tk-upg-del").forEach(function (btn) {
          btn.addEventListener("click", function () {
            var idx = parseInt(btn.getAttribute("data-idx"), 10);
            state.upgrades.splice(idx, 1);
            fillBudget();
          });
        });
      } else {
        body.innerHTML = "<div class=\"wiz-banner wiz-banner-empty\">No upgrades added yet.</div>";
      }
    }
  }

  function fillPMBudget(data) {
    var ext  = calcExterior(data);
    var intr = calcInterior(data);
    var ct   = calcContract(data);
    var cab  = calcCabinets();
    var sel  = calcSelections();

    // Part A: contractor labor rows
    var ctrBody = document.getElementById("tk-bud-ctr-body");
    if (ctrBody) {
      if (ext.lines.length) {
        ctrBody.innerHTML = ext.lines.map(function (l) {
          return "<div class='rw'><span class='rl'>" + S.escapeHtml(l.label) + "</span>" +
            "<span class='rv'>" + S.formatMoney(l.cost) + "</span></div>";
        }).join("");
      } else {
        ctrBody.innerHTML = "<div class='wiz-banner wiz-banner-empty'>No exterior rate card items found.</div>";
      }
    }
    S.setText("tk-bud-ctr-total",    S.formatMoney(ext.total));
    S.setText("tk-bud-cust-labor",   S.formatMoney(ext.customerPrice));
    S.setText("tk-bud-ctr-cost",     S.formatMoney(ext.total));
    S.setText("tk-bud-labor-margin", ext.margin + "%");

    // Part C: interior trade budget rows
    var intBody = document.getElementById("tk-bud-int-body");
    if (intBody) {
      var groups = Object.keys(intr.byGroup);
      if (groups.length) {
        intBody.innerHTML = groups.map(function (g) {
          return "<div class='rw'><span class='rl'>" + S.escapeHtml(g) + "</span>" +
            "<span class='rv'>" + S.formatMoney(intr.byGroup[g]) + "</span></div>";
        }).join("");
      } else {
        intBody.innerHTML = "<div class='wiz-banner wiz-banner-empty'>No interior rate card items found.</div>";
      }
    }
    S.setText("tk-bud-int-total", S.formatMoney(intr.trueCost));

    // Part D: full build budget
    S.setText("tk-bud-p10",        S.formatMoney(ct.p10));
    S.setText("tk-bud-ext-labor",  S.formatMoney(ext.total));
    S.setText("tk-bud-concrete-cost", S.formatMoney(ct.concrete));
    S.setText("tk-bud-int-sum",    S.formatMoney(intr.trueCost));
    S.setText("tk-bud-cab-cost",   S.formatMoney(cab.total));
    S.setText("tk-bud-upg-cost",   S.formatMoney(sel.total + calcUpgradesTotal()));
    var grandTotal = ct.p10 + ext.total + ct.concrete + intr.trueCost + cab.total + sel.total + calcUpgradesTotal();
    S.setText("tk-bud-grand-total", S.formatMoney(grandTotal));
    S.setText("tk-bud-total-bar",  S.formatMoney(grandTotal));
  }

  function fillContract(data) {
    var ct = calcContract(data);
    var cust = loadCustomer();
    S.setText("tk-cont-customer", cust.customerName || state.customerName || "Customer");
    S.setText("tk-cont-p10",      S.formatMoney(ct.p10));
    S.setText("tk-cont-slab",     S.formatMoney(ct.slab));
    S.setText("tk-cont-concrete", S.formatMoney(ct.concrete));
    S.setText("tk-cont-exterior", S.formatMoney(ct.exterior));
    S.setText("tk-cont-interior", S.formatMoney(ct.interior));
    S.setText("tk-cont-cabinets", S.formatMoney(ct.cabinets));
    S.setText("tk-cont-upgrades", S.formatMoney(ct.upgrades));
    S.setText("tk-cont-total",    S.formatMoney(ct.total));
    S.setText("tk-cont-banner",   S.formatMoney(ct.total));
    ct.draws.forEach(function (amt, i) { S.setText("tk-draw-" + i, S.formatMoney(amt)); });
    S.setText("tk-draw-total", S.formatMoney(ct.total));
    // Update header total
    S.setText("tk-header-total", S.formatMoney(ct.total));
    var hc = document.getElementById("tk-header-customer");
    if (hc) hc.textContent = cust.customerName || state.customerName || "Turnkey";
  }

  // ── Master update ─────────────────────────────────────────────────────────
  function update(data) {
    updateProgressBar();
    showStep();
    var step = state.step;
    if (step === 0) fillMetrics();
    if (step === 1) fillConcrete();
    if (step === 2) fillExterior(data);
    if (step === 3) fillInterior(data);
    if (step === 4) fillCabinets();
    if (step === 5) fillSelections();
    if (step === 6) fillBudget();
    if (step === 7) fillContract(data);
    if (step === 8) fillPMBudget(data);
    // always keep header total refreshed
    var ct = calcContract(data);
    S.setText("tk-header-total", S.formatMoney(ct.total));
  }

  // ── Event bindings ────────────────────────────────────────────────────────
  function bindEvents(data) {
    // Metric inputs
    document.querySelectorAll(".metric-input[data-metric]").forEach(function (inp) {
      inp.addEventListener("input", function () {
        state.metrics[inp.getAttribute("data-metric")] = S.parseNumber(inp.value);
        state.metrics = recomputeMetrics(state.metrics);
        // refresh computed fields
        S.setText("m-slabSF",    S.formatCount(state.metrics.slabSF));
        S.setText("m-counterSF", S.formatCount(state.metrics.counterSF));
        S.setText("m-hvacTons",  String(state.metrics.hvacTons));
        var slabCost = calcSlabCost();
        S.setText("tk-slab-cost",  S.formatMoney(slabCost));
        S.setText("tk-slab-total", S.formatMoney(slabCost));
      });
    });

    // Slab fields
    bind("tk-slab-area",  "input",  function (v) { state.slabArea  = S.parseNumber(v); fillMetrics(); });
    bind("tk-slab-type",  "change", function (v) { state.slabType  = v; fillMetrics(); });
    bind("tk-slab-zone",  "change", function (v) { state.slabZone  = v; fillMetrics(); });
    bind("tk-pier-beam",  "input",  function (v) { state.pierBeam  = S.parseNumber(v); fillMetrics(); });

    // Concrete
    bind("c-area",  "input",  function (v) { state.concreteArea = S.parseNumber(v); fillConcrete(); });
    bind("c-type",  "change", function (v) { state.concreteType = v; fillConcrete(); });
    bind("c-zone",  "change", function (v) { state.concreteZone = v; fillConcrete(); });
    bind("c-foam",  "input",  function (v) { state.cFoamLF  = S.parseNumber(v); fillConcrete(); });
    bind("c-drive", "input",  function (v) { state.cDriveSF = S.parseNumber(v); fillConcrete(); });
    bind("c-walk",  "input",  function (v) { state.cWalkSF  = S.parseNumber(v); fillConcrete(); });
    bindCheck("c-lp",    function (v) { state.cLp    = v; fillConcrete(); });
    bindCheck("c-bp",    function (v) { state.cBp    = v; fillConcrete(); });
    bindCheck("c-wire",  function (v) { state.cWire  = v; fillConcrete(); });
    bindCheck("c-rebar", function (v) { state.cRebar = v; fillConcrete(); });
    var cSlabBtn = document.getElementById("c-use-slab-btn");
    if (cSlabBtn) cSlabBtn.addEventListener("click", function () {
      state.concreteArea = state.metrics.slabSF || 0;
      var el = document.getElementById("c-area");
      if (el) el.value = Math.round(state.concreteArea);
      fillConcrete();
    });

    // Cabinets
    bind("cab-line",    "change", function (v) { state.cabLine    = v; fillCabinets(); });
    bind("cab-door",    "change", function (v) { state.cabDoor    = v; });
    bind("cab-finish",  "change", function (v) { state.cabFinish  = v; });
    bind("cab-lf",      "input",  function (v) { state.cabLF      = S.parseNumber(v); fillCabinets(); });
    bind("cab-ct",      "input",  function (v) { state.cabCtSF    = S.parseNumber(v); fillCabinets(); });
    bind("cab-counter", "change", function (v) { state.cabCounter = v; fillCabinets(); });
    bindCheck("cab-island", function (v) { state.cabIsland = v; fillCabinets(); });

    // Selections
    bind("sel-floor",     "change", function (v) { state.selFloor     = v; fillSelections(); });
    bind("sel-floor-sf",  "input",  function (v) { state.selFloorSF   = S.parseNumber(v); fillSelections(); });
    bind("sel-bath-tile", "change", function (v) { state.selBathTile  = v; });
    bind("sel-paint",     "change", function (v) { state.selPaint     = v; });
    bind("sel-trim",      "change", function (v) { state.selTrim      = v; fillSelections(); });
    bind("sel-lighting",  "change", function (v) { state.selLighting  = v; fillSelections(); });
    bindCheck("sel-fireplace",  function (v) { state.selFireplace  = v; fillSelections(); });
    bindCheck("sel-tile-shower",function (v) { state.selTileShower = v; fillSelections(); });
    bindCheck("sel-deck",       function (v) { state.selDeck        = v; fillSelections(); });

    // P10
    bind("tk-p10", "input", function (v) { state.p10 = S.parseNumber(v); fillBudget(); });

    // Upgrade entry
    var addBtn    = document.getElementById("tk-add-upgrade");
    var form      = document.getElementById("tk-upgrade-form");
    var saveBtn   = document.getElementById("tk-upg-save");
    var cancelBtn = document.getElementById("tk-upg-cancel");
    if (addBtn)    addBtn.addEventListener("click",    function () { if (form) form.style.display = ""; });
    if (cancelBtn) cancelBtn.addEventListener("click", function () { if (form) form.style.display = "none"; });
    if (saveBtn) saveBtn.addEventListener("click", function () {
      var desc   = document.getElementById("tk-upg-desc");
      var amount = document.getElementById("tk-upg-amount");
      if (!desc || !desc.value.trim()) { S.showToast("Enter a description."); return; }
      state.upgrades.push({ description: desc.value.trim(), amount: S.parseNumber(amount && amount.value) });
      desc.value = ""; if (amount) amount.value = "";
      if (form) form.style.display = "none";
      fillBudget();
    });

    // Nav buttons
    var prevBtn = document.getElementById("tk-prev");
    var nextBtn = document.getElementById("tk-next");
    if (prevBtn) prevBtn.addEventListener("click", function () {
      if (state.step > 0) { state.step--; update(data); window.scrollTo(0, 0); }
    });
    if (nextBtn) nextBtn.addEventListener("click", function () {
      if (state.step < TOTAL_STEPS - 1) { state.step++; update(data); window.scrollTo(0, 0); }
    });

    // PDF / DocuSign stubs
    var genBtn = document.getElementById("tk-generate");
    var dsBtn  = document.getElementById("tk-docusign");
    if (genBtn) genBtn.addEventListener("click", function () { S.showToast("Contract PDF generated."); });
    if (dsBtn)  dsBtn.addEventListener("click",  function () { S.showToast("Sent to DocuSign."); });

    // Logout → login
    document.querySelectorAll(".logout-link").forEach(function (el) {
      el.addEventListener("click", function () {
        window.location.href = (window.STMC_ROUTES && window.STMC_ROUTES.login) || "/stmc_ops/login/";
      });
    });
  }

  // ── Tiny helpers ──────────────────────────────────────────────────────────
  function bind(id, event, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener(event, function () { fn(el.value); });
  }
  function bindCheck(id, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("change", function () { fn(el.checked); });
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    S.loadData().then(function (data) {
      state = initState(data);
      buildProgressBar();
      bindEvents(data);
      update(data);
    }).catch(function (err) {
      console.error("STMC turnkey load error:", err);
    });
  });

}());
