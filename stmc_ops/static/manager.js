// STMC Ops - Manager role JavaScript
// Auth is handled server-side (Django session + @role_required).
// Template injects window.STMC_USER / LOGIN_URL / LOGOUT_URL / CSRF_TOKEN.

const LOGIN_URL = window.LOGIN_URL;
const LOGOUT_URL = window.LOGOUT_URL;

function initials(name) {
  return (name || '')
    .split(/\s+/)
    .map(function (part) { return part[0] || ''; })
    .join('')
    .toUpperCase()
    .slice(0, 2) || '?';
}

function showToast(message) {
  var toast = document.getElementById('toast');
  if (!toast) return;

  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(function () {
    toast.classList.remove('show');
  }, 3200);
}

function activateTab(button, tab, options) {
  var shouldRefresh = !(options && options.refresh === false);
  document.querySelectorAll('.tab-panel').forEach(function (panel) {
    panel.style.display = 'none';
  });
  document.querySelectorAll('.app-nav-link[data-tab]').forEach(function (link) {
    link.classList.remove('active');
  });

  var target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';
  if (button) button.classList.add('active');
  setManagerSearchVisibility(tab);
  setManagerViewToggleVisibility((tab))

  if (shouldRefresh) {
    document.body.dispatchEvent(new CustomEvent('manager-' + tab + '-refresh'));
  }
}

function setManagerSearchVisibility(tab) {
  var searchWrap = document.getElementById('job-search-wrap');
  if (!searchWrap) return;
  var visibleTabs = {
    'builds-active': true,
    'builds-closed': true,
    'draws': true,
  };
  searchWrap.style.display = visibleTabs[tab] ? 'flex' : 'none';
}

function setManagerViewToggleVisibility(tab) {
  var toggle = document.querySelector('.job-view-toggle');
  if (!toggle) return;
  var visibleTabs = {
    'builds-active': true,
    'builds-closed': true,
    'draws': true
  }
  toggle.style.display = visibleTabs[tab] ? 'inline-flex' : 'none';
}

function bindTabs() {
  document.querySelectorAll('.app-nav-link[data-tab]').forEach(function (button) {
    button.addEventListener('click', function () {
      activateTab(button, button.dataset.tab);
    });
  });
}

function bindLogout() {
  document.querySelectorAll('.logout-link').forEach(function (button) {
    button.addEventListener('click', function () {
      fetch(LOGOUT_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': window.CSRF_TOKEN },
      }).finally(function () { window.location.href = LOGIN_URL; });
    });
  });
}

function bindProjectToggles() {
  document.addEventListener('click', function (event) {
    var header = event.target.closest('.proj-hdr');
    if (!header) return;

    var body = header.nextElementSibling;
    var chevron = header.querySelector('.chevron');
    if (body) body.classList.toggle('open');
    if (chevron) chevron.classList.toggle('open');
  });
}

function bindHtmxFeedback() {
  if (!window.htmx) return;

  // Error path only — the success path fires a richer toast via the
  // 'qb-invoice-sent' listener below (triggered by the server's
  // HX-Trigger JSON header on the complete endpoint).
  document.body.addEventListener('htmx:afterRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-complete-form="1"]')) return;
    if (event.detail.successful) {
      // The draw panel is swapped via hx-target, so explicitly clear the
      // shared modal host after a successful complete action.
      closeChangeOrderModal();
      return;
    }
    if (!event.detail.successful) {
      showToast('Error saving - try again');
      // Restore the button label if the request failed. On success the
      // server swaps #tab-draws-panel so the button element is replaced
      // entirely and this restore is moot.
      restoreCompleteLabel(elt);
    }
  });
}

function restoreCompleteLabel(form) {
  var label = form.querySelector('.btn-complete-label');
  if (label && label.dataset.originalLabel) {
    label.textContent = label.dataset.originalLabel;
  }
}

function bindCompleteBusyLabel() {
  // When the Mark Complete form fires off, swap the label to "Sending..."
  // so the PM gets immediate feedback that the click registered. Combined
  // with hx-disabled-elt on the button this gives us both visual busy
  // state AND hard debounce — impossible to double-submit.
  document.body.addEventListener('htmx:beforeRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-complete-form="1"]')) return;
    var button = elt.querySelector('.btn-complete');
    var label = elt.querySelector('.btn-complete-label');
    if (!button || !label) return;
    var busyText = button.getAttribute('data-busy-label') || 'Sending...';
    if (!label.dataset.originalLabel) {
      label.dataset.originalLabel = label.textContent;
    }
    label.textContent = busyText;
  });
}

