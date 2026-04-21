// STMC Ops - Login page behavior
// Requires script.js (window.STMC) to be loaded first.

(function () {
  var S = window.STMC;
  if (!S) return;

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function toText(value) {
    return value == null ? "" : String(value);
  }

  function renderOptions(selectEl, items, mapLabel) {
    if (!selectEl) return;

    selectEl.replaceChildren();

    var list = asArray(items);
    if (!list.length) return;

    var frag = document.createDocumentFragment();

    list.forEach(function (item) {
      var opt = document.createElement("option");
      var id = item && item.id != null ? item.id : "";
      opt.value = toText(id);
      opt.textContent = toText(mapLabel(item));
      frag.appendChild(opt);
    });

    selectEl.appendChild(frag);
  }

  function initLogin() {
    var users = asArray(S.getCollection("users"));
    var regions = asArray(S.getCollection("regions"));
    var userSel = S.$id("lU");
    var regSel = S.$id("lR");

    renderOptions(userSel, users, function (u) {
      var name = u && u.name ? u.name : "";
      var title = u && u.title ? u.title : "";
      return name + " - " + title;
    });
    renderOptions(regSel, regions, function (r) {
      return r && r.name ? r.name : "";
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
        S.showLoadError("Unable to load app data. Refresh and try again.");
      });
  });
})();
