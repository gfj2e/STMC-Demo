// STMC Ops – Shell Wizard (shell.js)
// Requires script.js (window.STMC) loaded first.

(function () {
  "use strict";
  var S = window.STMC;

  // ── Rates ─────────────────────────────────────────────────────────────────
  var ZONE_RATES = { "1": 7.50, "2": 8.25, "3": 8.75 };
  var SLAB_TYPE_ADDER = { "4fiber": 0, "6fiber": 0.55, "4mono": 0.75, "6mono": 1.10 };

  // ── Steps ─────────────────────────────────────────────────────────────────
  var STEP_LABELS = ["Metrics", "Concrete", "Exterior", "Contract"];
  var STEP_IDS    = ["sh-step-0", "sh-step-1", "sh-step-2", "sh-step-3"];
  var TOTAL_STEPS = STEP_LABELS.length;

  var state = null;

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
      extDoors:  3,
      windows:   Math.round(sf / 150 + 3)
    };
    m.slabSF = (m.livingSF || 0) + (m.garageSF || 0) + (m.porchSF || 0);
    return m;
  }

  function recomputeMetrics(m) {
    m.slabSF = (m.livingSF || 0) + (m.garageSF || 0) + (m.porchSF || 0);
    return m;
  }

  function initState(data) {
    var models = getModels(data);
    var def    = models[0] || null;
    var cust   = loadCustomer();
    return {
      step: 0,
      customerName: cust.customerName || "",
      modelId: def ? def.id : "",
      regionId: S.getSession().regionId,
      metrics: initMetrics(def),
      p10: def ? Math.round(S.parseNumber(def.materialTotal) * 1.1) : 0,
      // slab
      slabArea: 0, slabType: "4fiber", slabZone: "1",
      // concrete
      concreteArea: 0, concreteType: "4fiber", concreteZone: "1",
      cLp: false, cBp: false, cWire: false, cRebar: false,
      cDriveSF: 0, cWalkSF: 0
    };
  }

  function loadCustomer() {
    try { return JSON.parse(localStorage.getItem("stmc_customer") || "{}"); }
    catch (e) { return {}; }
  }

  function getModels(data) {
    return (data && data.sales && data.sales.wizard && data.sales.wizard.models) || [];
  }

  function getRateCard(data) {
    return (data && data.sales && data.sales.wizard && data.sales.wizard.rateCard) || [];
  }

  function getRegion(data) {
    var regions = (data && data.regions) || [];
    var sid = S.getSession().regionId;
    return regions.find(function (r) { return r.id === sid; }) || regions[0] || {};
  }

  // ── Calcs ─────────────────────────────────────────────────────────────────
  function calcSlabCost() {
    var area  = state.slabArea || state.metrics.slabSF || 0;
    var rate  = ZONE_RATES[state.slabZone] || 7.50;
    var adder = SLAB_TYPE_ADDER[state.slabType] || 0;
    return Math.round(area * (rate + adder));
  }

  function calcConcrete() {
    var area  = state.concreteArea || 0;
    var rate  = ZONE_RATES[state.concreteZone] || 7.50;
    var adder = SLAB_TYPE_ADDER[state.concreteType] || 0;
    var slab  = Math.round(area * (rate + adder));
    var extras = 0;
    if (state.cLp)    extras += 1750;
    if (state.cBp)    extras += 2500;
    if (state.cWire)  extras += Math.round(area * 0.85);
    if (state.cRebar) extras += Math.round(area * 1.25);
    var drive = Math.round((state.cDriveSF || 0) * rate);
    var walk  = Math.round((state.cWalkSF  || 0) * (rate * 0.9));
    return { slab: slab, extras: extras, drive: drive, walk: walk, total: slab + extras + drive + walk };
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

  function calcContract(data) {
    var slab     = calcSlabCost();
    var concrete = calcConcrete();
    var exterior = calcExterior(data);
    var p10      = S.parseNumber(state.p10);
    var total    = p10 + slab + concrete.total + exterior.customerPrice;

    var deposit = 2500;
    var d1 = Math.max(p10 - deposit, 0);
    var d2 = slab;
    var d3 = concrete.total;
    var d4 = exterior.customerPrice;

    return {
      p10: p10, slab: slab, concrete: concrete.total,
      exterior: exterior.customerPrice,
      total: total,
      draws: [deposit, d1, d2, d3, d4]
    };
  }

  // ── Progress bar ──────────────────────────────────────────────────────────
  function buildProgressBar() {
    var bar = document.getElementById("sh-progress-bar");
    if (!bar) return;
    var html = "";
    STEP_LABELS.forEach(function (label, i) {
      if (i > 0) html += "<div class=\"wiz-prog-sep\" id=\"sh-sep-" + (i - 1) + "\"></div>";
      html += "<button class=\"wiz-prog-step\" id=\"sh-prog-" + i + "\" type=\"button\">" +
        "<div class=\"wiz-prog-num\" id=\"sh-pnum-" + i + "\">" + (i + 1) + "</div>" +
        "<div class=\"wiz-prog-label\">" + label + "</div></button>";
    });
    bar.innerHTML = html;
  }

  function updateProgressBar() {
    STEP_LABELS.forEach(function (_, i) {
      var btn  = document.getElementById("sh-prog-"  + i);
      var pnum = document.getElementById("sh-pnum-"  + i);
      var sep  = document.getElementById("sh-sep-"   + (i - 1));
      if (!btn) return;
      btn.classList.remove("active", "done");
      if (i < state.step)       { btn.classList.add("done");   pnum.textContent = "✓"; }
      else if (i === state.step) { btn.classList.add("active"); pnum.textContent = String(i + 1); }
      else                       { pnum.textContent = String(i + 1); }
      if (sep) sep.classList.toggle("done", i <= state.step);
    });
    var st = document.getElementById("sh-status");
    if (st) st.textContent = "Step " + (state.step + 1) + " of " + TOTAL_STEPS;
  }

  function showStep() {
    STEP_IDS.forEach(function (id, i) {
      var el = document.getElementById(id);
      if (el) el.style.display = i === state.step ? "" : "none";
    });
    var prev = document.getElementById("sh-prev");
    var next = document.getElementById("sh-next");
    if (prev) prev.disabled = (state.step === 0);
    if (next) next.textContent = (state.step === TOTAL_STEPS - 1) ? "Finish" : "Next →";
  }

  // ── Fill helpers ──────────────────────────────────────────────────────────
  function fillMetrics() {
    var editable = ["livingSF","garageSF","porchSF","roofSF","extWallSF","soffitLF","beamLF","extDoors","windows"];
    editable.forEach(function (k) {
      var el = document.getElementById("sh-m-" + k);
      if (el) el.value = Math.round(S.parseNumber(state.metrics[k]));
    });
    S.setText("sh-m-slabSF", S.formatCount(state.metrics.slabSF));
    var hint = document.getElementById("sh-slab-area-hint");
    if (hint) hint.textContent = "Slab: " + S.formatCount(state.metrics.slabSF) + " SF";
    var slabEl = document.getElementById("sh-slab-area");
    if (slabEl && !slabEl.value) slabEl.value = Math.round(state.metrics.slabSF);
    var p10El = document.getElementById("sh-p10");
    if (p10El && !p10El.value) p10El.value = Math.round(S.parseNumber(state.p10));
    var slabCost = calcSlabCost();
    S.setText("sh-slab-cost", S.formatMoney(slabCost));
    S.setText("sh-p10-kpi",   S.formatMoney(S.parseNumber(state.p10)));
  }

  function fillConcrete() {
    var c    = calcConcrete();
    var hint = document.getElementById("sh-c-area-hint");
    if (hint) hint.textContent = "Slab: " + S.formatCount(state.metrics.slabSF) + " SF";
    S.setText("sh-c-lp-cost",    state.cLp    ? "$1,750" : "—");
    S.setText("sh-c-bp-cost",    state.cBp    ? "$2,500" : "—");
    S.setText("sh-c-wire-cost",  state.cWire  ? S.formatMoney(Math.round((state.concreteArea || 0) * 0.85)) : "—");
    S.setText("sh-c-rebar-cost", state.cRebar ? S.formatMoney(Math.round((state.concreteArea || 0) * 1.25)) : "—");
    S.setText("sh-c-drive-cost", S.formatMoney(c.drive));
    S.setText("sh-c-walk-cost",  S.formatMoney(c.walk));
    S.setText("sh-c-slab-cost",  S.formatMoney(c.slab));
    S.setText("sh-c-total",      S.formatMoney(c.total));
  }

  function fillExterior(data) {
    var ext  = calcExterior(data);
    var body = document.getElementById("sh-ext-lines-body");
    if (body) {
      body.innerHTML = ext.lines.map(function (line) {
        return "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(line.label) + "</span>" +
          "<span class=\"rd\">" + S.formatCount(line.quantity) + " × $" + line.rate + "</span>" +
          "<span class=\"rv\">" + S.formatMoney(line.cost) + "</span></div>";
      }).join("") +
      "<div class=\"rw rt\"><span class=\"rl\">True cost</span>" +
      "<span class=\"rv\">" + S.formatMoney(ext.total) + "</span></div>";
    }
    S.setText("sh-ext-cust-price",       S.formatMoney(ext.customerPrice));
    S.setText("sh-ext-cust-slab-detail", S.formatCount(state.metrics.slabSF) + " SF × $12");
    S.setText("sh-ext-cust-total",       S.formatMoney(ext.customerPrice));
    S.setText("sh-ext-true-cost",        S.formatMoney(ext.total));
    S.setText("sh-ext-kpi-customer",     S.formatMoney(ext.customerPrice));
    S.setText("sh-ext-kpi-truecost",     S.formatMoney(ext.total));
    var mEl = document.getElementById("sh-ext-kpi-margin");
    if (mEl) { mEl.textContent = ext.margin + "%"; mEl.style.color = ext.margin >= 20 ? "var(--green)" : "var(--red)"; }
  }

  function fillContract(data) {
    var ct   = calcContract(data);
    var cust = loadCustomer();
    S.setText("sh-cont-customer", cust.customerName || state.customerName || "Customer");
    S.setText("sh-cont-p10",      S.formatMoney(ct.p10));
    S.setText("sh-cont-slab",     S.formatMoney(ct.slab));
    S.setText("sh-cont-concrete", S.formatMoney(ct.concrete));
    S.setText("sh-cont-exterior", S.formatMoney(ct.exterior));
    S.setText("sh-cont-total",    S.formatMoney(ct.total));
    S.setText("sh-cont-banner",   S.formatMoney(ct.total));
    ct.draws.forEach(function (amt, i) { S.setText("sh-draw-" + i, S.formatMoney(amt)); });
    S.setText("sh-draw-total", S.formatMoney(ct.total));
    S.setText("sh-header-total", S.formatMoney(ct.total));
    var hc = document.getElementById("sh-header-customer");
    if (hc) hc.textContent = cust.customerName || state.customerName || "Shell Only";
  }

  // ── Master update ─────────────────────────────────────────────────────────
  function update(data) {
    updateProgressBar();
    showStep();
    if (state.step === 0) fillMetrics();
    if (state.step === 1) fillConcrete();
    if (state.step === 2) fillExterior(data);
    if (state.step === 3) fillContract(data);
    var ct = calcContract(data);
    S.setText("sh-header-total", S.formatMoney(ct.total));
  }

  // ── Event bindings ────────────────────────────────────────────────────────
  function bindEvents(data) {
    // Metric inputs
    document.querySelectorAll("[id^='sh-m-']").forEach(function (inp) {
      if (inp.tagName !== "INPUT") return;
      var key = inp.id.replace("sh-m-", "");
      inp.addEventListener("input", function () {
        state.metrics[key] = S.parseNumber(inp.value);
        state.metrics = recomputeMetrics(state.metrics);
        S.setText("sh-m-slabSF", S.formatCount(state.metrics.slabSF));
        S.setText("sh-slab-cost", S.formatMoney(calcSlabCost()));
      });
    });

    // Slab
    bind("sh-slab-area", "input",  function (v) { state.slabArea = S.parseNumber(v); fillMetrics(); });
    bind("sh-slab-type", "change", function (v) { state.slabType = v; fillMetrics(); });
    bind("sh-slab-zone", "change", function (v) { state.slabZone = v; fillMetrics(); });
    bind("sh-p10",       "input",  function (v) { state.p10 = S.parseNumber(v); S.setText("sh-p10-kpi", S.formatMoney(state.p10)); });

    // Concrete
    bind("sh-c-area",  "input",  function (v) { state.concreteArea = S.parseNumber(v); fillConcrete(); });
    bind("sh-c-type",  "change", function (v) { state.concreteType = v; fillConcrete(); });
    bind("sh-c-zone",  "change", function (v) { state.concreteZone = v; fillConcrete(); });
    bind("sh-c-drive", "input",  function (v) { state.cDriveSF = S.parseNumber(v); fillConcrete(); });
    bind("sh-c-walk",  "input",  function (v) { state.cWalkSF  = S.parseNumber(v); fillConcrete(); });
    bindCheck("sh-c-lp",    function (v) { state.cLp    = v; fillConcrete(); });
    bindCheck("sh-c-bp",    function (v) { state.cBp    = v; fillConcrete(); });
    bindCheck("sh-c-wire",  function (v) { state.cWire  = v; fillConcrete(); });
    bindCheck("sh-c-rebar", function (v) { state.cRebar = v; fillConcrete(); });

    var cSlabBtn = document.getElementById("sh-c-use-slab-btn");
    if (cSlabBtn) cSlabBtn.addEventListener("click", function () {
      state.concreteArea = state.metrics.slabSF || 0;
      var el = document.getElementById("sh-c-area");
      if (el) el.value = Math.round(state.concreteArea);
      fillConcrete();
    });

    // Nav
    var prevBtn = document.getElementById("sh-prev");
    var nextBtn = document.getElementById("sh-next");
    if (prevBtn) prevBtn.addEventListener("click", function () {
      if (state.step > 0) { state.step--; update(data); window.scrollTo(0, 0); }
    });
    if (nextBtn) nextBtn.addEventListener("click", function () {
      if (state.step < TOTAL_STEPS - 1) { state.step++; update(data); window.scrollTo(0, 0); }
    });

    // PDF / DocuSign stubs
    var genBtn = document.getElementById("sh-generate");
    var dsBtn  = document.getElementById("sh-docusign");
    if (genBtn) genBtn.addEventListener("click", function () { S.showToast("Contract PDF generated."); });
    if (dsBtn)  dsBtn.addEventListener("click",  function () { S.showToast("Sent to DocuSign."); });

    // Logout → login
    document.querySelectorAll(".logout-link").forEach(function (el) {
      el.addEventListener("click", function () {
        window.location.href = (window.STMC_ROUTES && window.STMC_ROUTES.login) || "/stmc_ops/login/";
      });
    });
  }

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
      console.error("STMC shell load error:", err);
    });
  });

}());