function bindQbInvoiceToast() {
  // Fired by the server's HX-Trigger: {"qb-invoice-sent": {...}} response
  // header after manager_panel_mark_complete_view. Detail payload:
  //   { invoice_number, team, amount, status, url }
  // status is "sent" (real QB invoice) or "failed_fallback" (local only).
  document.body.addEventListener('qb-invoice-sent', function (event) {
    var d = (event && event.detail) || {};
    // Phase 4 refresh path supplies a pre-formatted `message`; prefer that
    // over the per-event invoice_number/team format used by mark-complete.
    if (d.message) {
      showToast(d.message);
      return;
    }
    var prefix = d.status === 'failed_fallback'
      ? 'Draw complete (QB unavailable - recorded locally)'
      : 'QuickBooks Invoice ' + (d.invoice_number || '');
    var suffix = d.team
      ? ' sent for ' + d.team + ' - $' + (d.amount || '0')
      : '';
    showToast(prefix + suffix);
  });
}

function initAuthHeader() {
  var user = window.STMC_USER || {};
  var nameEl = document.getElementById('hN');
  var badgeEl = document.getElementById('hA');
  if (nameEl) nameEl.textContent = user.name || '';
  if (badgeEl) badgeEl.textContent = user.initials || initials(user.name);
}

function closeChangeOrderModal() {
  var host = document.getElementById('manager-modal-host');
  if (host) host.innerHTML = '';
}

function bindChangeOrderModal() {
  // Close on overlay click (outside the inner .modal box) or Cancel button.
  document.addEventListener('click', function (event) {
    var cancel = event.target.closest('[data-co-cancel]');
    if (cancel) {
      event.preventDefault();
      closeChangeOrderModal();
      return;
    }
    var overlay = event.target.closest('[data-co-modal]');
    if (overlay && event.target === overlay) {
      closeChangeOrderModal();
    }
  });

  // Close on Esc.
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    if (document.querySelector('[data-co-modal]')) closeChangeOrderModal();
  });

  // Server fires a JSON HX-Trigger {"change-order-created": {...}} after a
  // successful POST. The response body re-renders #tab-builds-active-panel; we
  // close the modal here and show a confirmation toast.
  document.body.addEventListener('change-order-created', function (event) {
    var d = (event && event.detail) || {};
    closeChangeOrderModal();
    var amt = parseFloat((d.amount || '0').replace(/,/g, ''));
    var sign = amt < 0 ? '-' : '+';
    var pretty = Math.abs(amt).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    showToast(
      'Change Order #' + (d.number || '?') + ' added to ' +
      (d.customer || 'build') + ' (' + sign + '$' + pretty + ')'
    );
  });

  // Edit flow: update view fires {"change-order-updated": {...}} after a
  // successful save. Close the modal and toast — same shape as the create path.
  document.body.addEventListener('change-order-updated', function (event) {
    var d = (event && event.detail) || {};
    closeChangeOrderModal();
    showToast(
      'Change Order #' + (d.number || '?') + ' updated for ' +
      (d.customer || 'build')
    );
  });

  // Delete flow: server fires {"change-order-deleted": {...}} after the row
  // is removed. Close any open modal (defensive; row-level delete usually has
  // none open) and toast.
  document.body.addEventListener('change-order-deleted', function (event) {
    var d = (event && event.detail) || {};
    closeChangeOrderModal();
    showToast(
      'Change Order #' + (d.number || '?') + ' deleted from ' +
      (d.customer || 'build')
    );
  });
}

function clearJobHit() {
  document.querySelectorAll('.job-search-hit').forEach(function (node) {
    node.classList.remove('job-search-hit');
  });
}

