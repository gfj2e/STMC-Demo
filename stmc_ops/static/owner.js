// STMC Ops – Owner/Executive role JavaScript (owner.js)
// Requires script.js to be loaded first (window.STMC).

(function () {
  var S = window.STMC;

  function renderKpis(containerId, kpis) {
    var container = S.$id(containerId);
    if (!container) return;
    container.innerHTML = (kpis || []).map(function (kpi) {
      var cls = ["kpi-value"];
      if (kpi.mono) cls.push("mono");
      var tone = S.getToneClass(kpi.tone, "value");
      if (tone) cls.push(tone);
      return "<article class=\"kpi\">" +
        "<div class=\"kpi-label\">" + S.escapeHtml(kpi.label) + "</div>" +
        "<div class=\"" + cls.join(" ") + "\">" + S.escapeHtml(kpi.value) + "</div>" +
        "</article>";
    }).join("");
  }

  function renderNotifications(notifications) {
    var container = S.$id("own-notifications");
    if (!container) return;
    container.innerHTML = (notifications || []).map(function (item) {
      return "<article class=\"notification\">" +
        "<span class=\"dot " + S.getToneClass(item.tone, "dot") + "\"></span>" +
        "<div><strong>" + S.escapeHtml(item.title) + "</strong>" +
        "<div class=\"small muted\">" + S.escapeHtml(item.message) + "</div></div>" +
        "</article>";
    }).join("");
  }

  function renderProjects(projects) {
    var body = S.$id("own-projects-body");
    if (!body) return;
    body.innerHTML = (projects || []).map(function (item) {
      return "<tr>" +
        "<td>" + S.escapeHtml(item.project) + "</td>" +
        "<td>" + S.escapeHtml(item.pm) + "</td>" +
        "<td class=\"mono\">" + S.escapeHtml(item.contract) + "</td>" +
        "<td><span class=\"pill " + S.getToneClass(item.marginTone, "pill") + "\">" + S.escapeHtml(item.margin) + "</span></td>" +
        "</tr>";
    }).join("");
  }

  function renderPayments(payments) {
    var container = S.$id("own-payments-list");
    if (!container) return;
    container.innerHTML = (payments || []).map(function (item) {
      var pct = S.clampPercent(item.collectedPercent);
      return "<div class=\"row\"><span class=\"muted\">" + S.escapeHtml(item.project) + "</span>" +
        "<span class=\"value\">" + pct + "% collected</span></div>" +
        "<div class=\"progress\"><span style=\"width:" + pct + "%\"></span></div>";
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-page") !== "owner") return;

    S.loadData()
      .then(function (data) {
        var user = S.applyHeaderSession();
        if (!user) return;

        S.bindLogout();
        S.bindTabNav();

        var own = data.owner || {};
        renderKpis("own-kpis", own.kpis);
        renderNotifications(own.notifications);
        renderProjects(own.projects);
        renderPayments(own.payments);
      })
      .catch(function (err) {
        console.error(err);
        S.showLoadError("Unable to load demo data. Check data.json and refresh.");
      });
  });

})();
