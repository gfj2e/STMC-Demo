// STMC Ops - Login page behavior
// Sign-in options are server-rendered via HTMX.

(function () {
  var ROUTES = window.STMC_ROUTES || {};
  var LOGIN_URL = ROUTES.login || "/stmc_ops/login/";

  function getRoleUrl(role) {
    var map = {
      sales: ROUTES.sales,
      pm: ROUTES.pm,
      exec: ROUTES.exec,
    };
    return map[role] || LOGIN_URL;
  }

  function showToast(message) {
    var toast = document.getElementById("app-toast");
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

  function signIn() {
    var userSel = document.getElementById("lU");
    var regSel = document.getElementById("lR");

    var userId = userSel ? userSel.value : "";
    var regionId = regSel ? regSel.value : "";
    var userOpt = userSel && userSel.selectedOptions ? userSel.selectedOptions[0] : null;
    var role = userOpt ? userOpt.getAttribute("data-role") : "";

    if (!userId || !role) {
      showToast("Select a valid user to continue.");
      return;
    }
    if (!regionId) {
      showToast("Select a region to continue.");
      return;
    }

    localStorage.setItem("stmc_user", userId);
    localStorage.setItem("stmc_region", regionId);
    window.location.href = getRoleUrl(role);
  }

  function bindSignInButton() {
    var button = document.getElementById("signInBtn");
    if (!button || button.dataset.bound === "1") return;

    button.dataset.bound = "1";
    button.addEventListener("click", signIn);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-page") !== "login") return;
    bindSignInButton();
  });

  document.body.addEventListener("htmx:afterSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (!target || target.id !== "login-panel") return;
    bindSignInButton();
  });
})();