function findManagerJobMatch(query) {
  // Search whichever rendering is currently visible. In cards mode look
  // at .proj-card; in table mode look at .job-table-row. Both carry the
  // same data-job-search so the lookup is identical.
  var inTableMode = document.body.classList.contains('view-mode-table');
  var selector = inTableMode
    ? '.table-view tr.job-table-row[data-job-search]'
    : '.cards-view .proj-card[data-job-search]';
  var targets = [
    { tab: 'builds-active', panelId: 'tab-builds-active-panel' },
    { tab: 'builds-closed', panelId: 'tab-builds-closed-panel' },
    { tab: 'draws', panelId: 'tab-draws-panel' },
  ];

  // Prefer the tab the user is currently on so a search from the Draws
  // tab stays on Draws instead of jumping to Active Builds (where every
  // draw's underlying job also lives).
  var activeTabBtn = document.querySelector('.app-nav-link.active[data-tab]');
  var activeTab = activeTabBtn && activeTabBtn.dataset.tab;
  if (activeTab) {
    targets.sort(function (a, b) {
      if (a.tab === activeTab) return -1;
      if (b.tab === activeTab) return 1;
      return 0;
    });
  }

  for (var i = 0; i < targets.length; i++) {
    var target = targets[i];
    var panel = document.getElementById(target.panelId);
    if (!panel) continue;

    var nodes = panel.querySelectorAll(selector);
    for (var j = 0; j < nodes.length; j++) {
      var node = nodes[j];
      var haystack = (node.getAttribute('data-job-search') || node.textContent || '').toLowerCase();
      if (haystack.indexOf(query) !== -1) {
        return { target: target, card: node };
      }
    }
  }
  return null;
}

function openManagerFoundCard(node) {
  // node may be either a .proj-card (cards view) or a .job-table-row
  // (table view). Each has its own "expand" affordance.
  if (node.classList.contains('job-table-row')) {
    var detail = node._detailRow || node.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail') && detail.hasAttribute('hidden')) {
      _toggleManagerTableRowDetail(node);
    }
    return;
  }

  var details = node.closest('details');
  if (details) details.open = true;

  var body = node.querySelector('.proj-body');
  var chevron = node.querySelector('.chevron');
  if (body) body.classList.add('open');
  if (chevron) chevron.classList.add('open');
}

function runManagerJobSearch() {
  var input = document.getElementById('job-search-input');
  if (!input) return;

  var query = (input.value || '').trim().toLowerCase();
  if (!query) {
    showToast('Type a job name, order number, or branch to search');
    return;
  }

  clearJobHit();
  var match = findManagerJobMatch(query);
  if (!match) {
    showToast('No matching job found');
    return;
  }

  var button = document.querySelector('.app-nav-link[data-tab="' + match.target.tab + '"]');
  activateTab(button, match.target.tab, { refresh: false });
  openManagerFoundCard(match.card);
  match.card.classList.add('job-search-hit');
  match.card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(function () {
    match.card.classList.remove('job-search-hit');
  }, 2200);
  showToast('Job found');
}

function bindJobSearch() {
  var button = document.getElementById('job-search-btn');
  var input = document.getElementById('job-search-input');
  if (!button || !input) return;

  button.addEventListener('click', runManagerJobSearch);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      runManagerJobSearch();
    }
  });
}

function _managerNormalize(value) {
  return (value || '').toString().trim().toLowerCase();
}

function _managerFilterPanels() {
  return ['tab-builds-active-panel', 'tab-builds-closed-panel', 'tab-draws-panel'];
}

function _managerFilterCards() {
  // Returns ALL filterable elements: card view (.proj-card) AND table
  // rows (.job-table-row). Both carry the same data-* attributes so the
  // same filter logic works against either rendering. The view toggle
  // just hides whichever view isn't active via body class.
  var nodes = [];
  _managerFilterPanels().forEach(function (panelId) {
    var panel = document.getElementById(panelId);
    if (!panel) return;
    panel.querySelectorAll('[data-job-search]').forEach(function (node) {
      nodes.push(node);
    });
  });
  return nodes;
}

function _managerPopulateFilterSelect(selectId, values, emptyLabel) {
  var select = document.getElementById(selectId);
  if (!select) return;
  var selected = select.value;
  var options = ['<option value="">' + emptyLabel + '</option>'];
  values.forEach(function (value) {
    options.push('<option value="' + value + '">' + value + '</option>');
  });
  select.innerHTML = options.join('');
  select.value = values.indexOf(selected) !== -1 ? selected : '';
}

function rebuildManagerFilterOptions() {
  var branches = new Set();
  var plans = new Set();
  var phases = new Set();
  var years = new Set();

  _managerFilterCards().forEach(function (card) {
    var branch = card.dataset.branch || '';
    var plan = card.dataset.plan || '';
    var phase = card.dataset.phase || '';
    var year = card.dataset.year || '';
    if (branch) branches.add(branch);
    if (plan) plans.add(plan);
    if (phase) phases.add(phase);
    if (year) years.add(year);
  });

  _managerPopulateFilterSelect('job-filter-branch', Array.from(branches).sort(), 'All branches');
  _managerPopulateFilterSelect('job-filter-plan', Array.from(plans).sort(), 'All plans');
  _managerPopulateFilterSelect('job-filter-phase', Array.from(phases).sort(), 'All phases');
  _managerPopulateFilterSelect(
    'job-filter-year',
    Array.from(years).sort(function (a, b) { return Number(b) - Number(a); }),
    'All years'
  );
}

