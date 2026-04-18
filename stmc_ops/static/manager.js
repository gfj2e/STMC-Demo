// STMC Ops – Manager role JavaScript (manager.js)
// Requires script.js to be loaded first (window.STMC).

(function () {
  var S = window.STMC;

  function renderPipeline(pipeline) {
    var body = S.$id("mgr-pipeline-body");
    if (!body) return;
    body.innerHTML = (pipeline || []).map(function (item) {
      return "<tr>" +
        "<td>" + S.escapeHtml(item.build) + "</td>" +
        "<td>" + S.escapeHtml(item.model) + "</td>" +
        "<td><span class=\"pill " + S.getToneClass(item.phaseTone, "pill") + "\">" + S.escapeHtml(item.phase) + "</span></td>" +
        "<td class=\"mono\">" + S.escapeHtml(item.contract) + "</td>" +
        "</tr>";
    }).join("");
  }

  function renderBudgets(budgets) {
    var container = S.$id("mgr-budgets-list");
    if (!container) return;
    container.innerHTML = (budgets || []).map(function (item) {
      var pct = S.clampPercent(item.progress);
      return "<article class=\"card\">" +
        "<div class=\"row\"><span class=\"muted\">" + S.escapeHtml(item.build) + " – spent</span>" +
        "<span class=\"value\">" + S.escapeHtml(item.spent) + " / " + S.escapeHtml(item.total) + "</span></div>" +
        "<div class=\"progress\"><span style=\"width:" + pct + "%\"></span></div>" +
        "<div class=\"notice\">Remaining: " + S.escapeHtml(item.remaining) + "</div>" +
        "</article>";
    }).join("");
  }

  function renderDraws(draws) {
    var body = S.$id("mgr-draws-body");
    if (!body) return;
    body.innerHTML = (draws || []).map(function (item) {
      return "<tr>" +
        "<td>" + S.escapeHtml(item.build) + "</td>" +
        "<td>" + S.escapeHtml(item.currentDraw) + "</td>" +
        "<td><span class=\"pill " + S.getToneClass(item.statusTone, "pill") + "\">" + S.escapeHtml(item.status) + "</span></td>" +
        "<td class=\"mono\">" + S.escapeHtml(item.amount) + "</td>" +
        "</tr>";
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (document.body.getAttribute("data-page") !== "manager") return;

    S.loadData()
      .then(function (data) {
        var user = S.applyHeaderSession();
        if (!user) return;

        S.bindLogout();
        S.bindTabNav();

        var mgr = data.manager || {};
        S.renderKpis("mgr-build-kpis", mgr.kpis);
        renderPipeline(mgr.pipeline);
        renderBudgets(mgr.budgets);
        renderDraws(mgr.draws);
      })
      .catch(function (err) {
        console.error(err);
        S.showLoadError("Unable to load demo data. Check data.json and refresh.");
      });
  });

})();
