// STMC Ops – Sales role JavaScript (sales.js)
// Requires script.js to be loaded first (window.STMC).

(function () {
  var S = window.STMC;

  // ── Wizard state ──────────────────────────────────────────────────────────
  var wizardState = null;
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
      modelId:      def ? def.id : "",
      metrics:      initMetrics(def),
      upgrades:     [],
      p10:          Math.round(S.parseNumber(def && def.materialTotal) * 1.1)
    };
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
    var slab     = Math.round(S.parseNumber(state.metrics.slabSF) * slabRate);
    var driveway = 3600, walkway = 900, gradeBeam = 4200;
    return { slabRate: slabRate, slab: slab, driveway: driveway, walkway: walkway, gradeBeam: gradeBeam, total: slab + driveway + walkway + gradeBeam };
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
    var editable = ["livingSF","garageSF","porchSF","roofSF","extWallSF",
                    "soffitLF","beamLF","cabLF","intDoors","extDoors","windows","fixtures"];
    editable.forEach(function (key) {
      S.setValue("m-" + key, Math.round(S.parseNumber(state.metrics[key])));
    });
    var computed = ["slabSF","counterSF","hvacTons"];
    computed.forEach(function (key) {
      S.setText("m-" + key, Math.round(S.parseNumber(state.metrics[key])).toLocaleString());
    });
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
    var c = totals.concrete;
    S.setText("c-slab-detail", S.formatCount(state.metrics.slabSF) + " SF \u00D7 $" + c.slabRate.toFixed(2));
    S.setText("c-slab-cost",   S.formatMoney(c.slab));
    S.setText("c-total",       S.formatMoney(c.total));
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
        updateWizard(salesData);
      });
    }

    var custInput = S.$id("sw-customer");
    if (custInput) {
      custInput.addEventListener("input", function () {
        wizardState.customerName = custInput.value;
      });
    }

    document.querySelectorAll(".metric-input[data-metric]").forEach(function (inp) {
      inp.addEventListener("change", function () {
        wizardState.metrics[inp.getAttribute("data-metric")] = S.parseNumber(inp.value);
        wizardState.metrics = recomputeMetrics(wizardState.metrics);
        var computed = ["slabSF","counterSF","hvacTons"];
        computed.forEach(function (key) {
          S.setText("m-" + key, Math.round(S.parseNumber(wizardState.metrics[key])).toLocaleString());
        });
      });
    });

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
    if (genBtn) genBtn.addEventListener("click", function () { S.showToast("Contract PDF generated."); });
    var dsBtn  = S.$id("sw-docusign");
    if (dsBtn)  dsBtn.addEventListener("click",  function () { S.showToast("Sent to DocuSign."); });
  }

  // ── Projects tab ──────────────────────────────────────────────────────────
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