function _managerCardSortValue(card) {
  var ts = Number(card.dataset.sortTs || 0);
  if (Number.isFinite(ts) && ts > 0) return ts;
  var order = String(card.dataset.order || '').replace(/\D/g, '');
  return Number(order || 0);
}

function _managerSortGroupCards(group, sortMode) {
  var body = group.querySelector('.project-group-body');
  if (!body) return;
  var cards = Array.from(body.querySelectorAll('.proj-card[data-job-search]'));
  cards.sort(function (a, b) {
    var av = _managerCardSortValue(a);
    var bv = _managerCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  cards.forEach(function (card) { body.appendChild(card); });
}

function _managerSortTableRows(panel, sortMode) {
  // Each project is TWO rows (summary + detail). Sort moves them as a
  // pair so an expanded detail row stays beneath its own summary.
  var tbody = panel.querySelector('.table-view tbody');
  if (!tbody) return;
  var rows = Array.from(tbody.querySelectorAll('tr.job-table-row'));
  rows.sort(function (a, b) {
    var av = _managerCardSortValue(a);
    var bv = _managerCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  rows.forEach(function (row) {
    tbody.appendChild(row);
    if (row._detailRow) tbody.appendChild(row._detailRow);
  });
}

function _bindManagerRowDetailRefs() {
  // Stash each summary row's paired detail row so sort can move the pair
  // together (since appendChild changes sibling relationships).
  document.querySelectorAll('.table-view tr.job-table-row').forEach(function (row) {
    var detail = row.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail')) {
      row._detailRow = detail;
    }
  });
}

function _toggleManagerTableRowDetail(summary) {
  var detail = summary._detailRow || summary.nextElementSibling;
  if (!detail || !detail.classList.contains('job-table-detail')) return;
  var willExpand = detail.hasAttribute('hidden');
  if (willExpand) {
    detail.removeAttribute('hidden');
  } else {
    detail.setAttribute('hidden', '');
  }
  // Don't touch inline display — CSS drives the open/close transition off
  // the [hidden] attribute. Setting display:none would jump the row into/out
  // of layout and kill the transition.
  detail.style.display = '';
  summary.setAttribute('aria-expanded', String(willExpand));
  summary.classList.toggle('is-expanded', willExpand);
  var chev = summary.querySelector('.row-chevron');
  if (chev) chev.textContent = willExpand ? '▾' : '▸';
}

function bindManagerTableRowToggle() {
  // Delegate so newly-swapped panels work without re-binding. Click or
  // keyboard (Enter/Space) on a summary row toggles its detail row.
  // Clicks on actual interactive elements inside the row (a, button,
  // <input>, etc.) are NOT treated as a row-toggle so links/buttons
  // still work normally.
  document.addEventListener('click', function (event) {
    var summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    if (event.target.closest('a, button, input, select, label')) return;
    _toggleManagerTableRowDetail(summary);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    var summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    event.preventDefault();
    _toggleManagerTableRowDetail(summary);
  });
}

// ── View toggle (Cards / Table) ──────────────────────────────────────
// Persists across navigation via localStorage. CSS controls visibility
// based on body class `view-mode-table`.
var MANAGER_VIEW_KEY = 'stmc-manager-view-mode';

function _applyManagerViewMode(mode) {
  var isTable = mode === 'table';
  document.body.classList.toggle('view-mode-table', isTable);
  var cardsBtn = document.getElementById('job-view-cards');
  var tableBtn = document.getElementById('job-view-table');
  if (cardsBtn) {
    cardsBtn.classList.toggle('active', !isTable);
    cardsBtn.setAttribute('aria-pressed', String(!isTable));
  }
  if (tableBtn) {
    tableBtn.classList.toggle('active', isTable);
    tableBtn.setAttribute('aria-pressed', String(isTable));
  }
}

function bindManagerViewToggle() {
  var cardsBtn = document.getElementById('job-view-cards');
  var tableBtn = document.getElementById('job-view-table');
  if (!cardsBtn || !tableBtn) return;
  var saved = 'table';
  try { saved = localStorage.getItem(MANAGER_VIEW_KEY) || 'table'; } catch (e) { /* private mode */ }
  _applyManagerViewMode(saved === 'cards' ? 'cards' : 'table');

  cardsBtn.addEventListener('click', function () {
    _applyManagerViewMode('cards');
    try { localStorage.setItem(MANAGER_VIEW_KEY, 'cards'); } catch (e) {}
  });
  tableBtn.addEventListener('click', function () {
    _applyManagerViewMode('table');
    try { localStorage.setItem(MANAGER_VIEW_KEY, 'table'); } catch (e) {}
  });
}

function applyManagerFilters() {
  var branch = _managerNormalize(document.getElementById('job-filter-branch') && document.getElementById('job-filter-branch').value);
  var plan = _managerNormalize(document.getElementById('job-filter-plan') && document.getElementById('job-filter-plan').value);
  var phase = _managerNormalize(document.getElementById('job-filter-phase') && document.getElementById('job-filter-phase').value);
  var year = _managerNormalize(document.getElementById('job-filter-year') && document.getElementById('job-filter-year').value);
  var sortMode = _managerNormalize(document.getElementById('job-filter-sort') && document.getElementById('job-filter-sort').value) || 'newest';

  _managerFilterPanels().forEach(function (panelId) {
    var panel = document.getElementById(panelId);
    if (!panel) return;

    var panelVisibleCount = 0;
    panel.querySelectorAll('.project-group').forEach(function (group) {
      _managerSortGroupCards(group, sortMode);
      var visibleCount = 0;
      group.querySelectorAll('.proj-card[data-job-search]').forEach(function (card) {
        var matches = true;
        if (branch && _managerNormalize(card.dataset.branch) !== branch) matches = false;
        if (plan && _managerNormalize(card.dataset.plan) !== plan) matches = false;
        if (phase && _managerNormalize(card.dataset.phase) !== phase) matches = false;
        if (year && _managerNormalize(card.dataset.year) !== year) matches = false;
        card.style.display = matches ? '' : 'none';
        if (matches) visibleCount += 1;
      });

      var countEl = group.querySelector('.project-group-count');
      if (countEl) countEl.textContent = String(visibleCount);
      group.style.display = visibleCount ? '' : 'none';
      panelVisibleCount += visibleCount;
    });

    // Mirror the same filter on the flat table view (if present). Each
    // job has TWO <tr>s: the summary row and a paired detail row hidden
    // by default. Hide both in lockstep when a filter excludes the job.
    _managerSortTableRows(panel, sortMode);
    panel.querySelectorAll('.table-view tr.job-table-row').forEach(function (row) {
      var matches = true;
      if (branch && _managerNormalize(row.dataset.branch) !== branch) matches = false;
      if (plan && _managerNormalize(row.dataset.plan) !== plan) matches = false;
      if (phase && _managerNormalize(row.dataset.phase) !== phase) matches = false;
      if (year && _managerNormalize(row.dataset.year) !== year) matches = false;
      row.style.display = matches ? '' : 'none';
      var detail = row.nextElementSibling;
      if (detail && detail.classList.contains('job-table-detail')) {
        // Filter excludes: hide via inline display. Filter includes: clear
        // the override and let CSS drive the open/close transition off
        // [hidden].
        detail.style.display = matches ? '' : 'none';
      }
    });

    var sectionCount = panel.querySelector('.group-section-title .group-section-count');
    if (sectionCount) sectionCount.textContent = '(' + panelVisibleCount + ')';
  });
}

function bindManagerFilters() {
  ['job-filter-branch', 'job-filter-plan', 'job-filter-phase', 'job-filter-year', 'job-filter-sort'].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el || el.dataset.filterBound === '1') return;
    el.dataset.filterBound = '1';
    el.addEventListener('change', applyManagerFilters);
  });
}

