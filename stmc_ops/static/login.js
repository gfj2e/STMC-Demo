// STMC Ops - Login page behavior
// Requires script.js (window.STMC) to be loaded first.

(function () {
  var S = window.STMC;
  if (!S) return;

  function renderOptions(selectEl, items, mapLabel) {
    if (!selectEl) return;
    if (!items.length) {
      selectEl.innerHTML = "";
      return;
    }
    selectEl.innerHTML = items.map(function (item) {
      return '<option value="' + S.escapeHtml(item.id) + '">' +
        S.escapeHtml(mapLabel(item)) +
        '</option>';
    }).join("");
  }

  function initLogin() {
    var users = S.getCollection("users");
    var regions = S.getCollection("regions");
    var userSel = S.$id("lU");
    var regSel = S.$id("lR");

    renderOptions(userSel, users, function (u) {
      return u.name + " - " + u.title;
    });
    renderOptions(regSel, regions, function (r) {
      return r.name;
    });

    var signInBtn = S.$id("signInBtn");
    if (!signInBtn) return;

    signInBtn.addEventListener("click", function () {
      var userId = userSel ? userSel.value : "";
      var regionId = regSel ? regSel.value : "";
      var user = S.findById(users, userId);
      if (!user) {
        S.showToast("Select a valid user to continue.");
        return;
      }
      S.setSession(userId, regionId);
      window.location.href = S.getRoleUrl(user.role) || S.getLoginUrl();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-page") !== "login") return;

    S.loadData()
      .then(function () {
        initLogin();
      })
      .catch(function (err) {
        console.error(err);
        S.showLoadError("Unable to load demo data. Check data.json and refresh.");
      });
  });
})();
