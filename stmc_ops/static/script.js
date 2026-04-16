// STMC Ops - Shared utilities (script.js)
// Loaded on every page before role-specific scripts.

(function (window) {
  var DATA_FILE = window.STMC_DATA_URL || "/static/data.json";
  var ROUTES    = window.STMC_ROUTES   || {};

  var demoData = null;

  // ── DOM helpers ──────────────────────────────────────────────────────────
  function $id(id) {
    return document.getElementById(id);
  }

  function setText(id, value) {
    var el = $id(id);
    if (el) el.textContent = value;
  }

  function setValue(id, value) {
    var el = $id(id);
    if (el) el.value = value;
  }

  // ── String / number helpers ───────────────────────────────────────────────
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g,  "&amp;")
      .replace(/</g,  "&lt;")
      .replace(/>/g,  "&gt;")
      .replace(/"/g,  "&quot;")
      .replace(/'/g,  "&#39;");
  }

  function parseNumber(value) {
    if (typeof value === "number") return value;
    if (typeof value === "string") {
      var n = Number(value.replace(/[^0-9.-]/g, ""));
      return isNaN(n) ? 0 : n;
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
    var p = Number(value);
    return isNaN(p) ? 0 : Math.max(0, Math.min(100, p));
  }

  function getToneClass(tone, type) {
    if (type === "pill") {
      if (tone === "success") return "pill-success";
      if (tone === "danger")  return "pill-danger";
      return "pill-warning";
    }
    if (type === "dot") {
      if (tone === "success") return "dot-success";
      if (tone === "warning") return "dot-warning";
      return "dot-brand";
    }
    if (tone === "success") return "tone-success";
    if (tone === "warning") return "tone-warning";
    if (tone === "danger")  return "tone-danger";
    return "";
  }

  // ── Data access ───────────────────────────────────────────────────────────
  function getCollection(name) {
    return (demoData && demoData[name]) || [];
  }

  function findById(collection, id) {
    return collection.find(function (item) { return item.id === id; }) || null;
  }

  // ── Session ───────────────────────────────────────────────────────────────
  function setSession(userId, regionId) {
    localStorage.setItem("stmc_user",   userId);
    localStorage.setItem("stmc_region", regionId);
  }

  function clearSession() {
    localStorage.removeItem("stmc_user");
    localStorage.removeItem("stmc_region");
  }

  function getSession() {
    var regions = getCollection("regions");
    return {
      userId:   localStorage.getItem("stmc_user")   || "",
      regionId: localStorage.getItem("stmc_region") || (regions.length ? regions[0].id : "")
    };
  }

  function getSessionRegion() {
    var session = getSession();
    var regions = getCollection("regions");
    return findById(regions, session.regionId) || regions[0] || {};
  }

  // ── Routing ───────────────────────────────────────────────────────────────
  function getLoginUrl() { return ROUTES.login || "/stmc_ops/login/"; }

  function getRoleUrl(role) {
    var map = { sales: ROUTES.sales, pm: ROUTES.pm, exec: ROUTES.exec };
    return map[role] || "";
  }

  // ── UI feedback ───────────────────────────────────────────────────────────
  function showToast(message) {
    var toast = $id("app-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "app-toast";
      toast.className = "toast-message";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(function () {
      toast.classList.remove("show");
    }, 2200);
  }

  function showLoadError(message) {
    var wrap = document.querySelector(".wrap") ||
               document.querySelector(".login-wrap") ||
               document.body;
    var banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent = message;
    wrap.insertBefore(banner, wrap.firstChild);
  }

  // ── Data loading ──────────────────────────────────────────────────────────
  function loadData() {
    if (demoData) return Promise.resolve(demoData);
    return fetch(DATA_FILE, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("Could not load " + DATA_FILE + " (" + r.status + ")");
        return r.json();
      })
      .then(function (data) {
        demoData = data;
        return data;
      });
  }

  // ── Header ───────────────────────────────────────────────────────────────
  function applyHeaderSession() {
    var users   = getCollection("users");
    var regions = getCollection("regions");
    var session = getSession();
    var user    = findById(users,   session.userId);
    var region  = findById(regions, session.regionId);

    if (!user) {
      window.location.href = getLoginUrl();
      return null;
    }

    setText("hN", user.name);
    setText("hA", user.initials);
    setText("hR", region ? region.name : "");
    return user;
  }

  // ── Tab navigation ────────────────────────────────────────────────────────
  function bindLogout() {
    document.querySelectorAll(".logout-link").forEach(function (el) {
      el.addEventListener("click", function () {
        clearSession();
        window.location.href = getLoginUrl();
      });
    });
  }

  function bindTabNav() {
    var buttons = Array.from(document.querySelectorAll(".nav button[data-target]"));
    if (!buttons.length) return;
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = btn.getAttribute("data-target");
        buttons.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        document.querySelectorAll(".page").forEach(function (p) { p.classList.remove("active"); });
        var page = document.getElementById(target);
        if (page) page.classList.add("active");
      });
    });
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.STMC = {
    loadData:           loadData,
    getCollection:      getCollection,
    findById:           findById,
    getSession:         getSession,
    getSessionRegion:   getSessionRegion,
    setSession:         setSession,
    clearSession:       clearSession,
    getLoginUrl:        getLoginUrl,
    getRoleUrl:         getRoleUrl,
    applyHeaderSession: applyHeaderSession,
    bindLogout:         bindLogout,
    bindTabNav:         bindTabNav,
    showToast:          showToast,
    showLoadError:      showLoadError,
    escapeHtml:         escapeHtml,
    parseNumber:        parseNumber,
    formatMoney:        formatMoney,
    formatCount:        formatCount,
    clampPercent:       clampPercent,
    getToneClass:       getToneClass,
    setText:            setText,
    setValue:           setValue,
    $id:                $id
  };

})(window);