function bindManagerFilterRefreshOnSwap() {
  if (!window.htmx) return;
  document.body.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target) return;
    if (
      target.id !== 'tab-builds-active-panel' &&
      target.id !== 'tab-builds-closed-panel' &&
      target.id !== 'tab-draws-panel'
    ) return;
    rebuildManagerFilterOptions();
    bindManagerFilters();
    _bindManagerRowDetailRefs();
    applyManagerFilters();
  });
}

// ── Preserve open/expanded state across HTMX panel swaps ─────────────
// When a draw is marked complete or a change order is saved, the server
// returns a fresh render of the panel — collapsing every open card and
// table row. Snapshot which jobs were expanded before the swap and
// re-open them after. Keyed by data-job-id (added to both .proj-card
// and tr.job-table-row in the templates).
var _MANAGER_PANEL_OPEN_STATE = {};

function _captureManagerPanelOpenState(panel) {
  var state = { cards: [], rows: [], groups: [] };
  panel.querySelectorAll('.proj-card[data-job-id]').forEach(function (card) {
    var body = card.querySelector('.proj-body');
    if (body && body.classList.contains('open')) {
      state.cards.push(card.dataset.jobId);
    }
  });
  panel.querySelectorAll('.table-view tr.job-table-row[data-job-id]').forEach(function (row) {
    var detail = row.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail') && !detail.hasAttribute('hidden')) {
      state.rows.push(row.dataset.jobId);
    }
  });
  panel.querySelectorAll('details.project-group').forEach(function (g) {
    var summary = g.querySelector('.project-group-summary');
    var label = summary ? summary.textContent.trim() : '';
    state.groups.push({ label: label, open: !!g.open });
  });
  return state;
}

