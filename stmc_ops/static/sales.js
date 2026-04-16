// STMC Ops – Sales role JavaScript (sales.js)
// Requires script.js to be loaded first (window.STMC).

(function () {
  var S = window.STMC;

  // ── Plan database — loaded from data.json planData ────────────────────────
  var SLAB_AREAS  = [];
  var ROOF_AREAS  = [];
  var SLAB_DATA   = {};
  var ROOF_DATA   = {};
  var PLAN_METRICS = {};

  function initPlanData(planData) {
    if (!planData) return;
    SLAB_AREAS   = planData.slabAreas   || [];
    ROOF_AREAS   = planData.roofAreas   || [];
    SLAB_DATA    = planData.slabData    || {};
    ROOF_DATA    = planData.roofData    || {};
    PLAN_METRICS = planData.planMetrics || {};
  }


  var STEP_LABELS = ["Model", "Metrics", "Exterior", "Concrete", "Interior", "P10 / Upgrades", "Contract"];
  var STEP_IDS    = ["step-model", "step-metrics", "step-exterior", "step-concrete",
                     "step-interior", "step-upgrades", "step-contract"];

  // ── Calculation helpers ───────────────────────────────────────────────────
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

  function getWizardData(salesData) {
    var w = salesData.wizard || {};
    var fallback = (salesData.models || []).map(function (item) {
      return {
        id:            item.model.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
        name:          item.model,
        livingSf:      S.parseNumber(item.sf),
        materialTotal: Math.round(S.parseNumber(item.total) * 0.24),
        laborBudget:   Math.round(S.parseNumber(item.total) * 0.11),
        concreteBudget:Math.round(S.parseNumber(item.total) * 0.1),
        turnkeyRate:   S.parseNumber(item.turnkeyPerSf)
      };
    });
    return {
      models:   w.models   || fallback,
      rateCard: w.rateCard || [],
      upgrades: w.upgrades || []
    };
  }

  function createWizardState(salesData) {
    var wd  = getWizardData(salesData);
    var def = wd.models[0] || null;
    return {
      step:         0,
      customerName: "",
      orderNumber:  "",
      address:      "",
      salesRep:     "",
      modelId:      def ? def.id : "",
      metrics:      initMetrics(def),
      upgrades:     [],
      p10:          Math.round(S.parseNumber(def && def.materialTotal) * 1.1),
      // ── Plans tab fields ────────────────────────────────────────────────
      foundType:     "concrete",
      bsmtFrame:     0,
      crawlSF:       0,
      stories:       1,
      slab:          [],
      roof:          [],
      sheath:        0,
      g26:           0,
      wallTuff:      0,
      wallRock:      0,
      wallStone:     0,
      wallType:      "Metal",
      stoneUpg:      0,
      wainscotUpg:   0,
      sglW:          0,
      dblW:          0,
      s2s:           0,
      s2d:           0,
      win12:         0,
      dblD:          0,
      sglD:          0,
      punchAmt:          2500,
      customCharges:     [],
      concCustomCharges: [],
      awnQty:            0,
      cupQty:        0,
      chimQty:       0,
      detShop:       0,
      deckShown:     0
    };
    loadModelPlans(def && def.name, state);
    return state;
  }

  // Load plan-specific data (slab schedule, roof schedule, plan metrics)
  // for the selected model and store it in state.
  function loadModelPlans(modelName, state) {
    if (!modelName) return;
    var key = modelName.toUpperCase();
    var pm  = PLAN_METRICS[key] || {};
    var sd  = SLAB_DATA[key]    || [];
    var rd  = ROOF_DATA[key]    || [];

    state.stories  = pm.st  || 1;
    state.wallTuff = pm.ew  || 0;
    state.dblD     = pm.dd  || 0;
    state.sglD     = pm.sd  || 0;
    state.dblW     = pm.dw  || 0;
    state.sglW     = pm.sw  || 0;

    state.slab = sd.map(function (s) { return { n: s.n, sf: s.sf, tg: 0 }; });
    if (!state.slab.length) state.slab = [{ n: "1st Floor Living Area", sf: 0, tg: 0 }];

    state.roof = rd.map(function (r) { return { n: r.n, sf: r.sf, steep: 0, type: "metal" }; });
    if (!state.roof.length) state.roof = [{ n: "House Roof", sf: 0, steep: 0, type: "metal" }];

    // Reset overridable plan fields
    state.foundType     = "concrete";
    state.bsmtFrame     = 0;
    state.crawlSF       = 0;
    state.sheath        = 0;
    state.g26           = 0;
    state.wallRock      = 0;
    state.wallStone     = 0;
    state.wallType      = "Metal";
    state.stoneUpg      = 0;
    state.wainscotUpg   = 0;
    state.win12         = 0;
    state.s2s           = 0;
    state.s2d           = 0;
    state.punchAmt      = 2500;
    state.customCharges = [];
    state.awnQty        = 0;
    state.cupQty        = 0;
    state.chimQty       = 0;
    state.detShop       = 0;
    state.deckShown     = 0;

    syncPlanMetrics(state);
  }

  // Derive the legacy metrics values from the new plans fields so that
  // the existing exterior/concrete/interior calc functions keep working.
  function syncPlanMetrics(state) {
    var livSF = 0, garSF = 0, porSF = 0, totRoof = 0;
    state.slab.forEach(function (s) {
      var n = s.n;
      if (n === "1st Floor Living Area" || n === "2nd Floor Area" || n === "Bonus Room") livSF += s.sf;
      else if (n === "Garage Area") garSF += s.sf;
      else if (n === "Front Porch Area" || n === "Back Porch Area") porSF += s.sf;
    });
    state.roof.forEach(function (r) { totRoof += r.sf; });

    state.metrics.livingSF  = livSF;
    state.metrics.garageSF  = garSF;
    state.metrics.porchSF   = porSF;
    state.metrics.slabSF    = livSF + garSF + porSF;
    state.metrics.roofSF    = totRoof;
    state.metrics.extWallSF = state.wallTuff;
    state.metrics.windows   = state.sglW + state.dblW + state.s2s + state.s2d;
    state.metrics.extDoors  = state.dblD + state.sglD;
    state.metrics = recomputeMetrics(state.metrics);
  }

  function calcExterior(state, region, wd) {
    var mult  = S.parseNumber(region.laborMultiplier) || 1;
    var lines = [];
    var total = 0;
    wd.rateCard.forEach(function (item) {
      if (item.category !== "exterior") return;
      var qty  = item.metric === "flat" ? 1 : S.parseNumber(state.metrics[item.metric]);
      var cost = Math.round(qty * S.parseNumber(item.rate) * mult);
      if (cost > 0) {
        lines.push({ label: item.label, quantity: qty, rate: S.parseNumber(item.rate), cost: cost, unit: item.unit });
        total += cost;
      }
    });
    var custPrice = Math.round(S.parseNumber(state.metrics.slabSF) * 12);
    var margin    = custPrice ? Math.round((1 - total / custPrice) * 100) : 0;
    return { lines: lines, total: total, customerPrice: custPrice, margin: margin };
  }

  function calcConcrete(state, region) {
    var slabRate = 8 * (S.parseNumber(region.concreteMultiplier) || 1);
    var concArea = state.concArea || Math.round(S.parseNumber(state.metrics.slabSF));
    var slab     = Math.round(concArea * slabRate);
    var driveway = 3600, walkway = 900, gradeBeam = 4200;

    var addons = 0;
    if (state.concLp)    addons += 1750;
    if (state.concBp)    addons += 2500;
    if (state.concWire  && concArea > 0) addons += Math.round(concArea * 0.85);
    if (state.concRebar && concArea > 0) addons += Math.round(concArea * 1.25);
    if (state.concFoam  > 0) addons += Math.round(S.parseNumber(state.concFoam) * 9);
    if (state.concCustomCharges) {
      state.concCustomCharges.forEach(function (cc) {
        addons += Math.round(S.parseNumber(cc.qty) * S.parseNumber(cc.rate));
      });
    }

    return { slabRate: slabRate, slab: slab, driveway: driveway, walkway: walkway, gradeBeam: gradeBeam, addons: addons, total: slab + driveway + walkway + gradeBeam + addons };
  }

  function calcInterior(state, region, wd, model) {
    var byGroup = {};
    var trueCost = 0;
    wd.rateCard.forEach(function (item) {
      if (item.category !== "interior") return;
      var qty  = item.metric === "flat" ? 1 : S.parseNumber(state.metrics[item.metric]);
      var cost = Math.round(qty * S.parseNumber(item.rate));
      trueCost += cost;
      byGroup[item.group] = (byGroup[item.group] || 0) + cost;
    });
    var turnkeyRate = S.parseNumber(model && model.turnkeyRate);
    var premium     = S.parseNumber(region.turnkeyPremium);
    var livingSf    = S.parseNumber(model && model.livingSf);
    var contract    = Math.round(livingSf * (turnkeyRate + premium));
    var margin      = contract ? Math.round((1 - trueCost / contract) * 100) : 0;
    return { byGroup: byGroup, trueCost: trueCost, contract: contract, margin: margin };
  }

  function calcTotals(state, region, wd, model) {
    var exterior     = calcExterior(state, region, wd);
    var concrete     = calcConcrete(state, region);
    var interior     = calcInterior(state, region, wd, model);
    var upgradesTotal = state.upgrades.reduce(function (t, u) { return t + S.parseNumber(u.amount); }, 0);
    var p10          = S.parseNumber(state.p10);
    var contractTotal = p10 + concrete.total + exterior.total + interior.contract + upgradesTotal;

    var deposit = 2500;
    var first   = Math.max(p10 - deposit, 0);
    var second  = concrete.total;
    var third   = exterior.total;
    var fourth  = Math.round(contractTotal * 0.2);
    var fifth   = Math.round(contractTotal * 0.2);
    var sixth   = contractTotal - deposit - first - second - third - fourth - fifth;

    return {
      exterior: exterior, concrete: concrete, interior: interior,
      upgradesTotal: upgradesTotal, p10: p10, contractTotal: contractTotal,
      draws: [deposit, first, second, third, fourth, fifth, sixth]
    };
  }

  // ── Wizard stepper ────────────────────────────────────────────────────────
  function updateStepper(step) {
    STEP_LABELS.forEach(function (_, i) {
      var dot  = S.$id("sdot-"  + i);
      var line = S.$id("sline-" + i);
      if (!dot) return;
      dot.classList.remove("done", "current", "todo");
      if (i < step) {
        dot.classList.add("done");
        dot.textContent = "\u2713";
      } else if (i === step) {
        dot.classList.add("current");
        dot.textContent = String(i + 1);
      } else {
        dot.classList.add("todo");
        dot.textContent = String(i + 1);
      }
      if (line) {
        line.classList.toggle("done", i < step);
      }
    });
    S.setText("step-caption-label", STEP_LABELS[step] || "");
    S.setText("step-caption-count", "Step " + (step + 1) + " / " + STEP_LABELS.length);
  }

  // ── Step panel show/hide ──────────────────────────────────────────────────
  function showStep(step) {
    STEP_IDS.forEach(function (id, i) {
      var el = S.$id(id);
      if (el) el.style.display = i === step ? "" : "none";
    });
    var prev    = S.$id("sw-prev");
    var next    = S.$id("sw-next");
    var restart = S.$id("sw-restart");
    if (prev)    prev.style.display    = step > 0 ? "" : "none";
    if (next)    next.style.display    = step < 6 ? "" : "none";
    if (restart) restart.style.display = step === 6 ? "" : "none";
    if (next) next.disabled = (step === 0 && !wizardState.modelId);
  }

  // ── Fill helpers ──────────────────────────────────────────────────────────
  function fillStepModel(state, wd, region) {
    var sel = S.$id("sw-model-select");
    if (sel) {
      sel.innerHTML = wd.models.map(function (m) {
        var sel_ = m.id === state.modelId ? " selected" : "";
        return "<option value=\"" + S.escapeHtml(m.id) + "\"" + sel_ + ">" +
          S.escapeHtml(m.name + " – " + S.parseNumber(m.livingSf).toLocaleString() + " SF") +
          "</option>";
      }).join("");
    }
    var custInput = S.$id("sw-customer");
    if (custInput) custInput.value = state.customerName || "";
    var orderInput  = S.$id("sw-order");
    if (orderInput)  orderInput.value  = state.orderNumber  || "";
    var addrInput   = S.$id("sw-address");
    if (addrInput)   addrInput.value   = state.address      || "";
    var repInput    = S.$id("sw-salesrep");
    if (repInput)    repInput.value    = state.salesRep     || "";

    var model = S.findById(wd.models, state.modelId);
    var kpis  = S.$id("model-kpis");
    if (model && kpis) {
      kpis.style.display = "";
      var turnkey = S.parseNumber(model.turnkeyRate) + S.parseNumber(region.turnkeyPremium);
      S.setText("kpi-living-sf",  S.parseNumber(model.livingSf).toLocaleString());
      S.setText("kpi-turnkey-sf", "$" + turnkey.toFixed(2));
      S.setText("kpi-region",     region.name || "");
    } else if (kpis) {
      kpis.style.display = "none";
    }
  }

  function fillStepMetrics(state) {
    // ── Foundation ───────────────────────────────────────────────────────
    var ftConcrete = S.$id("pm-ft-concrete");
    var ftCrawl    = S.$id("pm-ft-crawl");
    if (ftConcrete) ftConcrete.checked = (state.foundType !== "crawl");
    if (ftCrawl)    ftCrawl.checked    = (state.foundType === "crawl");
    var crawlExtra = S.$id("pm-crawl-extra");
    if (crawlExtra) crawlExtra.style.display = state.foundType === "crawl" ? "" : "none";
    var bfYes = S.$id("pm-bf-yes");
    var bfNo  = S.$id("pm-bf-no");
    if (bfYes) bfYes.checked = (state.bsmtFrame === 1);
    if (bfNo)  bfNo.checked  = (state.bsmtFrame !== 1);
    var crawlSFEl = S.$id("pm-crawl-sf");
    if (crawlSFEl) crawlSFEl.value = state.crawlSF || state.metrics.livingSF || "";

    // ── Stories ──────────────────────────────────────────────────────────
    var storiesSel = S.$id("pm-stories");
    if (storiesSel) storiesSel.value = String(state.stories);

    // ── Slab & roof dynamic rows ─────────────────────────────────────────
    renderSlabBody(state);
    renderRoofBody(state);
    updatePlanSummaries(state);

    // ── Ext wall ─────────────────────────────────────────────────────────
    document.querySelectorAll("input[name='pm-wt']").forEach(function (r) {
      r.checked = (r.value === state.wallType);
    });
    var wtEl = S.$id("pm-wall-tuff");
    if (wtEl) wtEl.value = state.wallTuff || "";
    var wainEl = S.$id("pm-wainscot");
    if (wainEl) wainEl.value = state.wainscotUpg ? "1" : "0";
    var wainExtra = S.$id("pm-wainscot-extra");
    if (wainExtra) wainExtra.style.display = state.wainscotUpg ? "" : "none";
    var rockEl  = S.$id("pm-wall-rock");
    var stoneEl = S.$id("pm-wall-stone");
    if (rockEl)  rockEl.value  = state.wallRock  || "";
    if (stoneEl) stoneEl.value = state.wallStone || "";
    var stoneUpgSel = S.$id("pm-stone-upg");
    if (stoneUpgSel) stoneUpgSel.value = state.stoneUpg ? "1" : "0";
    var stoneRow = S.$id("pm-stone-upg-row");
    if (stoneRow) stoneRow.style.display = state.stoneUpg ? "" : "none";

    // ── Window steppers ──────────────────────────────────────────────────
    S.setText("pm-sglw-qty", state.sglW);
    S.setText("pm-dblw-qty", state.dblW);
    var win12Sel = S.$id("pm-win12");
    if (win12Sel) win12Sel.value = state.win12 ? "1" : "0";
    var win12Extra = S.$id("pm-win12-extra");
    if (win12Extra) win12Extra.style.display = state.win12 ? "" : "none";
    S.setText("pm-s2s-qty", state.s2s);
    S.setText("pm-s2d-qty", state.s2d);

    // ── Door steppers ────────────────────────────────────────────────────
    S.setText("pm-dbld-qty", state.dblD);
    S.setText("pm-sgld-qty", state.sglD);

    // ── Punch & custom ───────────────────────────────────────────────────
    var punchEl = S.$id("pm-punch");
    if (punchEl) punchEl.value = state.punchAmt || 2500;
    S.setText("pm-punch-cost", "$" + Math.round(state.punchAmt || 2500).toLocaleString());
    renderCustomBody(state);

    // ── Additional ───────────────────────────────────────────────────────
    S.setText("pm-awn-qty",  state.awnQty);
    S.setText("pm-cup-qty",  state.cupQty);
    S.setText("pm-chim-qty", state.chimQty);
    var awnCostEl  = S.$id("pm-awn-cost");
    var cupCostEl  = S.$id("pm-cup-cost");
    var chimCostEl = S.$id("pm-chim-cost");
    if (awnCostEl)  { awnCostEl.textContent  = state.awnQty  ? "$" + (state.awnQty  * 450).toLocaleString()  : "—"; awnCostEl.className  = "upg-cost" + (state.awnQty  ? " active" : ""); }
    if (cupCostEl)  { cupCostEl.textContent  = state.cupQty  ? "$" + (state.cupQty  * 250).toLocaleString()  : "—"; cupCostEl.className  = "upg-cost" + (state.cupQty  ? " active" : ""); }
    if (chimCostEl) { chimCostEl.textContent = state.chimQty ? "$" + (state.chimQty * 1500).toLocaleString() : "—"; chimCostEl.className = "upg-cost" + (state.chimQty ? " active" : ""); }
    var detShopEl  = S.$id("pm-det-shop");
    var deckEl     = S.$id("pm-deck-shown");
    if (detShopEl) detShopEl.value  = state.detShop  ? "1" : "0";
    if (deckEl)    deckEl.value     = state.deckShown ? "1" : "0";

    // ── Roof global options ──────────────────────────────────────────────
    var sheathEl = S.$id("pm-sheath");
    var g26El    = S.$id("pm-g26");
    if (sheathEl) sheathEl.checked = !!state.sheath;
    if (g26El)    g26El.checked    = !!state.g26;

    // ── Interior metrics ─────────────────────────────────────────────────
    var intEditable = ["cabLF","intDoors","fixtures","soffitLF","beamLF"];
    intEditable.forEach(function (key) {
      S.setValue("m-" + key, Math.round(S.parseNumber(state.metrics[key])));
    });
    S.setText("m-counterSF", Math.round(S.parseNumber(state.metrics.counterSF)).toLocaleString());
    S.setText("m-hvacTons",  Math.round(S.parseNumber(state.metrics.hvacTons)));
  }

  // ── Dynamic row renderers ─────────────────────────────────────────────────
  function makeSelectOptions(arr, selected) {
    return arr.map(function (v) {
      return "<option value=\"" + S.escapeHtml(v) + "\"" + (v === selected ? " selected" : "") + ">" + S.escapeHtml(v) + "</option>";
    }).join("");
  }

  function renderSlabBody(state) {
    var body = S.$id("pm-slab-body");
    if (!body) return;
    body.innerHTML = state.slab.map(function (s, i) {
      var isPorch = (s.n === "Front Porch Area" || s.n === "Back Porch Area");
      var tgCell  = isPorch
        ? "<select class=\"slab-tg-select\" data-i=\"" + i + "\"><option value=\"0\"" + (s.tg ? "" : " selected") + ">No</option><option value=\"1\"" + (s.tg ? " selected" : "") + ">Yes</option></select>"
        : "<span style=\"text-align:center;font-size:11px;color:var(--text-soft)\">—</span>";
      return "<div class=\"sched-row\">" +
        "<select class=\"slab-area-select\" data-i=\"" + i + "\">" + makeSelectOptions(SLAB_AREAS, s.n) + "</select>" +
        "<input type=\"number\" class=\"slab-sf-input\" data-i=\"" + i + "\" value=\"" + (s.sf || "") + "\" />" +
        tgCell +
        "<button type=\"button\" class=\"del-btn slab-del\" data-i=\"" + i + "\">\u00D7</button>" +
        "</div>";
    }).join("");
  }

  function renderRoofBody(state) {
    var body = S.$id("pm-roof-body");
    if (!body) return;
    body.innerHTML = state.roof.map(function (r, i) {
      var typeOpts = [
        "<option value=\"metal\""    + (r.type === "metal"    ? " selected" : "") + ">Metal</option>",
        "<option value=\"ss\""       + (r.type === "ss"       ? " selected" : "") + ">Standing Seam</option>",
        "<option value=\"shingles\"" + (r.type === "shingles" ? " selected" : "") + ">Shingles</option>"
      ].join("");
      var pitchOpts =
        "<option value=\"0\"" + (!r.steep ? " selected" : "") + ">7/12 or Under</option>" +
        "<option value=\"1\"" + (r.steep  ? " selected" : "") + ">8/12 or Greater</option>";
      return "<div class=\"roof-sched-row\">" +
        "<select class=\"roof-area-select\" data-i=\"" + i + "\">" + makeSelectOptions(ROOF_AREAS, r.n) + "</select>" +
        "<select class=\"roof-type-select\" data-i=\"" + i + "\">" + typeOpts + "</select>" +
        "<select class=\"roof-pitch-select\" data-i=\"" + i + "\">" + pitchOpts + "</select>" +
        "<input type=\"number\" class=\"roof-sf-input\" data-i=\"" + i + "\" value=\"" + (r.sf || "") + "\" />" +
        "<button type=\"button\" class=\"del-btn roof-del\" data-i=\"" + i + "\">\u00D7</button>" +
        "</div>";
    }).join("");

    // Roof summary boxes
    var summary = S.$id("pm-roof-summary");
    if (summary) {
      summary.innerHTML = state.roof.map(function (r) {
        var label = r.n + (r.type !== "metal" ? " \u2022 " + (r.type === "ss" ? "SS" : "Shingles") : "");
        return "<div class=\"sqft-box\"><div class=\"sqft-val\">" + Math.round(r.sf).toLocaleString() + "</div><div class=\"sqft-lbl\">" + S.escapeHtml(label) + "</div></div>";
      }).join("");
      var cols = Math.min(state.roof.length, 4);
      summary.style.gridTemplateColumns = "repeat(" + cols + ", 1fr)";
    }
  }

  function renderConcCustomBody(state) {
    var body = S.$id("c-custom-body");
    if (!body) return;
    if (!state.concCustomCharges.length) { body.innerHTML = ""; return; }
    body.innerHTML = state.concCustomCharges.map(function (cc, ci) {
      var cost = S.parseNumber(cc.qty) * S.parseNumber(cc.rate);
      return "<div class=\"custom-charge-row\" data-ci=\"" + ci + "\">" +
        "<input type=\"text\"   class=\"conc-cc-desc\" data-ci=\"" + ci + "\" placeholder=\"Description\" value=\"" + S.escapeHtml(cc.desc || "") + "\" />" +
        "<span class=\"custom-charge-lbl\">Rate</span>" +
        "<input type=\"number\" class=\"conc-cc-rate\" data-ci=\"" + ci + "\" placeholder=\"0\" value=\"" + (cc.rate || "") + "\" />" +
        "<span class=\"custom-charge-lbl\">Unit</span>" +
        "<select class=\"conc-cc-unit\" data-ci=\"" + ci + "\">" +
          "<option value=\"SF\"" + (cc.unit === "SF"  ? " selected" : "") + ">SF</option>" +
          "<option value=\"LF\"" + (cc.unit === "LF"  ? " selected" : "") + ">LF</option>" +
          "<option value=\"ea\"" + (cc.unit === "ea"  ? " selected" : "") + ">Each</option>" +
        "</select>" +
        "<span class=\"custom-charge-lbl\">Qty</span>" +
        "<input type=\"number\" class=\"conc-cc-qty\"  data-ci=\"" + ci + "\" placeholder=\"0\" value=\"" + (cc.qty || "") + "\" />" +
        "<span class=\"upg-cost" + (cost > 0 ? " active" : "") + "\">" + (cost > 0 ? "$" + Math.round(cost).toLocaleString() : "—") + "</span>" +
        "<button type=\"button\" class=\"del-btn conc-cc-del\" data-ci=\"" + ci + "\">\u00D7</button>" +
        "</div>";
    }).join("");
  }

  function renderConcSummaryBody(state) {
    var body = S.$id("c-summary-body");
    if (!body) return;
    var rows = "";
    if (state.concLp)   rows += "<div class=\"rw\"><span class=\"rl\">Line pump</span><span class=\"rv\">$1,750</span></div>";
    if (state.concBp)   rows += "<div class=\"rw\"><span class=\"rl\">Boom pump</span><span class=\"rv\">$2,500</span></div>";
    if (state.concArea > 0) {
      if (state.concWire)  rows += "<div class=\"rw\"><span class=\"rl\">Wire</span><span class=\"rd\">" + Math.round(state.concArea).toLocaleString() + " SF × $0.85</span><span class=\"rv\">" + S.formatMoney(state.concArea * 0.85) + "</span></div>";
      if (state.concRebar) rows += "<div class=\"rw\"><span class=\"rl\">Rebar</span><span class=\"rd\">" + Math.round(state.concArea).toLocaleString() + " SF × $1.25</span><span class=\"rv\">" + S.formatMoney(state.concArea * 1.25) + "</span></div>";
    }
    if (state.concFoam > 0) rows += "<div class=\"rw\"><span class=\"rl\">2\" foam perimeter</span><span class=\"rd\">" + Math.round(state.concFoam).toLocaleString() + " LF × $9.00</span><span class=\"rv\">" + S.formatMoney(state.concFoam * 9) + "</span></div>";
    state.concCustomCharges.forEach(function (cc) {
      var cost = S.parseNumber(cc.qty) * S.parseNumber(cc.rate);
      if (cost > 0) rows += "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(cc.desc || "Custom") + "</span><span class=\"rd\">" + S.parseNumber(cc.qty).toLocaleString() + " " + (cc.unit || "SF") + " × $" + S.parseNumber(cc.rate).toFixed(2) + "</span><span class=\"rv\">" + S.formatMoney(cost) + "</span></div>";
    });
    body.innerHTML = rows;
  }

  function renderConcrete(state, totals) {
    var c = totals.concrete;
    var slabSF = Math.round(state.metrics.slabSF);
    var concArea = state.concArea || slabSF;

    // Area hint & button
    var hint = S.$id("c-area-hint");
    var useBtn = S.$id("c-use-slab-btn");
    var areaEl = S.$id("c-area");
    if (hint)   hint.textContent = slabSF > 0 && concArea !== slabSF ? "Slab total is " + slabSF.toLocaleString() + " SF" : "";
    if (useBtn) useBtn.style.display = slabSF > 0 && !state.concArea ? "" : "none";
    if (areaEl && document.activeElement !== areaEl) areaEl.value = state.concArea || "";

    // Type
    var typeEl = S.$id("c-type");
    if (typeEl && document.activeElement !== typeEl) typeEl.value = state.concType || "";

    // Zone
    var zoneEl = S.$id("c-zone");
    if (zoneEl && document.activeElement !== zoneEl) zoneEl.value = String(state.concZone || 1);

    // Checkboxes
    var lpEl    = S.$id("c-lp");    if (lpEl)    lpEl.checked    = !!state.concLp;
    var bpEl    = S.$id("c-bp");    if (bpEl)    bpEl.checked    = !!state.concBp;
    var wireEl  = S.$id("c-wire");  if (wireEl)  wireEl.checked  = !!state.concWire;
    var rebarEl = S.$id("c-rebar"); if (rebarEl) rebarEl.checked = !!state.concRebar;
    var foamEl  = S.$id("c-foam");  if (foamEl && document.activeElement !== foamEl) foamEl.value = state.concFoam || "";

    // Cost badges
    S.setText("c-lp-cost",   state.concLp   ? "$1,750" : "—");
    S.setText("c-bp-cost",   state.concBp   ? "$2,500" : "—");
    S.setText("c-wire-cost",  state.concWire  && concArea > 0 ? S.formatMoney(concArea * 0.85) : "—");
    S.setText("c-rebar-cost", state.concRebar && concArea > 0 ? S.formatMoney(concArea * 1.25) : "—");
    S.setText("c-foam-cost",  state.concFoam  > 0             ? S.formatMoney(state.concFoam * 9) : "—");

    // Slab row
    S.setText("c-slab-detail", S.formatCount(state.metrics.slabSF) + " SF × $" + c.slabRate.toFixed(2));
    S.setText("c-slab-cost",   S.formatMoney(c.slab));

    renderConcCustomBody(state);
    renderConcSummaryBody(state);

    // Total comes directly from calcConcrete (which already includes all addons)
    S.setText("c-total", S.formatMoney(c.total));
  }

  function renderCustomBody(state) {
    var body = S.$id("pm-custom-body");
    if (!body) return;
    if (!state.customCharges.length) { body.innerHTML = ""; return; }
    body.innerHTML = state.customCharges.map(function (cc, ci) {
      var cost = S.parseNumber(cc.qty) * S.parseNumber(cc.rate);
      return "<div class=\"custom-charge-row\" data-ci=\"" + ci + "\">" +
        "<input type=\"text\"   class=\"cc-desc\" data-ci=\"" + ci + "\" placeholder=\"Description\" value=\"" + S.escapeHtml(cc.desc || "") + "\" />" +
        "<span class=\"custom-charge-lbl\">Rate</span>" +
        "<input type=\"number\" class=\"cc-rate\" data-ci=\"" + ci + "\" placeholder=\"0\" value=\"" + (cc.rate || "") + "\" />" +
        "<span class=\"custom-charge-lbl\">Unit</span>" +
        "<select class=\"cc-unit\" data-ci=\"" + ci + "\">" +
          "<option value=\"SF\"" +  (cc.unit === "SF"  ? " selected" : "") + ">SF</option>" +
          "<option value=\"LF\"" +  (cc.unit === "LF"  ? " selected" : "") + ">LF</option>" +
          "<option value=\"ea\"" +  (cc.unit === "ea"  ? " selected" : "") + ">Each</option>" +
        "</select>" +
        "<span class=\"custom-charge-lbl\">Qty</span>" +
        "<input type=\"number\" class=\"cc-qty\"  data-ci=\"" + ci + "\" placeholder=\"0\" value=\"" + (cc.qty || "") + "\" />" +
        "<span class=\"upg-cost" + (cost > 0 ? " active" : "") + "\">" + (cost > 0 ? "$" + Math.round(cost).toLocaleString() : "—") + "</span>" +
        "<button type=\"button\" class=\"del-btn cc-del\" data-ci=\"" + ci + "\">\u00D7</button>" +
        "</div>";
    }).join("");
  }

  function updatePlanSummaries(state) {
    // Slab totals
    var livSF = 0, garSF = 0, porSF = 0, totSlab = 0;
    state.slab.forEach(function (s) {
      totSlab += s.sf;
      var n = s.n;
      if (n === "1st Floor Living Area" || n === "2nd Floor Area" || n === "Bonus Room") livSF += s.sf;
      else if (n === "Garage Area" || n === "Carport Area") garSF += s.sf;
      else if (n === "Front Porch Area" || n === "Back Porch Area") porSF += s.sf;
    });
    S.setText("pm-slab-total", Math.round(totSlab).toLocaleString() + " SF");
    S.setText("pm-sum-living", Math.round(livSF).toLocaleString());
    S.setText("pm-sum-garage", Math.round(garSF).toLocaleString());
    S.setText("pm-sum-porch",  Math.round(porSF).toLocaleString());

    // Roof total
    var totRoof = 0;
    state.roof.forEach(function (r) { totRoof += r.sf; });
    S.setText("pm-roof-total", Math.round(totRoof).toLocaleString() + " SF");

    // Wall totals
    S.setText("pm-wall-total", Math.round(state.wallTuff || 0).toLocaleString() + " SF");
    S.setText("pm-sum-tuff",   Math.round(state.wallTuff || 0).toLocaleString());

    // Window / door counts
    var totalWin  = (state.sglW  || 0) + (state.dblW || 0) + (state.s2s || 0) + (state.s2d || 0);
    var totalDoor = (state.dblD  || 0) + (state.sglD  || 0);
    S.setText("pm-win-total",  totalWin  + " Windows");
    S.setText("pm-door-total", totalDoor + " Doors");
    S.setText("pm-sum-sglw",   state.sglW || 0);
    S.setText("pm-sum-dblw",   state.dblW || 0);
    S.setText("pm-sum-dbld",   state.dblD || 0);
    S.setText("pm-sum-sgld",   state.sglD || 0);
  }

  function fillStepExterior(state, totals) {
    var ext = totals.exterior;
    S.setText("ext-cust-slab-detail", S.formatCount(state.metrics.slabSF) + " SF × $12");
    S.setText("ext-cust-price",  S.formatMoney(ext.customerPrice));
    S.setText("ext-cust-total",  S.formatMoney(ext.customerPrice));
    S.setText("ext-true-cost",   S.formatMoney(ext.total));

    var body = S.$id("ext-lines-body");
    if (body) {
      body.innerHTML = ext.lines.map(function (line) {
        return "<div class=\"rw\">" +
          "<span class=\"rl\">" + S.escapeHtml(line.label) + "</span>" +
          "<span class=\"rd\">" + S.formatCount(line.quantity) + " \u00D7 $" + line.rate + "</span>" +
          "<span class=\"rv\">" + S.formatMoney(line.cost) + "</span>" +
          "</div>";
      }).join("") +
      "<div class=\"rw rt\"><span class=\"rl\">True cost</span><span class=\"rv\">" + S.formatMoney(ext.total) + "</span></div>";
    }

    S.setText("ext-kpi-customer", S.formatMoney(ext.customerPrice));
    S.setText("ext-kpi-truecost", S.formatMoney(ext.total));
    var marginEl = S.$id("ext-kpi-margin");
    if (marginEl) {
      marginEl.textContent = ext.margin + "%";
      marginEl.style.color = ext.margin >= 20 ? "var(--success)" : "var(--brand)";
    }
  }

  function fillStepConcrete(state, totals) {
    renderConcrete(state, totals);
  }

  function fillStepInterior(totals, model, region) {
    var int_ = totals.interior;
    var turnkey = S.parseNumber(model && model.turnkeyRate) + S.parseNumber(region.turnkeyPremium);
    var livingSf = S.parseNumber(model && model.livingSf);
    S.setText("int-sf-detail", S.formatCount(livingSf) + " SF \u00D7 $" + turnkey.toFixed(2));
    S.setText("int-contract",  S.formatMoney(int_.contract));
    S.setText("int-true-cost", S.formatMoney(int_.trueCost));

    var body = S.$id("int-groups-body");
    if (body) {
      body.innerHTML = Object.keys(int_.byGroup)
        .sort(function (a, b) { return int_.byGroup[b] - int_.byGroup[a]; })
        .map(function (group) {
          return "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(group) + "</span>" +
            "<span class=\"rv\">" + S.formatMoney(int_.byGroup[group]) + "</span></div>";
        }).join("") +
        "<div class=\"rw rt\"><span class=\"rl\">Total true cost</span><span class=\"rv\">" + S.formatMoney(int_.trueCost) + "</span></div>";
    }

    S.setText("int-kpi-contract", S.formatMoney(int_.contract));
    S.setText("int-kpi-truecost", S.formatMoney(int_.trueCost));
    var marginEl = S.$id("int-kpi-margin");
    if (marginEl) {
      marginEl.textContent = int_.margin + "%";
      marginEl.style.color = int_.margin >= 20 ? "var(--success)" : "var(--brand)";
    }
  }

  function fillStepUpgrades(state) {
    S.setValue("sw-p10", Math.round(S.parseNumber(state.p10)));
    var total  = state.upgrades.reduce(function (t, u) { return t + S.parseNumber(u.amount); }, 0);
    S.setText("upgrades-total", S.formatMoney(total));

    var body = S.$id("upgrades-body");
    if (body) {
      if (state.upgrades.length) {
        body.innerHTML = state.upgrades.map(function (u) {
          return "<div class=\"rw\"><span class=\"rl\">" + S.escapeHtml(u.description) + "</span>" +
            "<span class=\"rv\">" + S.formatMoney(u.amount) + "</span></div>";
        }).join("");
      } else {
        body.innerHTML = "<div style=\"color:var(--text-soft);font-size:12px;text-align:center;padding:12px\">No upgrades added</div>";
      }
    }
  }

  function fillStepContract(state, totals) {
    S.setText("cont-p10",       S.formatMoney(totals.p10));
    S.setText("cont-concrete",  S.formatMoney(totals.concrete.total));
    S.setText("cont-exterior",  S.formatMoney(totals.exterior.total));
    S.setText("cont-interior",  S.formatMoney(totals.interior.contract));
    S.setText("cont-upgrades",  S.formatMoney(totals.upgradesTotal));
    S.setText("cont-total",     S.formatMoney(totals.contractTotal));
    S.setText("cont-banner",    S.formatMoney(totals.contractTotal));
    S.setText("cont-customer",  state.customerName || "Customer");

    totals.draws.forEach(function (amount, i) {
      S.setText("draw-" + i, S.formatMoney(amount));
    });
    S.setText("draw-total", S.formatMoney(totals.contractTotal));
  }

  // ── Master wizard update ──────────────────────────────────────────────────
  function updateWizard(salesData) {
    var wd     = getWizardData(salesData);
    var region = S.getSessionRegion();
    var model  = S.findById(wd.models, wizardState.modelId);
    var totals = calcTotals(wizardState, region, wd, model);
    var step   = wizardState.step;

    updateStepper(step);
    showStep(step);

    if (step === 0) fillStepModel(wizardState, wd, region);
    if (step === 1) fillStepMetrics(wizardState);
    if (step === 2) fillStepExterior(wizardState, totals);
    if (step === 3) fillStepConcrete(wizardState, totals);
    if (step === 4) fillStepInterior(totals, model, region);
    if (step === 5) fillStepUpgrades(wizardState);
    if (step === 6) fillStepContract(wizardState, totals);
  }

  // ── Wizard event bindings ─────────────────────────────────────────────────
  function bindWizardEvents(salesData) {
    var modelSel = S.$id("sw-model-select");
    if (modelSel) {
      modelSel.addEventListener("change", function () {
        var wd = getWizardData(salesData);
        var m  = S.findById(wd.models, modelSel.value);
        wizardState.modelId  = modelSel.value;
        wizardState.metrics  = initMetrics(m);
        wizardState.upgrades = [];
        wizardState.p10      = Math.round(S.parseNumber(m && m.materialTotal) * 1.1);
        loadModelPlans(m && m.name, wizardState);
        updateWizard(salesData);
      });
    }

    var custInput = S.$id("sw-customer");
    if (custInput) {
      custInput.addEventListener("input", function () {
        wizardState.customerName = custInput.value;
      });
    }
    var orderInput = S.$id("sw-order");
    if (orderInput) {
      orderInput.addEventListener("input", function () {
        wizardState.orderNumber = orderInput.value;
      });
    }
    var addrInput = S.$id("sw-address");
    if (addrInput) {
      addrInput.addEventListener("input", function () {
        wizardState.address = addrInput.value;
      });
    }
    var repInput = S.$id("sw-salesrep");
    if (repInput) {
      repInput.addEventListener("input", function () {
        wizardState.salesRep = repInput.value;
      });
    }

    // Metric inputs are now handled by bindPlanEvents

    var p10inp = S.$id("sw-p10");
    if (p10inp) {
      p10inp.addEventListener("input", function () {
        wizardState.p10 = S.parseNumber(p10inp.value);
      });
    }

    var addUpgradeBtn = S.$id("sw-add-upgrade");
    if (addUpgradeBtn) {
      addUpgradeBtn.addEventListener("click", function () {
        var wd = getWizardData(salesData);
        var remaining = wd.upgrades.filter(function (u) {
          return !wizardState.upgrades.some(function (e) { return e.description === u.description; });
        });
        if (!remaining.length) { S.showToast("All preset upgrades already added."); return; }
        wizardState.upgrades.push(remaining[0]);
        S.showToast("Added: " + remaining[0].description);
        fillStepUpgrades(wizardState);
      });
    }

    var prevBtn    = S.$id("sw-prev");
    var nextBtn    = S.$id("sw-next");
    var restartBtn = S.$id("sw-restart");

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        wizardState.step = Math.max(0, wizardState.step - 1);
        updateWizard(salesData);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (!wizardState.modelId) { S.showToast("Select a model first."); return; }
        wizardState.metrics = recomputeMetrics(wizardState.metrics);
        wizardState.step = Math.min(6, wizardState.step + 1);
        updateWizard(salesData);
      });
    }
    if (restartBtn) {
      restartBtn.addEventListener("click", function () {
        wizardState = createWizardState(salesData);
        updateWizard(salesData);
      });
    }

    var genBtn = S.$id("sw-generate");
    if (genBtn) {
      genBtn.addEventListener("click", function () {
        genBtn.disabled = true;
        genBtn.textContent = "Generating…";

        // Resolve model name from the current wizard state
        var wd      = getWizardData(salesData);
        var model   = S.findById(wd.models, wizardState.modelId);
        var modelName = model ? model.name : "";
        var region  = (salesData.regions || [{ laborMultiplier: 1, concreteMultiplier: 1 }])[0];
        var concMult = S.parseNumber(region.concreteMultiplier) || 1;
        var concArea = wizardState.concArea || Math.round(S.parseNumber(wizardState.metrics.slabSF));

        // Build the state payload matching pdf_generator.py expectations
        var payload = {
          pdf_type: "full",
          model:    modelName,
          branch:   "summertown",
          miles:    wizardState.miles || 0,
          custInfo: {
            name:  wizardState.customerName || "",
            addr:  wizardState.address      || "",
            order: wizardState.orderNumber  || "",
            rep:   wizardState.salesRep     || "",
            p10:   S.parseNumber(wizardState.p10) || 0
          },
          slab:          wizardState.slab          || [],
          roof:          wizardState.roof          || [],
          wallTuff:      wizardState.wallTuff       || 0,
          wallRock:      wizardState.wallRock       || 0,
          wallStone:     wizardState.wallStone      || 0,
          wallType:      wizardState.wallType       || "Metal",
          stoneUpg:      wizardState.stoneUpg       || 0,
          wainscotUpg:   wizardState.wainscotUpg    || 0,
          dblD:          wizardState.dblD           || 0,
          sglD:          wizardState.sglD           || 0,
          dblW:          wizardState.dblW           || 0,
          sglW:          wizardState.sglW           || 0,
          s2s:           wizardState.s2s            || 0,
          s2d:           wizardState.s2d            || 0,
          awnQty:        wizardState.awnQty         || 0,
          cupQty:        wizardState.cupQty         || 0,
          chimQty:       wizardState.chimQty        || 0,
          foundType:     wizardState.foundType      || "concrete",
          crawlSF:       wizardState.crawlSF        || 0,
          sheath:        wizardState.sheath         || 0,
          g26:           wizardState.g26            || 0,
          punchAmt:      wizardState.punchAmt       || 2500,
          customCharges:     wizardState.customCharges     || [],
          concCustomCharges: wizardState.concCustomCharges || [],
          ctrOv:         wizardState.ctrOv          || {},
          conc: {
            sqft:  concArea,
            type:  wizardState.concType  || "4fiber",
            zone:  wizardState.concZone  || 1,
            lp:    !!wizardState.concLp,
            bp:    !!wizardState.concBp,
            wire:  !!wizardState.concWire,
            rebar: !!wizardState.concRebar,
            foam:  S.parseNumber(wizardState.concFoam) || 0
          },
          scopeText:    wizardState.scopeText    || "",
          scopeWindows: wizardState.scopeWindows || "",
          scopeDoors:   wizardState.scopeDoors   || ""
        };

        var csrfToken = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";

        fetch("/stmc_ops/api/pdf/ext-labor/", {
          method:  "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken":  csrfToken
          },
          body: JSON.stringify(payload)
        })
        .then(function (response) {
          if (!response.ok) {
            return response.json().then(function (data) {
              throw new Error(data.error || "Server error " + response.status);
            });
          }
          return response.blob();
        })
        .then(function (blob) {
          var slug    = modelName.replace(/\s+/g, "_") || "STMC";
          var filename = "STMC_" + slug + "_Full_Contract.pdf";
          var url  = URL.createObjectURL(blob);
          var link = document.createElement("a");
          link.href = url;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          S.showToast("PDF downloaded.");
        })
        .catch(function (err) {
          S.showToast("PDF error: " + err.message);
        })
        .finally(function () {
          genBtn.disabled = false;
          genBtn.textContent = "Generate PDF";
        });
      });
    }
    var dsBtn  = S.$id("sw-docusign");
    if (dsBtn)  dsBtn.addEventListener("click",  function () { S.showToast("Sent to DocuSign."); });

    bindPlanEvents(salesData);
  }

  // ── Plan tab event bindings ───────────────────────────────────────────────
  function bindPlanEvents(salesData) {

    function refresh() {
      syncPlanMetrics(wizardState);
      if (wizardState.step === 1) fillStepMetrics(wizardState);
    }

    // Foundation
    document.querySelectorAll("input[name='pm-ft']").forEach(function (r) {
      r.addEventListener("change", function () {
        wizardState.foundType = r.value;
        var crawlExtra = S.$id("pm-crawl-extra");
        if (crawlExtra) crawlExtra.style.display = wizardState.foundType === "crawl" ? "" : "none";
        refresh();
      });
    });
    document.querySelectorAll("input[name='pm-bf']").forEach(function (r) {
      r.addEventListener("change", function () { wizardState.bsmtFrame = parseInt(r.value); refresh(); });
    });
    var crawlSFEl = S.$id("pm-crawl-sf");
    if (crawlSFEl) crawlSFEl.addEventListener("change", function () { wizardState.crawlSF = S.parseNumber(this.value); refresh(); });

    // Stories
    var storiesSel = S.$id("pm-stories");
    if (storiesSel) storiesSel.addEventListener("change", function () { wizardState.stories = parseFloat(this.value); refresh(); });

    // Slab body — event delegation
    var slabBody = S.$id("pm-slab-body");
    if (slabBody) {
      slabBody.addEventListener("change", function (e) {
        var t = e.target, i = parseInt(t.getAttribute("data-i"));
        if (isNaN(i)) return;
        if (t.classList.contains("slab-area-select")) {
          wizardState.slab[i].n = t.value;
          var isPorch = (t.value === "Front Porch Area" || t.value === "Back Porch Area");
          if (!isPorch) wizardState.slab[i].tg = 0;
          renderSlabBody(wizardState);
        }
        if (t.classList.contains("slab-sf-input")) { wizardState.slab[i].sf = S.parseNumber(t.value); }
        if (t.classList.contains("slab-tg-select")) { wizardState.slab[i].tg = parseInt(t.value); }
        refresh();
        updatePlanSummaries(wizardState);
      });
      slabBody.addEventListener("click", function (e) {
        if (e.target.classList.contains("slab-del")) {
          var i = parseInt(e.target.getAttribute("data-i"));
          if (wizardState.slab.length > 1) {
            wizardState.slab.splice(i, 1);
            renderSlabBody(wizardState);
            refresh();
            updatePlanSummaries(wizardState);
          }
        }
      });
    }
    var slabAddBtn = S.$id("pm-slab-add");
    if (slabAddBtn) slabAddBtn.addEventListener("click", function () {
      wizardState.slab.push({ n: "Custom", sf: 0, tg: 0 });
      renderSlabBody(wizardState);
      updatePlanSummaries(wizardState);
    });

    // Roof body — event delegation
    var roofBody = S.$id("pm-roof-body");
    if (roofBody) {
      roofBody.addEventListener("change", function (e) {
        var t = e.target, i = parseInt(t.getAttribute("data-i"));
        if (isNaN(i)) return;
        if (t.classList.contains("roof-area-select"))  wizardState.roof[i].n     = t.value;
        if (t.classList.contains("roof-type-select"))  wizardState.roof[i].type  = t.value;
        if (t.classList.contains("roof-pitch-select")) wizardState.roof[i].steep = parseInt(t.value);
        if (t.classList.contains("roof-sf-input"))     wizardState.roof[i].sf    = S.parseNumber(t.value);
        refresh();
        renderRoofBody(wizardState);
        updatePlanSummaries(wizardState);
      });
      roofBody.addEventListener("click", function (e) {
        if (e.target.classList.contains("roof-del")) {
          var i = parseInt(e.target.getAttribute("data-i"));
          if (wizardState.roof.length > 1) {
            wizardState.roof.splice(i, 1);
            renderRoofBody(wizardState);
            refresh();
            updatePlanSummaries(wizardState);
          }
        }
      });
    }
    var roofAddBtn = S.$id("pm-roof-add");
    if (roofAddBtn) roofAddBtn.addEventListener("click", function () {
      wizardState.roof.push({ n: "House Roof", sf: 0, steep: 0, type: "metal" });
      renderRoofBody(wizardState);
      updatePlanSummaries(wizardState);
    });

    // Roof options
    var sheathEl = S.$id("pm-sheath");
    var g26El    = S.$id("pm-g26");
    if (sheathEl) sheathEl.addEventListener("change", function () { wizardState.sheath = this.checked ? 1 : 0; refresh(); });
    if (g26El)    g26El.addEventListener("change",    function () { wizardState.g26    = this.checked ? 1 : 0; refresh(); });

    // Ext wall
    document.querySelectorAll("input[name='pm-wt']").forEach(function (r) {
      r.addEventListener("change", function () { wizardState.wallType = r.value; refresh(); });
    });
    var wallTuffEl = S.$id("pm-wall-tuff");
    if (wallTuffEl) wallTuffEl.addEventListener("change", function () {
      wizardState.wallTuff = S.parseNumber(this.value);
      updatePlanSummaries(wizardState);
      refresh();
    });
    var wainSel = S.$id("pm-wainscot");
    if (wainSel) wainSel.addEventListener("change", function () {
      wizardState.wainscotUpg = parseInt(this.value);
      var wainExtra = S.$id("pm-wainscot-extra");
      if (wainExtra) wainExtra.style.display = wizardState.wainscotUpg ? "" : "none";
      if (!wizardState.wainscotUpg) { wizardState.wallRock = 0; wizardState.wallStone = 0; }
      refresh();
    });
    var rockEl  = S.$id("pm-wall-rock");
    var stoneEl = S.$id("pm-wall-stone");
    if (rockEl)  rockEl.addEventListener("change",  function () { wizardState.wallRock  = S.parseNumber(this.value); refresh(); });
    if (stoneEl) stoneEl.addEventListener("change", function () { wizardState.wallStone = S.parseNumber(this.value); refresh(); });
    var stoneUpgSel = S.$id("pm-stone-upg");
    if (stoneUpgSel) stoneUpgSel.addEventListener("change", function () {
      wizardState.stoneUpg = parseInt(this.value);
      var stoneRow = S.$id("pm-stone-upg-row");
      if (stoneRow) stoneRow.style.display = wizardState.stoneUpg ? "" : "none";
      refresh();
    });
    var stoneSFEl = S.$id("pm-stone-sf");
    if (stoneSFEl) stoneSFEl.addEventListener("change", function () { wizardState.wallStone = S.parseNumber(this.value); refresh(); });

    // Window steppers
    // Steppers
    function bindStepper(decId, incId, qtyId, key) {
      var decBtn = S.$id(decId);
      var incBtn = S.$id(incId);
      if (decBtn) decBtn.addEventListener("click", function () {
        wizardState[key] = Math.max(0, (wizardState[key] || 0) - 1);
        S.setText(qtyId, wizardState[key]);
        refresh();
        updatePlanSummaries(wizardState);
      });
      if (incBtn) incBtn.addEventListener("click", function () {
        wizardState[key] = (wizardState[key] || 0) + 1;
        S.setText(qtyId, wizardState[key]);
        refresh();
        updatePlanSummaries(wizardState);
      });
    }
    bindStepper("pm-sglw-dec", "pm-sglw-inc", "pm-sglw-qty", "sglW");
    bindStepper("pm-dblw-dec", "pm-dblw-inc", "pm-dblw-qty", "dblW");
    bindStepper("pm-s2s-dec",  "pm-s2s-inc",  "pm-s2s-qty",  "s2s");
    bindStepper("pm-s2d-dec",  "pm-s2d-inc",  "pm-s2d-qty",  "s2d");
    bindStepper("pm-dbld-dec", "pm-dbld-inc", "pm-dbld-qty", "dblD");
    bindStepper("pm-sgld-dec", "pm-sgld-inc", "pm-sgld-qty", "sglD");

    // Awning / cupola / chimney steppers (also update cost display)
    function bindCostStepper(decId, incId, qtyId, costId, key, unitCost) {
      var decBtn = S.$id(decId);
      var incBtn = S.$id(incId);
      function updateCost() {
        var qty = wizardState[key] || 0;
        S.setText(qtyId, qty);
        var costEl = S.$id(costId);
        if (costEl) {
          costEl.textContent = qty > 0 ? "$" + (qty * unitCost).toLocaleString() : "—";
          costEl.className   = "upg-cost" + (qty > 0 ? " active" : "");
        }
        refresh();
      }
      if (decBtn) decBtn.addEventListener("click", function () { wizardState[key] = Math.max(0, (wizardState[key] || 0) - 1); updateCost(); });
      if (incBtn) incBtn.addEventListener("click", function () { wizardState[key] = (wizardState[key] || 0) + 1; updateCost(); });
    }
    bindCostStepper("pm-awn-dec",  "pm-awn-inc",  "pm-awn-qty",  "pm-awn-cost",  "awnQty",  450);
    bindCostStepper("pm-cup-dec",  "pm-cup-inc",  "pm-cup-qty",  "pm-cup-cost",  "cupQty",  250);
    bindCostStepper("pm-chim-dec", "pm-chim-inc", "pm-chim-qty", "pm-chim-cost", "chimQty", 1500);

    var win12Sel = S.$id("pm-win12");
    if (win12Sel) win12Sel.addEventListener("change", function () {
      wizardState.win12 = parseInt(this.value);
      var win12Extra = S.$id("pm-win12-extra");
      if (win12Extra) win12Extra.style.display = wizardState.win12 ? "" : "none";
      if (!wizardState.win12) { wizardState.s2s = 0; wizardState.s2d = 0; }
      refresh();
    });

    // Punch
    var punchEl = S.$id("pm-punch");
    if (punchEl) punchEl.addEventListener("change", function () {
      wizardState.punchAmt = Math.max(2500, S.parseNumber(this.value));
      this.value = wizardState.punchAmt;
      S.setText("pm-punch-cost", "$" + Math.round(wizardState.punchAmt).toLocaleString());
    });

    // Custom charges — delegation on custom body
    var customBody = S.$id("pm-custom-body");
    if (customBody) {
      customBody.addEventListener("change", function (e) {
        var t = e.target, ci = parseInt(t.getAttribute("data-ci"));
        if (isNaN(ci)) return;
        if (t.classList.contains("cc-desc")) wizardState.customCharges[ci].desc = t.value;
        if (t.classList.contains("cc-rate")) wizardState.customCharges[ci].rate = S.parseNumber(t.value);
        if (t.classList.contains("cc-unit")) wizardState.customCharges[ci].unit = t.value;
        if (t.classList.contains("cc-qty"))  wizardState.customCharges[ci].qty  = S.parseNumber(t.value);
        renderCustomBody(wizardState);
      });
      customBody.addEventListener("click", function (e) {
        if (e.target.classList.contains("cc-del")) {
          var ci = parseInt(e.target.getAttribute("data-ci"));
          wizardState.customCharges.splice(ci, 1);
          renderCustomBody(wizardState);
        }
      });
    }
    var customAddBtn = S.$id("pm-custom-add");
    if (customAddBtn) customAddBtn.addEventListener("click", function () {
      wizardState.customCharges.push({ desc: "", rate: 0, unit: "SF", qty: 0 });
      renderCustomBody(wizardState);
    });

    // Concrete custom charges
    var concCustomBody = S.$id("c-custom-body");
    if (concCustomBody) {
      concCustomBody.addEventListener("change", function (e) {
        var t = e.target, ci = parseInt(t.getAttribute("data-ci"));
        if (isNaN(ci)) return;
        if (t.classList.contains("conc-cc-desc")) wizardState.concCustomCharges[ci].desc = t.value;
        if (t.classList.contains("conc-cc-rate")) wizardState.concCustomCharges[ci].rate = S.parseNumber(t.value);
        if (t.classList.contains("conc-cc-unit")) wizardState.concCustomCharges[ci].unit = t.value;
        if (t.classList.contains("conc-cc-qty"))  wizardState.concCustomCharges[ci].qty  = S.parseNumber(t.value);
        refreshConc();
      });
      concCustomBody.addEventListener("click", function (e) {
        if (e.target.classList.contains("conc-cc-del")) {
          var ci = parseInt(e.target.getAttribute("data-ci"));
          wizardState.concCustomCharges.splice(ci, 1);
          refreshConc();
        }
      });
    }
    var concAddBtn = S.$id("c-add-custom");
    if (concAddBtn) concAddBtn.addEventListener("click", function () {
      wizardState.concCustomCharges.push({ desc: "", rate: 0, unit: "SF", qty: 0 });
      refreshConc();
    });

    // Concrete configuration inputs
    var cAreaEl  = S.$id("c-area");
    var cTypeEl  = S.$id("c-type");
    var cZoneEl  = S.$id("c-zone");
    var cLpEl    = S.$id("c-lp");
    var cBpEl    = S.$id("c-bp");
    var cWireEl  = S.$id("c-wire");
    var cRebarEl = S.$id("c-rebar");
    var cFoamEl  = S.$id("c-foam");
    var cUseBtn  = S.$id("c-use-slab-btn");

    function refreshConc() {
      updateWizard(salesData);
    }

    if (cAreaEl)  cAreaEl.addEventListener("change",  function () { wizardState.concArea  = S.parseNumber(this.value); refreshConc(); });
    if (cTypeEl)  cTypeEl.addEventListener("change",  function () { wizardState.concType  = this.value; refreshConc(); });
    if (cZoneEl)  cZoneEl.addEventListener("change",  function () { wizardState.concZone  = parseInt(this.value); refreshConc(); });
    if (cLpEl)    cLpEl.addEventListener("change",    function () { wizardState.concLp    = this.checked; if (this.checked) wizardState.concBp = false; refreshConc(); });
    if (cBpEl)    cBpEl.addEventListener("change",    function () { wizardState.concBp    = this.checked; if (this.checked) wizardState.concLp = false; refreshConc(); });
    if (cWireEl)  cWireEl.addEventListener("change",  function () { wizardState.concWire  = this.checked; refreshConc(); });
    if (cRebarEl) cRebarEl.addEventListener("change",  function () { wizardState.concRebar = this.checked; refreshConc(); });
    if (cFoamEl)  cFoamEl.addEventListener("change",  function () { wizardState.concFoam  = S.parseNumber(this.value); refreshConc(); });
    if (cUseBtn)  cUseBtn.addEventListener("click",   function () { wizardState.concArea  = Math.round(wizardState.metrics.slabSF); refreshConc(); });

    // Additional selects
    var detShopEl = S.$id("pm-det-shop");
    var deckEl    = S.$id("pm-deck-shown");
    if (detShopEl) detShopEl.addEventListener("change", function () { wizardState.detShop  = parseInt(this.value); });
    if (deckEl)    deckEl.addEventListener("change",    function () { wizardState.deckShown = parseInt(this.value); });

    // Interior metrics
    document.querySelectorAll(".metric-input[data-metric]").forEach(function (inp) {
      inp.addEventListener("change", function () {
        var key = inp.getAttribute("data-metric");
        wizardState.metrics[key] = S.parseNumber(inp.value);
        wizardState.metrics = recomputeMetrics(wizardState.metrics);
        S.setText("m-counterSF", Math.round(wizardState.metrics.counterSF).toLocaleString());
        S.setText("m-hvacTons",  Math.round(wizardState.metrics.hvacTons));
      });
    });
  }


  function renderProjects(salesData) {
    var container = S.$id("sales-projects-list");
    if (!container) return;
    var projects = salesData.projects || [];
    if (!projects.length) {
      container.innerHTML = "<article class=\"card\"><div class=\"notice\">No active projects.</div></article>";
      return;
    }
    container.innerHTML = projects.map(function (item) {
      var collected  = S.parseNumber(item.collected);
      var remaining  = S.parseNumber(item.remaining);
      var contract   = S.parseNumber(item.contract) || (collected + remaining);
      var pct        = contract > 0 ? Math.round((collected / contract) * 100) : 0;
      var meta       = [item.model, item.client, item.pm ? "PM: " + item.pm : ""].filter(Boolean).join(" – ");

      return "<article class=\"sales-project-card\">" +
        "<div class=\"sales-project-head\">" +
        "<div><h3>" + S.escapeHtml(item.project || "Project") + "</h3>" +
        "<p>" + S.escapeHtml(meta || "Active project") + "</p></div>" +
        "<span class=\"sales-stage " + S.getToneClass(item.stageTone, "") + "\">" + S.escapeHtml(item.stage || "Open") + "</span>" +
        "</div>" +
        "<div class=\"sales-project-stats\">" +
        "<div class=\"sales-project-stat\"><span>Contract</span><strong class=\"mono\">" + S.escapeHtml(item.contract || S.formatMoney(contract)) + "</strong></div>" +
        "<div class=\"sales-project-stat\"><span>Collected</span><strong class=\"mono tone-success\">" + S.escapeHtml(item.collected || S.formatMoney(collected)) + "</strong></div>" +
        "<div class=\"sales-project-stat\"><span>Budget</span><strong class=\"mono\">" + pct + "%</strong></div>" +
        "<div class=\"sales-project-stat\"><span>Remaining</span><strong class=\"mono tone-success\">" + S.escapeHtml(item.remaining || S.formatMoney(remaining)) + "</strong></div>" +
        "</div></article>";
    }).join("");
  }

  // ── Models tab ────────────────────────────────────────────────────────────
  function renderModels(salesData) {
    var container = S.$id("sales-models-list");
    if (!container) return;
    var region  = S.getSessionRegion();
    var wd      = getWizardData(salesData);
    var models  = wd.models.slice().sort(function (a, b) {
      return S.parseNumber(a.livingSf) - S.parseNumber(b.livingSf);
    });

    S.setText("models-region-name", region.name || "");
    S.setText("models-count",       String(models.length));

    container.innerHTML = models.map(function (m) {
      var sf      = S.parseNumber(m.livingSf);
      var turnkey = S.parseNumber(m.turnkeyRate) + S.parseNumber(region.turnkeyPremium);
      var total   = S.parseNumber(m.materialTotal) + S.parseNumber(m.laborBudget) + S.parseNumber(m.concreteBudget) + (sf * turnkey);
      var perSf   = sf > 0 ? Math.round(total / sf) : 0;
      return "<article class=\"card sales-model-row\">" +
        "<div class=\"sales-model-main\">" +
        "<div><h3>" + S.escapeHtml(m.name || "Model") + "</h3><p>" + S.formatCount(sf) + " SF</p></div>" +
        "<div class=\"sales-model-value\"><strong class=\"mono\">" + S.formatMoney(total) + "</strong><span>$" + perSf + "/SF</span></div>" +
        "</div></article>";
    }).join("");
  }

  // ── Rate card tab ─────────────────────────────────────────────────────────
  function renderRateCard(salesData) {
    var region  = S.getSessionRegion();
    var wd      = getWizardData(salesData);
    var rates   = wd.rateCard.map(function (item) {
      return { label: item.label, unit: item.unit, rate: item.rate, category: item.category };
    });

    var extRates = rates.filter(function (r) { return r.category === "exterior"; });
    var intRates = rates.filter(function (r) { return r.category === "interior"; });

    S.setText("rates-meta", (region.name || "") + " \u00B7 " + (salesData.rateCardVersion || "2026-02"));

    function makeRows(list) {
      return list.map(function (item) {
        return "<div class=\"rw rate-row\">" +
          "<span class=\"rl\">" + S.escapeHtml(item.label) + "</span>" +
          "<span class=\"rd mono\">" + S.escapeHtml(item.unit)  + "</span>" +
          "<span class=\"rv\">$" + S.parseNumber(item.rate).toFixed(2) + "</span>" +
          "</div>";
      }).join("");
    }

    var extBody = S.$id("sales-ext-rates");
    var intBody = S.$id("sales-int-rates");
    if (extBody) extBody.innerHTML = makeRows(extRates);
    if (intBody) intBody.innerHTML = makeRows(intRates);
  }

  // ── Login page ────────────────────────────────────────────────────────────
  function initLogin() {
    var users   = S.getCollection("users");
    var regions = S.getCollection("regions");
    var userSel = S.$id("lU");
    var regSel  = S.$id("lR");

    if (userSel) {
      userSel.innerHTML = users.map(function (u) {
        return "<option value=\"" + S.escapeHtml(u.id) + "\">" +
          S.escapeHtml(u.name + " – " + u.title) + "</option>";
      }).join("");
    }
    if (regSel) {
      regSel.innerHTML = regions.map(function (r) {
        return "<option value=\"" + S.escapeHtml(r.id) + "\">" + S.escapeHtml(r.name) + "</option>";
      }).join("");
    }

    var signInBtn = S.$id("signInBtn");
    if (signInBtn) {
      signInBtn.addEventListener("click", function () {
        var userId   = userSel ? userSel.value   : "";
        var regionId = regSel  ? regSel.value    : "";
        var user     = S.findById(users, userId);
        if (!user) return;
        S.setSession(userId, regionId);
        window.location.href = S.getRoleUrl(user.role) || S.getLoginUrl();
      });
    }
  }

  // ── Boot ─────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    var page = document.body.getAttribute("data-page") || "";

    S.loadData()
      .then(function (data) {
        if (page === "login") {
          initLogin();
          return;
        }

        if (page !== "sales") return;

        var user = S.applyHeaderSession();
        if (!user) return;

        S.bindLogout();
        S.bindTabNav();

        var salesData = data.sales || {};

        initPlanData(data.planData);
        wizardState = createWizardState(salesData);
        updateWizard(salesData);
        bindWizardEvents(salesData);
        renderProjects(salesData);
        renderModels(salesData);
        renderRateCard(salesData);
      })
      .catch(function (err) {
        console.error(err);
        S.showLoadError("Unable to load demo data. Check data.json and refresh.");
      });
  });

})();
