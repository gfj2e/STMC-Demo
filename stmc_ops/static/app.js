(function() {
  var DATA_FILE = window.STMC_DATA_URL || "/static/data.json";
  var ROUTES = window.STMC_ROUTES || {};

  var demoData = null;
  var salesWizardState = null;

  function $(id) {
    return document.getElementById(id);
  }

  function getPageMode() {
    return document.body.getAttribute("data-page") || "";
  }

  function getCollection(name) {
    if (!demoData || !demoData[name]) {
      return [];
    }
    return demoData[name];
  }

  function getRolePages() {
    if (!demoData || !demoData.rolePages) {
      return {};
    }
    return demoData.rolePages;
  }

  function getLoginUrl() {
    return ROUTES.login || "/stmc_ops/login/";
  }

  function getRoleUrl(role) {
    var routeByRole = {
      sales: ROUTES.sales,
      pm: ROUTES.pm,
      exec: ROUTES.exec
    };
    return routeByRole[role] || "";
  }

  function findById(collection, id) {
    return collection.find(function(item) {
      return item.id === id;
    }) || null;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function parseNumber(value) {
    if (typeof value === "number") {
      return value;
    }
    if (typeof value === "string") {
      var cleanValue = value.replace(/[^0-9.-]/g, "");
      var parsed = Number(cleanValue);
      return isNaN(parsed) ? 0 : parsed;
    }
    return 0;
  }

  function formatMoney(amount) {
    return "$" + Math.round(parseNumber(amount)).toLocaleString();
  }

  function formatCount(value) {
    return Math.round(parseNumber(value)).toLocaleString();
  }

  function clampPercent(value) {
    var percent = Number(value);
    if (isNaN(percent)) {
      return 0;
    }
    return Math.max(0, Math.min(100, percent));
  }

  function getToneClass(tone, type) {
    if (type === "pill") {
      if (tone === "success") {
        return "pill-success";
      }
      if (tone === "danger") {
        return "pill-danger";
      }
      return "pill-warning";
    }

    if (type === "dot") {
      if (tone === "success") {
        return "dot-success";
      }
      if (tone === "warning") {
        return "dot-warning";
      }
      return "dot-brand";
    }

    if (tone === "success") {
      return "tone-success";
    }
    if (tone === "warning") {
      return "tone-warning";
    }
    if (tone === "danger") {
      return "tone-danger";
    }
    return "";
  }

  function setStoredSession(userId, regionId) {
    localStorage.setItem("stmc_user", userId);
    localStorage.setItem("stmc_region", regionId);
  }

  function clearStoredSession() {
    localStorage.removeItem("stmc_user");
    localStorage.removeItem("stmc_region");
  }

  function getSession() {
    var regions = getCollection("regions");
    var defaultRegion = regions.length ? regions[0].id : "";
    return {
      userId: localStorage.getItem("stmc_user") || "",
      regionId: localStorage.getItem("stmc_region") || defaultRegion
    };
  }

  function getRegionForSession() {
    var session = getSession();
    var regions = getCollection("regions");
    return findById(regions, session.regionId) || regions[0] || {
      laborMultiplier: 1,
      concreteMultiplier: 1,
      turnkeyPremium: 0,
      name: "Default"
    };
  }

  function showLoadError(message) {
    var wrap = document.querySelector(".wrap") || document.querySelector(".login-wrap") || document.body;
    var banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent = message;
    wrap.insertBefore(banner, wrap.firstChild);
  }

  function showToast(message) {
    var toast = $("app-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "app-toast";
      toast.className = "toast-message";
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("show");

    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function() {
      toast.classList.remove("show");
    }, 2200);
  }

  function loadData() {
    if (demoData) {
      return Promise.resolve(demoData);
    }

    return fetch(DATA_FILE, { cache: "no-store" })
      .then(function(response) {
        if (!response.ok) {
          throw new Error("Could not load " + DATA_FILE + " (" + response.status + ")");
        }
        return response.json();
      })
      .then(function(data) {
        demoData = data;
        return demoData;
      });
  }

  function populateLoginOptions() {
    var users = getCollection("users");
    var regions = getCollection("regions");
    var userSelect = $("lU");
    var regionSelect = $("lR");

    if (userSelect) {
      userSelect.innerHTML = users
        .map(function(user) {
          return "<option value=\"" + escapeHtml(user.id) + "\">" +
            escapeHtml(user.name + " - " + user.title) +
            "</option>";
        })
        .join("");
    }

    if (regionSelect) {
      regionSelect.innerHTML = regions
        .map(function(region) {
          return "<option value=\"" + escapeHtml(region.id) + "\">" +
            escapeHtml(region.name) +
            "</option>";
        })
        .join("");
    }
  }

  function bindLogin() {
    var signInBtn = $("signInBtn");
    if (!signInBtn) {
      return;
    }

    signInBtn.addEventListener("click", function() {
      var users = getCollection("users");
      var rolePages = getRolePages();
      var userId = $("lU") ? $("lU").value : "";
      var regionId = $("lR") ? $("lR").value : "";
      var user = findById(users, userId);

      if (!user) {
        return;
      }

      setStoredSession(userId, regionId);
      window.location.href = getRoleUrl(user.role) || rolePages[user.role] || getLoginUrl();
    });
  }

  function applyHeaderSession() {
    var users = getCollection("users");
    var regions = getCollection("regions");
    var session = getSession();
    var user = findById(users, session.userId);
    var region = findById(regions, session.regionId);

    if (!user) {
      window.location.href = getLoginUrl();
      return null;
    }

    if ($("hN")) {
      $("hN").textContent = user.name;
    }

    if ($("hA")) {
      $("hA").textContent = user.initials;
    }

    if ($("hR")) {
      $("hR").textContent = region ? region.name : "";
    }

    return user;
  }

  function bindLogout() {
    document.querySelectorAll(".logout-link").forEach(function(el) {
      el.addEventListener("click", function() {
        clearStoredSession();
        window.location.href = getLoginUrl();
      });
    });
  }

  function bindTabNav() {
    var navButtons = Array.prototype.slice.call(document.querySelectorAll(".nav button[data-target]"));
    if (!navButtons.length) {
      return;
    }

    navButtons.forEach(function(button) {
      button.addEventListener("click", function() {
        var target = button.getAttribute("data-target");

        navButtons.forEach(function(item) {
          item.classList.remove("active");
        });
        button.classList.add("active");

        document.querySelectorAll(".page").forEach(function(page) {
          page.classList.remove("active");
        });

        var activePage = document.getElementById(target);
        if (activePage) {
          activePage.classList.add("active");
        }
      });
    });
  }

  function renderKpis(containerId, kpis) {
    var container = $(containerId);
    if (!container) {
      return;
    }

    container.innerHTML = kpis
      .map(function(kpi) {
        var valueClasses = ["kpi-value"];
        var toneClass = getToneClass(kpi.tone, "value");
        if (kpi.mono) {
          valueClasses.push("mono");
        }
        if (toneClass) {
          valueClasses.push(toneClass);
        }

        return "<article class=\"kpi\">" +
          "<div class=\"kpi-label\">" + escapeHtml(kpi.label) + "</div>" +
          "<div class=\"" + valueClasses.join(" ") + "\">" + escapeHtml(kpi.value) + "</div>" +
          "</article>";
      })
      .join("");
  }

  function getSalesWizardData(salesData) {
    var wizard = salesData.wizard || {};
    var fallbackModels = (salesData.models || []).map(function(item) {
      return {
        id: item.model.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
        name: item.model,
        livingSf: parseNumber(item.sf),
        materialTotal: Math.round(parseNumber(item.total) * 0.24),
        laborBudget: Math.round(parseNumber(item.total) * 0.11),
        concreteBudget: Math.round(parseNumber(item.total) * 0.1),
        turnkeyRate: parseNumber(item.turnkeyPerSf)
      };
    });

    return {
      models: wizard.models || fallbackModels,
      rateCard: wizard.rateCard || [],
      upgrades: wizard.upgrades || []
    };
  }

  function findModelById(models, modelId) {
    return models.find(function(item) {
      return item.id === modelId;
    }) || null;
  }

  function initializeSalesMetrics(model) {
    var livingSf = parseNumber(model && model.livingSf);
    var metrics = {
      livingSF: livingSf,
      garageSF: Math.round(livingSf * 0.35),
      porchSF: Math.round(livingSf * 0.18),
      roofSF: Math.round(livingSf * 1.8),
      extWallSF: Math.round(livingSf * 0.85),
      soffitLF: Math.round(Math.sqrt(Math.max(livingSf, 1)) * 5.2),
      beamLF: 0,
      cabLF: Math.round(livingSf * 0.02 + 12),
      intDoors: Math.round(livingSf / 120),
      extDoors: 3,
      windows: Math.round(livingSf / 150 + 3),
      fixtures: Math.round(livingSf / 200 + 4)
    };
    return recomputeSalesMetrics(metrics);
  }

  function recomputeSalesMetrics(metrics) {
    metrics.slabSF = (metrics.livingSF || 0) + (metrics.garageSF || 0) + (metrics.porchSF || 0);
    metrics.counterSF = Math.round((metrics.cabLF || 0) * 2);
    metrics.hvacTons = Math.max(2, Math.round((metrics.livingSF || 0) / 500));
    return metrics;
  }

  function createSalesWizardState(salesData) {
    var wizardData = getSalesWizardData(salesData);
    var defaultModel = wizardData.models[0] || null;
    var materialTotal = parseNumber(defaultModel && defaultModel.materialTotal);

    return {
      step: 0,
      customerName: "",
      modelId: defaultModel ? defaultModel.id : "",
      metrics: initializeSalesMetrics(defaultModel),
      upgrades: [],
      p10: Math.round(materialTotal * 1.1)
    };
  }

  function calculateExterior(state, region, wizardData) {
    var laborMultiplier = parseNumber(region.laborMultiplier) || 1;
    var lines = [];
    var total = 0;

    wizardData.rateCard.forEach(function(item) {
      if (item.category !== "exterior") {
        return;
      }

      var quantity = item.metric === "flat" ? 1 : parseNumber(state.metrics[item.metric]);
      var cost = Math.round(quantity * parseNumber(item.rate) * laborMultiplier);
      if (cost > 0) {
        lines.push({
          label: item.label,
          quantity: quantity,
          rate: parseNumber(item.rate),
          cost: cost,
          unit: item.unit
        });
        total += cost;
      }
    });

    var customerPrice = Math.round(parseNumber(state.metrics.slabSF) * 12);
    var margin = customerPrice ? Math.round((1 - total / customerPrice) * 100) : 0;

    return {
      lines: lines,
      total: total,
      customerPrice: customerPrice,
      margin: margin
    };
  }

  function calculateConcrete(state, region) {
    var slabRate = 8 * (parseNumber(region.concreteMultiplier) || 1);
    var slab = Math.round(parseNumber(state.metrics.slabSF) * slabRate);
    var driveway = 3600;
    var walkway = 900;
    var gradeBeam = 4200;
    var total = slab + driveway + walkway + gradeBeam;

    return {
      slabRate: slabRate,
      slab: slab,
      driveway: driveway,
      walkway: walkway,
      gradeBeam: gradeBeam,
      total: total
    };
  }

  function calculateInterior(state, region, wizardData, selectedModel) {
    var totalsByGroup = {};
    var trueCost = 0;

    wizardData.rateCard.forEach(function(item) {
      if (item.category !== "interior") {
        return;
      }

      var quantity = 1;
      if (item.metric !== "flat") {
        quantity = parseNumber(state.metrics[item.metric]);
      }

      var lineCost = Math.round(quantity * parseNumber(item.rate));
      trueCost += lineCost;
      totalsByGroup[item.group] = (totalsByGroup[item.group] || 0) + lineCost;
    });

    var turnkeyRate = parseNumber(selectedModel && selectedModel.turnkeyRate);
    var premium = parseNumber(region.turnkeyPremium);
    var livingSf = parseNumber(selectedModel && selectedModel.livingSf);
    var contract = Math.round(livingSf * (turnkeyRate + premium));
    var margin = contract ? Math.round((1 - trueCost / contract) * 100) : 0;

    return {
      totalsByGroup: totalsByGroup,
      trueCost: trueCost,
      contract: contract,
      margin: margin
    };
  }

  function calculateSalesTotals(state, region, wizardData, selectedModel) {
    var exterior = calculateExterior(state, region, wizardData);
    var concrete = calculateConcrete(state, region);
    var interior = calculateInterior(state, region, wizardData, selectedModel);
    var upgradesTotal = state.upgrades.reduce(function(total, item) {
      return total + parseNumber(item.amount);
    }, 0);
    var p10 = parseNumber(state.p10);
    var contractTotal = p10 + concrete.total + exterior.total + interior.contract + upgradesTotal;

    var deposit = 2500;
    var first = Math.max(p10 - deposit, 0);
    var second = concrete.total;
    var third = exterior.total;
    var fourth = Math.round(contractTotal * 0.2);
    var fifth = Math.round(contractTotal * 0.2);
    var sixth = contractTotal - deposit - first - second - third - fourth - fifth;

    return {
      exterior: exterior,
      concrete: concrete,
      interior: interior,
      upgradesTotal: upgradesTotal,
      p10: p10,
      contractTotal: contractTotal,
      drawSchedule: [
        { label: "Good Faith Deposit", amount: deposit },
        { label: "1st - Materials", amount: first },
        { label: "2nd - Concrete", amount: second },
        { label: "3rd - Exterior Labor", amount: third },
        { label: "4th - Rough-ins", amount: fourth },
        { label: "5th - Finishes", amount: fifth },
        { label: "6th - Final Punch", amount: sixth }
      ]
    };
  }

  function renderSalesStepper(labels, currentStep) {
    var nodes = labels.map(function(label, index) {
      var stateClass = "todo";
      var marker = String(index + 1);

      if (index < currentStep) {
        stateClass = "done";
        marker = "\u2713";
      } else if (index === currentStep) {
        stateClass = "current";
      }

      var node = "<span class=\"sales-step-dot " + stateClass + "\">" + marker + "</span>";
      if (index < labels.length - 1) {
        node += "<span class=\"sales-step-line " + (index < currentStep ? "done" : "") + "\"></span>";
      }
      return node;
    }).join("");

    return "<div class=\"sales-stepper\">" + nodes + "</div>" +
      "<div class=\"sales-step-caption\"><span>" + labels[currentStep] + "</span><span>Step " + (currentStep + 1) + " / " + labels.length + "</span></div>";
  }

  function renderSalesStepModel(state, wizardData, region, selectedModel) {
    var options = ["<option value=\"\">Choose a model...</option>"];
    wizardData.models.forEach(function(model) {
      options.push("<option value=\"" + escapeHtml(model.id) + "\"" + (state.modelId === model.id ? " selected" : "") + ">" +
        escapeHtml(model.name + " - " + parseNumber(model.livingSf).toLocaleString() + " SF") +
        "</option>");
    });

    var kpis = "";
    if (selectedModel) {
      var turnkey = parseNumber(selectedModel.turnkeyRate) + parseNumber(region.turnkeyPremium);
      kpis = "<div class=\"kpis cols-3\">" +
        "<article class=\"kpi\"><div class=\"kpi-label\">Living SF</div><div class=\"kpi-value mono\">" + parseNumber(selectedModel.livingSf).toLocaleString() + "</div></article>" +
        "<article class=\"kpi\"><div class=\"kpi-label\">Turnkey / SF</div><div class=\"kpi-value mono\">$" + turnkey.toFixed(2) + "</div></article>" +
        "<article class=\"kpi\"><div class=\"kpi-label\">Region</div><div class=\"kpi-value\">" + escapeHtml(region.name || "") + "</div></article>" +
        "</div>";
    }

    return "<h2 class=\"wizard-title\">Select model</h2>" +
      "<article class=\"card\">" +
      "<div class=\"field\"><label for=\"sw-model-select\">Model</label><select id=\"sw-model-select\">" + options.join("") + "</select></div>" +
      "<div class=\"field\"><label for=\"sw-customer\">Customer</label><input id=\"sw-customer\" value=\"" + escapeHtml(state.customerName || "") + "\" placeholder=\"Customer name\" /></div>" +
      "</article>" +
      kpis;
  }

  function renderSalesStepMetrics(state) {
    var fields = [
      { key: "livingSF", label: "Living SF", unit: "SF" },
      { key: "garageSF", label: "Garage SF", unit: "SF" },
      { key: "porchSF", label: "Porch SF", unit: "SF" },
      { key: "slabSF", label: "Slab SF (auto)", unit: "SF", computed: true },
      { key: "roofSF", label: "Roof Schedule SF", unit: "SF" },
      { key: "extWallSF", label: "Exterior Wall SF", unit: "SF" },
      { key: "soffitLF", label: "Soffit LF", unit: "LF" },
      { key: "beamLF", label: "Beam Wrap LF", unit: "LF" },
      { key: "windows", label: "Windows", unit: "ea" },
      { key: "extDoors", label: "Exterior Doors", unit: "ea" },
      { key: "cabLF", label: "Cabinet LF", unit: "LF" },
      { key: "counterSF", label: "Counter SF (auto)", unit: "SF", computed: true },
      { key: "intDoors", label: "Interior Doors", unit: "ea" },
      { key: "fixtures", label: "Plumbing Fixtures", unit: "ea" },
      { key: "hvacTons", label: "HVAC Tons (auto)", unit: "ton", computed: true }
    ];

    return "<h2 class=\"wizard-title\">Plan metrics</h2>" +
      "<article class=\"card metrics-grid\">" +
      fields.map(function(field) {
        var value = Math.round(parseNumber(state.metrics[field.key]));
        if (field.computed) {
          return "<div class=\"metric-row\"><span class=\"metric-label\">" + escapeHtml(field.label) + "</span><span class=\"metric-value\">" +
            value.toLocaleString() + "</span><span class=\"metric-unit\">" + escapeHtml(field.unit) + "</span></div>";
        }
        return "<div class=\"metric-row\"><span class=\"metric-label\">" + escapeHtml(field.label) + "</span>" +
          "<input class=\"metric-input\" data-metric=\"" + escapeHtml(field.key) + "\" type=\"number\" value=\"" + value + "\" />" +
          "<span class=\"metric-unit\">" + escapeHtml(field.unit) + "</span></div>";
      }).join("") +
      "</article>";
  }

  function renderSalesStepExterior(exterior, state) {
    var rows = exterior.lines.map(function(line) {
      return "<div class=\"rw\">" +
        "<span class=\"rl\">" + escapeHtml(line.label) + "</span>" +
        "<span class=\"rd\">" + formatCount(line.quantity) + " \u00D7 $" + parseNumber(line.rate) + "</span>" +
        "<span class=\"rv\">" + formatMoney(line.cost) + "</span>" +
        "</div>";
    }).join("");

    return "<div class=\"stl\">Exterior labor</div>" +
      "<div class=\"sh\">Customer pricing<span>" + formatMoney(exterior.customerPrice) + "</span></div>" +
      "<div class=\"sb\">" +
      "<div class=\"rw\"><span class=\"rl\">Base shell</span><span class=\"rd\">" + formatCount(state.metrics.slabSF) + " SF \u00D7 $12</span><span class=\"rv\">" + formatMoney(exterior.customerPrice) + "</span></div>" +
      "<div class=\"rw rt\"><span class=\"rl\">Customer total</span><span class=\"rv\" style=\"color:var(--brand)\">" + formatMoney(exterior.customerPrice) + "</span></div>" +
      "</div>" +
      "<div class=\"shd\">Contractor budget<span>" + formatMoney(exterior.total) + "</span></div>" +
      "<div class=\"sb\">" + rows +
      "<div class=\"rw rt\"><span class=\"rl\">True cost</span><span class=\"rv\">" + formatMoney(exterior.total) + "</span></div>" +
      "</div>" +
      "<div class=\"kpis k3\">" +
      "<div class=\"kpi\"><div class=\"kl\">Customer</div><div class=\"kv\" style=\"font-size:15px\">" + formatMoney(exterior.customerPrice) + "</div></div>" +
      "<div class=\"kpi\"><div class=\"kl\">True cost</div><div class=\"kv\" style=\"font-size:15px\">" + formatMoney(exterior.total) + "</div></div>" +
      "<div class=\"kpi\"><div class=\"kl\">Margin</div><div class=\"kv\" style=\"font-size:15px;color:" + (exterior.margin >= 20 ? "var(--success)" : "var(--brand)") + "\">" + exterior.margin + "%</div></div>" +
      "</div>";
  }

  function renderSalesStepConcrete(concrete, state) {
    return "<div class=\"stl\">Concrete</div>" +
      "<div class=\"sh\">Concrete - pass-through<span>No margin</span></div>" +
      "<div class=\"sb\">" +
      "<div class=\"rw\"><span class=\"rl\">Monolithic slab</span><span class=\"rd\">" + formatCount(state.metrics.slabSF) + " SF \u00D7 $" + concrete.slabRate.toFixed(2) + "</span><span class=\"rv\">" + formatMoney(concrete.slab) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Driveway</span><span class=\"rd\">480 SF \u00D7 $7.50</span><span class=\"rv\">" + formatMoney(concrete.driveway) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Walkway</span><span class=\"rd\">120 SF \u00D7 $7.50</span><span class=\"rv\">" + formatMoney(concrete.walkway) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Grade beam</span><span class=\"rd\">flat</span><span class=\"rv\">" + formatMoney(concrete.gradeBeam) + "</span></div>" +
      "<div class=\"rw rt\"><span class=\"rl\">Concrete total</span><span class=\"rv\" style=\"color:var(--brand)\">" + formatMoney(concrete.total) + "</span></div>" +
      "</div>";
  }

  function renderSalesStepInterior(interior, selectedModel, region) {
    var groupRows = Object.keys(interior.totalsByGroup).sort(function(a, b) {
      return interior.totalsByGroup[b] - interior.totalsByGroup[a];
    }).map(function(group) {
      return "<div class=\"rw\"><span class=\"rl\">" + escapeHtml(group) + "</span><span class=\"rv\">" +
        formatMoney(interior.totalsByGroup[group]) + "</span></div>";
    }).join("");

    return "<div class=\"stl\">Interior budget</div>" +
      "<div class=\"blk\"><div class=\"blk-t\">Turnkey INT contract</div><div class=\"rw\"><span class=\"rl\">Turnkey adder</span><span class=\"rd\">" +
      formatCount(selectedModel && selectedModel.livingSf) + " SF \u00D7 $" +
      (parseNumber(selectedModel && selectedModel.turnkeyRate) + parseNumber(region.turnkeyPremium)).toFixed(2) +
      "</span><span class=\"rv\">" + formatMoney(interior.contract) + "</span></div></div>" +
      "<div class=\"shd\">PM trade budget<span>" + formatMoney(interior.trueCost) + "</span></div>" +
      "<div class=\"sb\">" + groupRows +
      "<div class=\"rw rt\"><span class=\"rl\">Total true cost</span><span class=\"rv\">" + formatMoney(interior.trueCost) + "</span></div>" +
      "</div>" +
      "<div class=\"kpis k3\">" +
      "<div class=\"kpi\"><div class=\"kl\">INT contract</div><div class=\"kv\" style=\"font-size:15px\">" + formatMoney(interior.contract) + "</div></div>" +
      "<div class=\"kpi\"><div class=\"kl\">True cost</div><div class=\"kv\" style=\"font-size:15px\">" + formatMoney(interior.trueCost) + "</div></div>" +
      "<div class=\"kpi\"><div class=\"kl\">Margin</div><div class=\"kv\" style=\"font-size:15px;color:" + (interior.margin >= 20 ? "var(--success)" : "var(--brand)") + "\">" + interior.margin + "%</div></div>" +
      "</div>";
  }

  function renderSalesStepUpgrades(state, wizardData) {
    var rows = "<div style=\"color:var(--text-soft);font-size:12px;text-align:center;padding:12px\">No upgrades added</div>";
    if (state.upgrades.length) {
      rows = state.upgrades.map(function(item) {
        return "<div class=\"rw\"><span class=\"rl\">" + escapeHtml(item.description) + "</span><span class=\"rv\">" +
          formatMoney(item.amount) + "</span></div>";
      }).join("");
    }

    return "<div class=\"stl\">P10 and upgrades</div>" +
      "<article class=\"card\">" +
      "<div class=\"field\"><label for=\"sw-p10\">P10 order total</label><input id=\"sw-p10\" type=\"number\" value=\"" + Math.round(parseNumber(state.p10)) + "\" /></div>" +
      "</article>" +
      "<div class=\"sh\">Customer upgrades<span>" + formatMoney(state.upgrades.reduce(function(total, item) { return total + parseNumber(item.amount); }, 0)) + "</span></div>" +
      "<div class=\"sb\">" + rows +
      "<div class=\"wizard-actions\"><button id=\"sw-add-upgrade\" class=\"btn btn-secondary\" type=\"button\">+ Add upgrade</button></div>" +
      "</div>";
  }

  function renderSalesStepContract(state, totals) {
    var drawRows = totals.drawSchedule.map(function(item) {
      return "<div class=\"rw\"><span class=\"rl\">" + escapeHtml(item.label) + "</span><span class=\"rv\">" +
        formatMoney(item.amount) + "</span></div>";
    }).join("");

    return "<div class=\"stl\">Contract preview</div>" +
      "<div class=\"sh\">Contract summary<span>" + escapeHtml(state.customerName || "Customer") + "</span></div>" +
      "<div class=\"sb\">" +
      "<div class=\"rw\"><span class=\"rl\">P10 materials</span><span class=\"rv\">" + formatMoney(totals.p10) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Concrete</span><span class=\"rv\">" + formatMoney(totals.concrete.total) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Exterior labor</span><span class=\"rv\">" + formatMoney(totals.exterior.total) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Interior turnkey</span><span class=\"rv\">" + formatMoney(totals.interior.contract) + "</span></div>" +
      "<div class=\"rw\"><span class=\"rl\">Upgrades</span><span class=\"rv\" style=\"color:var(--brand)\">" + formatMoney(totals.upgradesTotal) + "</span></div>" +
      "<div class=\"rw rt\"><span class=\"rl\">Total contract</span><span class=\"rv\" style=\"color:var(--brand);font-size:15px\">" + formatMoney(totals.contractTotal) + "</span></div>" +
      "</div>" +
      "<div class=\"tbar\"><span style=\"font-size:14px;font-weight:500\">Contract total</span><span style=\"font-size:22px;font-weight:700;font-family:DM Mono\">" + formatMoney(totals.contractTotal) + "</span></div>" +
      "<article class=\"card\"><div class=\"stl\">Draw schedule</div>" + drawRows + "<div class=\"rw rt\"><span class=\"rl\">Total</span><span class=\"rv\">" + formatMoney(totals.contractTotal) + "</span></div></article>" +
      "<div class=\"wizard-actions\">" +
      "<button id=\"sw-generate\" class=\"btn btn-primary\" type=\"button\">Generate PDF</button>" +
      "<button id=\"sw-docusign\" class=\"btn btn-success\" type=\"button\">Send to DocuSign</button>" +
      "</div>";
  }

  function renderSalesWizardButtons(step, hasModel) {
    var canNext = hasModel || step > 0;
    var restartButton = step === 6
      ? "<button id=\"sw-restart\" class=\"btn btn-secondary\" type=\"button\">Start over</button>"
      : "";

    return "<div class=\"wizard-actions\">" +
      (step > 0 ? "<button id=\"sw-prev\" class=\"btn btn-secondary\" type=\"button\">Back</button>" : "") +
      (step < 6 ? "<button id=\"sw-next\" class=\"btn btn-primary\" type=\"button\"" + (canNext ? "" : " disabled") + ">Next</button>" : "") +
      restartButton +
      "</div>";
  }

  function renderSalesStepContent(step, state, wizardData, region, selectedModel, totals) {
    if (step === 0) {
      return renderSalesStepModel(state, wizardData, region, selectedModel);
    }
    if (step === 1) {
      return renderSalesStepMetrics(state);
    }
    if (step === 2) {
      return renderSalesStepExterior(totals.exterior, state);
    }
    if (step === 3) {
      return renderSalesStepConcrete(totals.concrete, state);
    }
    if (step === 4) {
      return renderSalesStepInterior(totals.interior, selectedModel, region);
    }
    if (step === 5) {
      return renderSalesStepUpgrades(state, wizardData);
    }
    return renderSalesStepContract(state, totals);
  }

  function bindSalesWizardEvents(salesData, wizardData) {
    var modelSelect = $("sw-model-select");
    if (modelSelect) {
      modelSelect.addEventListener("change", function() {
        var selectedModel = findModelById(wizardData.models, modelSelect.value);
        salesWizardState.modelId = modelSelect.value;
        salesWizardState.metrics = initializeSalesMetrics(selectedModel);
        salesWizardState.upgrades = [];
        salesWizardState.p10 = Math.round(parseNumber(selectedModel && selectedModel.materialTotal) * 1.1);
        renderSalesWizard(salesData);
      });
    }

    var customerInput = $("sw-customer");
    if (customerInput) {
      customerInput.addEventListener("input", function() {
        salesWizardState.customerName = customerInput.value;
      });
    }

    document.querySelectorAll(".metric-input[data-metric]").forEach(function(input) {
      input.addEventListener("change", function() {
        var key = input.getAttribute("data-metric");
        salesWizardState.metrics[key] = parseNumber(input.value);
        salesWizardState.metrics = recomputeSalesMetrics(salesWizardState.metrics);
        renderSalesWizard(salesData);
      });
    });

    var p10Input = $("sw-p10");
    if (p10Input) {
      p10Input.addEventListener("input", function() {
        salesWizardState.p10 = parseNumber(p10Input.value);
      });
    }

    var addUpgradeButton = $("sw-add-upgrade");
    if (addUpgradeButton) {
      addUpgradeButton.addEventListener("click", function() {
        var remaining = wizardData.upgrades.filter(function(item) {
          return !salesWizardState.upgrades.some(function(existing) {
            return existing.description === item.description;
          });
        });

        if (!remaining.length) {
          showToast("All preset upgrades are already added.");
          return;
        }

        salesWizardState.upgrades.push(remaining[0]);
        showToast("Added: " + remaining[0].description);
        renderSalesWizard(salesData);
      });
    }

    var previousButton = $("sw-prev");
    if (previousButton) {
      previousButton.addEventListener("click", function() {
        salesWizardState.step = Math.max(0, salesWizardState.step - 1);
        renderSalesWizard(salesData);
      });
    }

    var nextButton = $("sw-next");
    if (nextButton) {
      nextButton.addEventListener("click", function() {
        if (!salesWizardState.modelId) {
          showToast("Select a model first.");
          return;
        }

        salesWizardState.metrics = recomputeSalesMetrics(salesWizardState.metrics);
        salesWizardState.step = Math.min(6, salesWizardState.step + 1);
        renderSalesWizard(salesData);
      });
    }

    var restartButton = $("sw-restart");
    if (restartButton) {
      restartButton.addEventListener("click", function() {
        salesWizardState = createSalesWizardState(salesData);
        renderSalesWizard(salesData);
      });
    }

    var generateButton = $("sw-generate");
    if (generateButton) {
      generateButton.addEventListener("click", function() {
        showToast("Contract PDF generated.");
      });
    }

    var docusignButton = $("sw-docusign");
    if (docusignButton) {
      docusignButton.addEventListener("click", function() {
        showToast("Sent to DocuSign.");
      });
    }
  }

  function renderSalesWizard(salesData) {
    var container = $("sales-wizard");
    if (!container) {
      return;
    }

    if (!salesWizardState) {
      salesWizardState = createSalesWizardState(salesData);
    }

    var wizardData = getSalesWizardData(salesData);
    var region = getRegionForSession();
    var selectedModel = findModelById(wizardData.models, salesWizardState.modelId);
    var totals = calculateSalesTotals(salesWizardState, region, wizardData, selectedModel);
    var stepLabels = ["Model", "Metrics", "Exterior", "Concrete", "Interior", "P10/Upgrades", "Contract"];

    container.innerHTML =
      renderSalesStepper(stepLabels, salesWizardState.step) +
      renderSalesStepContent(salesWizardState.step, salesWizardState, wizardData, region, selectedModel, totals) +
      renderSalesWizardButtons(salesWizardState.step, !!selectedModel);

    bindSalesWizardEvents(salesData, wizardData);
  }

  function renderSalesProjectsList(projects) {
    return projects
      .map(function(item) {
        var collectedValue = parseNumber(item.collected);
        var remainingValue = parseNumber(item.remaining);
        var contractValue = parseNumber(item.contract) || (collectedValue + remainingValue);
        var computedRemaining = remainingValue || Math.max(0, contractValue - collectedValue);
        var budgetPercent = item.budget !== undefined
          ? clampPercent(parseNumber(item.budget))
          : (contractValue > 0 ? Math.round((collectedValue / contractValue) * 100) : 0);

        var contractLabel = item.contract ? escapeHtml(item.contract) : formatMoney(contractValue);
        var collectedLabel = item.collected ? escapeHtml(item.collected) : formatMoney(collectedValue);
        var remainingLabel = item.remaining ? escapeHtml(item.remaining) : formatMoney(computedRemaining);

        var metaParts = [];
        if (item.model) {
          metaParts.push(String(item.model));
        }
        if (item.client) {
          metaParts.push(String(item.client));
        }
        if (item.pm) {
          metaParts.push("PM: " + String(item.pm));
        }
        var metaLine = metaParts.join(" - ");

        return "<article class=\"sales-project-card\">" +
          "<div class=\"sales-project-head\">" +
          "<div><h3>" + escapeHtml(item.project || "Project") + "</h3>" +
          "<p>" + escapeHtml(metaLine || "Active project") + "</p></div>" +
          "<span class=\"sales-stage " + getToneClass(item.stageTone, "") + "\">" + escapeHtml(item.stage || "Open") + "</span>" +
          "</div>" +
          "<div class=\"sales-project-stats\">" +
          "<div class=\"sales-project-stat\"><span>Contract</span><strong class=\"mono\">" + contractLabel + "</strong></div>" +
          "<div class=\"sales-project-stat\"><span>Collected</span><strong class=\"mono tone-success\">" + collectedLabel + "</strong></div>" +
          "<div class=\"sales-project-stat\"><span>Budget</span><strong class=\"mono\">" + budgetPercent + "%</strong></div>" +
          "<div class=\"sales-project-stat\"><span>Remaining</span><strong class=\"mono tone-success\">" + remainingLabel + "</strong></div>" +
          "</div>" +
          "</article>";
      })
      .join("");
  }

  function renderSales() {
    var salesData = demoData.sales || {};

    renderSalesWizard(salesData);

    if ($("sales-projects-list")) {
      var projects = salesData.projects || [];
      $("sales-projects-list").innerHTML = projects.length
        ? renderSalesProjectsList(projects)
        : "<article class=\"card\"><div class=\"notice\">No active projects.</div></article>";
    }

    if ($("sales-models-body")) {
      $("sales-models-body").innerHTML = (salesData.models || [])
        .map(function(item) {
          return "<tr>" +
            "<td>" + escapeHtml(item.model) + "</td>" +
            "<td class=\"mono\">" + escapeHtml(item.sf) + "</td>" +
            "<td class=\"mono\">" + escapeHtml(item.turnkeyPerSf) + "</td>" +
            "<td class=\"mono\">" + escapeHtml(item.total) + "</td>" +
            "</tr>";
        })
        .join("");
    }

    if ($("sales-rates-body")) {
      $("sales-rates-body").innerHTML = (salesData.rates || [])
        .map(function(item) {
          return "<tr>" +
            "<td>" + escapeHtml(item.trade) + "</td>" +
            "<td>" + escapeHtml(item.unit) + "</td>" +
            "<td class=\"mono\">" + escapeHtml(item.rate) + "</td>" +
            "</tr>";
        })
        .join("");
    }
  }

  function renderManager() {
    var managerData = demoData.manager || {};
    renderKpis("mgr-build-kpis", managerData.kpis || []);

    if ($("mgr-pipeline-body")) {
      $("mgr-pipeline-body").innerHTML = (managerData.pipeline || [])
        .map(function(item) {
          return "<tr>" +
            "<td>" + escapeHtml(item.build) + "</td>" +
            "<td>" + escapeHtml(item.model) + "</td>" +
            "<td><span class=\"pill " + getToneClass(item.phaseTone, "pill") + "\">" + escapeHtml(item.phase) + "</span></td>" +
            "<td class=\"mono\">" + escapeHtml(item.contract) + "</td>" +
            "</tr>";
        })
        .join("");
    }

    if ($("mgr-budgets-list")) {
      $("mgr-budgets-list").innerHTML = (managerData.budgets || [])
        .map(function(item) {
          var progress = clampPercent(item.progress);
          return "<article class=\"card\">" +
            "<div class=\"row\"><span class=\"muted\">" + escapeHtml(item.build) + " - spent</span><span class=\"value\">" +
            escapeHtml(item.spent) + " / " + escapeHtml(item.total) +
            "</span></div>" +
            "<div class=\"progress\"><span style=\"width:" + progress + "%\"></span></div>" +
            "<div class=\"notice\">Remaining: " + escapeHtml(item.remaining) + "</div>" +
            "</article>";
        })
        .join("");
    }

    if ($("mgr-draws-body")) {
      $("mgr-draws-body").innerHTML = (managerData.draws || [])
        .map(function(item) {
          return "<tr>" +
            "<td>" + escapeHtml(item.build) + "</td>" +
            "<td>" + escapeHtml(item.currentDraw) + "</td>" +
            "<td><span class=\"pill " + getToneClass(item.statusTone, "pill") + "\">" + escapeHtml(item.status) + "</span></td>" +
            "<td class=\"mono\">" + escapeHtml(item.amount) + "</td>" +
            "</tr>";
        })
        .join("");
    }
  }

  function renderOwner() {
    var ownerData = demoData.owner || {};
    renderKpis("own-kpis", ownerData.kpis || []);

    if ($("own-notifications")) {
      $("own-notifications").innerHTML = (ownerData.notifications || [])
        .map(function(item) {
          return "<article class=\"notification\">" +
            "<span class=\"dot " + getToneClass(item.tone, "dot") + "\"></span>" +
            "<div><strong>" + escapeHtml(item.title) + "</strong>" +
            "<div class=\"small muted\">" + escapeHtml(item.message) + "</div></div>" +
            "</article>";
        })
        .join("");
    }

    if ($("own-projects-body")) {
      $("own-projects-body").innerHTML = (ownerData.projects || [])
        .map(function(item) {
          return "<tr>" +
            "<td>" + escapeHtml(item.project) + "</td>" +
            "<td>" + escapeHtml(item.pm) + "</td>" +
            "<td class=\"mono\">" + escapeHtml(item.contract) + "</td>" +
            "<td><span class=\"pill " + getToneClass(item.marginTone, "pill") + "\">" + escapeHtml(item.margin) + "</span></td>" +
            "</tr>";
        })
        .join("");
    }

    if ($("own-payments-card")) {
      $("own-payments-card").innerHTML = (ownerData.payments || [])
        .map(function(item) {
          var percent = clampPercent(item.collectedPercent);
          return "<div class=\"row\"><span class=\"muted\">" + escapeHtml(item.project) +
            "</span><span class=\"value\">" + percent + "% collected</span></div>" +
            "<div class=\"progress\"><span style=\"width:" + percent + "%\"></span></div>";
        })
        .join("");
    }
  }

  function renderPageByMode(mode) {
    if (mode === "sales") {
      renderSales();
      return;
    }

    if (mode === "manager") {
      renderManager();
      return;
    }

    if (mode === "owner") {
      renderOwner();
    }
  }

  document.addEventListener("DOMContentLoaded", function() {
    var mode = getPageMode();

    loadData()
      .then(function() {
        if (mode === "login") {
          populateLoginOptions();
          bindLogin();
          return;
        }

        var user = applyHeaderSession();
        if (!user) {
          return;
        }

        bindLogout();
        bindTabNav();
        renderPageByMode(mode);
      })
      .catch(function(error) {
        console.error(error);
        showLoadError("Unable to load demo data. Check data.json and refresh.");
      });
  });
})();