function _restoreManagerPanelOpenState(panel, state) {
  if (!state) return;
  state.cards.forEach(function (id) {
    var card = panel.querySelector('.proj-card[data-job-id="' + id + '"]');
    if (!card) return;
    var body = card.querySelector('.proj-body');
    var chev = card.querySelector('.chevron');
    if (body) body.classList.add('open');
    if (chev) chev.classList.add('open');
  });
  state.rows.forEach(function (id) {
    var row = panel.querySelector('.table-view tr.job-table-row[data-job-id="' + id + '"]');
    if (!row) return;
    var detail = row.nextElementSibling;
    if (!detail || !detail.classList.contains('job-table-detail')) return;
    detail.removeAttribute('hidden');
    detail.style.display = '';
    row.setAttribute('aria-expanded', 'true');
    row.classList.add('is-expanded');
    var chev = row.querySelector('.row-chevron');
    if (chev) chev.textContent = '▾';
  });
  if (state.groups.length) {
    var groups = panel.querySelectorAll('details.project-group');
    var labelMap = {};
    state.groups.forEach(function (g) { labelMap[g.label] = g.open; });
    groups.forEach(function (g) {
      var summary = g.querySelector('.project-group-summary');
      var label = summary ? summary.textContent.trim() : '';
      if (label in labelMap) g.open = labelMap[label];
    });
  }
}

function bindManagerPanelStatePersistence() {
  if (!window.htmx) return;
  document.body.addEventListener('htmx:beforeSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target || !target.id) return;
    if (
      target.id !== 'tab-builds-active-panel' &&
      target.id !== 'tab-builds-closed-panel' &&
      target.id !== 'tab-draws-panel'
    ) return;
    _MANAGER_PANEL_OPEN_STATE[target.id] = _captureManagerPanelOpenState(target);
  });
  document.body.addEventListener('htmx:afterSettle', function (event) {
    var target = event.detail && event.detail.target;
    if (!target || !target.id) return;
    var state = _MANAGER_PANEL_OPEN_STATE[target.id];
    if (!state) return;
    _restoreManagerPanelOpenState(target, state);
    delete _MANAGER_PANEL_OPEN_STATE[target.id];
  });
}

function activateExecTab(jobId, tabName) {
  var tabs = document.querySelectorAll('.exec-tab[data-job-id="' + jobId + '"]');
  var panels = document.querySelectorAll('.exec-tab-panel[data-job-id="' + jobId + '"]');
  tabs.forEach(function (tab) {
    tab.classList.toggle('is-active', tab.dataset.jobTab === tabName);
  });
  panels.forEach(function (panel) {
    panel.hidden = panel.dataset.jobPanel !== tabName;
  });
}

function bindExecTabs() {
  if (bindExecTabs._bound) return;
  bindExecTabs._bound = true;
  document.addEventListener('click', function (event) {
    var tab = event.target.closest('.exec-tab');
    if (!tab) return;
    activateExecTab(tab.dataset.jobId, tab.dataset.jobTab);
  });
}

function init() {
  bindTabs();
  bindExecTabs();
  bindLogout();
  bindProjectToggles();
  bindHtmxFeedback();
  bindCompleteBusyLabel();
  bindQbInvoiceToast();
  bindChangeOrderModal();
  bindJobSearch();
  bindManagerFilters();
  bindManagerFilterRefreshOnSwap();
  bindManagerPanelStatePersistence();
  bindManagerViewToggle();
  bindManagerTableRowToggle();
  _bindManagerRowDetailRefs();
  rebuildManagerFilterOptions();
  applyManagerFilters();
  initAuthHeader();
  setManagerSearchVisibility('builds-active');
  setManagerViewToggleVisibility('builds-active');
}

init();
