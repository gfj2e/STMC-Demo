// STMC Ops – Model View / Build Wizard landing page (model_view.js)
// Requires script.js (window.STMC) loaded first.

(function () {
  "use strict";
  var S = window.STMC;

  var STEP_LABELS = ["Customer, Model &amp; Scope"];
  var TOTAL_STEPS = STEP_LABELS.length;
  var currentStep = 0;
  var selectedScope = null; // "turnkey" | "shell"

  // ── Progress bar ──────────────────────────────────────────────────────────
  function buildProgressBar() {
    var bar = document.getElementById("mv-progress-bar");
    if (!bar) return;
    var html = "";
    STEP_LABELS.forEach(function (label, i) {
      if (i > 0) html += "<div class=\"wiz-prog-sep\" id=\"mv-sep-" + (i - 1) + "\"></div>";
      html += "<button class=\"wiz-prog-step\" id=\"mv-prog-" + i + "\" type=\"button\">" +
        "<div class=\"wiz-prog-num\" id=\"mv-pnum-" + i + "\">" + (i + 1) + "</div>" +
        "<div class=\"wiz-prog-label\">" + label + "</div></button>";
    });
    bar.innerHTML = html;
  }

  function updateProgressBar() {
    STEP_LABELS.forEach(function (_, i) {
      var btn  = document.getElementById("mv-prog-"  + i);
      var pnum = document.getElementById("mv-pnum-"  + i);
      var sep  = document.getElementById("mv-sep-"   + (i - 1));
      if (!btn) return;
      btn.classList.remove("active", "done");
      if (i < currentStep)       { btn.classList.add("done");   pnum.textContent = "✓"; }
      else if (i === currentStep) { btn.classList.add("active"); pnum.textContent = String(i + 1); }
      else                        { pnum.textContent = String(i + 1); }
      if (sep) sep.classList.toggle("done", i <= currentStep);
    });
    var st = document.getElementById("mv-status");
    if (st) st.textContent = "Step " + (currentStep + 1) + " of " + TOTAL_STEPS;
  }

  function showStep() {
    for (var i = 0; i < TOTAL_STEPS; i++) {
      var el = document.getElementById("mv-step-" + i);
      if (el) el.style.display = (i === currentStep) ? "" : "none";
    }
    var backBtn = document.getElementById("mv-back");
    var nextBtn = document.getElementById("mv-next");
    if (backBtn) backBtn.style.display = (currentStep > 0) ? "" : "none";
    if (nextBtn) {
      if (currentStep === TOTAL_STEPS - 1) {
        nextBtn.textContent = "Continue →";
      } else {
        nextBtn.textContent = "Next →";
      }
    }
  }

  // ── Model KPI fill ────────────────────────────────────────────────────────
  function fillModelKpis(data) {
    var modelSel  = document.getElementById("mv-model-select");
    var regionSel = document.getElementById("mv-region-select");
    if (!modelSel || !regionSel) return;

    var modelId  = modelSel.value;
    var regionId = regionSel.value;
    var models   = getModels(data);
    var regions  = (data && data.regions) || [];
    var model    = models.find(function (m) { return m.id === modelId; });
    var region   = regions.find(function (r) { return r.id === regionId; }) || regions[0] || {};

    var kpisEl = document.getElementById("mv-model-kpis");
    if (!model) {
      if (kpisEl) kpisEl.style.display = "none";
      return;
    }
    if (kpisEl) kpisEl.style.display = "";
    var rate = S.parseNumber(model.turnkeyRate) + S.parseNumber(region.turnkeyPremium);
    S.setText("mv-kpi-sf",     S.formatCount(model.livingSf));
    S.setText("mv-kpi-rate",   "$" + rate.toFixed(2) + "/SF");
    S.setText("mv-kpi-mat",    S.formatMoney(model.materialTotal));
    S.setText("mv-kpi-region", region.name || "—");
  }

  function getModels(data) {
    return (data && data.sales && data.sales.wizard && data.sales.wizard.models) || [];
  }

  // ── Populate selects ──────────────────────────────────────────────────────
  function populateSelects(data) {
    var models  = getModels(data);
    var regions = (data && data.regions) || [];
    var session = S.getSession();

    var modelSel = document.getElementById("mv-model-select");
    if (modelSel) {
      modelSel.innerHTML = "<option value=\"\">— Select model —</option>" +
        models.map(function (m) {
          return "<option value=\"" + S.escapeHtml(m.id) + "\">" +
            S.escapeHtml(m.name + " – " + S.formatCount(m.livingSf) + " SF") + "</option>";
        }).join("");
      if (models.length) modelSel.value = models[0].id;
    }

    var regionSel = document.getElementById("mv-region-select");
    if (regionSel) {
      regionSel.innerHTML = regions.map(function (r) {
        var sel = r.id === session.regionId ? " selected" : "";
        return "<option value=\"" + S.escapeHtml(r.id) + "\"" + sel + ">" + S.escapeHtml(r.name) + "</option>";
      }).join("");
    }

    fillModelKpis(data);
  }

  // ── Validate current step ────────────────────────────────────────────────
  function validateStep() {
    if (currentStep === 0) {
      var name = document.getElementById("mv-customer-name");
      if (!name || !name.value.trim()) {
        S.showToast("Please enter the customer name.");
        return false;
      }
      var modelSel = document.getElementById("mv-model-select");
      if (!modelSel || !modelSel.value) {
        S.showToast("Please select a model.");
        return false;
      }
      if (!selectedScope) {
        S.showToast("Please select a contract scope (Turnkey or Shell).");
        return false;
      }
    }
    return true;
  }

  // ── Save & navigate ───────────────────────────────────────────────────────
  function saveCustomerData() {
    var cust = {
      customerName: (document.getElementById("mv-customer-name") || {}).value || "",
      phone:        (document.getElementById("mv-phone")         || {}).value || "",
      email:        (document.getElementById("mv-email")         || {}).value || "",
      address:      (document.getElementById("mv-address")       || {}).value || "",
      city:         (document.getElementById("mv-city")          || {}).value || "",
      state:        (document.getElementById("mv-state")         || {}).value || "",
      zip:          (document.getElementById("mv-zip")           || {}).value || "",
      subdivision:  (document.getElementById("mv-subdivision")   || {}).value || ""
    };
    try { localStorage.setItem("stmc_customer", JSON.stringify(cust)); } catch (e) {}
  }

  function saveModelData() {
    var modelSel  = document.getElementById("mv-model-select");
    var regionSel = document.getElementById("mv-region-select");
    if (modelSel)  { try { localStorage.setItem("stmc_modelId",  modelSel.value);  } catch (e) {} }
    if (regionSel) {
      try { localStorage.setItem("stmc_region", regionSel.value); } catch (e) {}
    }
  }

  function goToWizard() {
    var routes = window.STMC_ROUTES || {};
    if (selectedScope === "turnkey") {
      window.location.href = routes.turnkey || "/stmc_ops/turnkey/";
    } else {
      window.location.href = routes.shell   || "/stmc_ops/shell/";
    }
  }

  // ── Scope buttons ─────────────────────────────────────────────────────────
  function bindScopeButtons() {
    var tkBtn = document.getElementById("mv-scope-turnkey");
    var shBtn = document.getElementById("mv-scope-shell");
    if (tkBtn) tkBtn.addEventListener("click", function () {
      selectedScope = "turnkey";
      tkBtn.classList.add("active");
      if (shBtn) shBtn.classList.remove("active");
    });
    if (shBtn) shBtn.addEventListener("click", function () {
      selectedScope = "shell";
      shBtn.classList.add("active");
      if (tkBtn) tkBtn.classList.remove("active");
    });
  }

  // ── Nav buttons ───────────────────────────────────────────────────────────
  function bindNav(data) {
    var nextBtn = document.getElementById("mv-next");
    var backBtn = document.getElementById("mv-back");

    if (nextBtn) nextBtn.addEventListener("click", function () {
      if (!validateStep()) return;
      saveCustomerData();
      saveModelData();
      goToWizard();
    });

    if (backBtn) backBtn.addEventListener("click", function () {
      if (currentStep > 0) {
        currentStep--;
        updateProgressBar();
        showStep();
        window.scrollTo(0, 0);
      }
    });
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    S.loadData().then(function (data) {
      var user = S.applyHeaderSession();
      if (!user) return;

      buildProgressBar();
      populateSelects(data);
      bindScopeButtons();
      bindNav(data);
      updateProgressBar();
      showStep();

      // Update KPIs on model/region change
      var modelSel  = document.getElementById("mv-model-select");
      var regionSel = document.getElementById("mv-region-select");
      if (modelSel)  modelSel.addEventListener("change",  function () { fillModelKpis(data); });
      if (regionSel) regionSel.addEventListener("change", function () {
        // persist region choice immediately
        try { localStorage.setItem("stmc_region", regionSel.value); } catch (e) {}
        fillModelKpis(data);
      });

      // Sales nav tab switching
      document.querySelectorAll("[data-mv-tab]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          var tab = btn.getAttribute("data-mv-tab");
          document.querySelectorAll("[data-mv-tab]").forEach(function (b) {
            b.classList.toggle("active", b.getAttribute("data-mv-tab") === tab);
          });
          document.querySelectorAll(".mv-tab-section").forEach(function (s) {
            s.style.display = s.id === "mv-tab-" + tab ? "" : "none";
          });
          var isWizard = tab === "new-contract";
          var pw = document.getElementById("mv-progress-wrap");
          if (pw) pw.style.display = isWizard ? "" : "none";
          var wf = document.getElementById("mv-wizard-footer");
          if (wf) wf.style.display = isWizard ? "" : "none";
        });
      });

      // Logout
      S.bindLogout();

    }).catch(function (err) {
      console.error("STMC model_view load error:", err);
    });
  });

}());
