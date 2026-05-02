// STMC Ops - Sales role JavaScript
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

function updateHeaderTitle(tab) {
  var titles = {
    leads: 'Leads',
    'in-progress': 'In Progress',
    closed: 'Closed',
    rates: 'Rate Card'
  };
  var titleEl = document.querySelector('.header-title');
  // Don't overwrite the P10 header — leave the default Django-rendered label alone.
  if (titleEl && titleEl.dataset.tabTitle !== undefined) {
    titleEl.textContent = titles[tab] || 'Sales';
  }
}

function activateTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(function (panel) {
    panel.style.display = 'none';
  });

  var target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';

  document.querySelectorAll('.app-nav-link[data-mv-tab]').forEach(function (link) {
    link.classList.remove('active');
  });

  var navMap = {
    leads: 'leads',
    'in-progress': 'in-progress',
    closed: 'closed',
    rates: 'rates'
  };
  var navLink = document.querySelector('.app-nav-link[data-mv-tab="' + navMap[tab] + '"]');
  if (navLink) navLink.classList.add('active');

  updateHeaderTitle(tab);
  setSalesSearchVisibility(tab);
  // Re-apply filters so a search query typed on Closed gets immediately
  // honored when switching back to Closed (and is correctly ignored
  // on other tabs).
  applySalesFilters();
  document.body.dispatchEvent(new CustomEvent('sales-' + tab + '-refresh'));

  var url = new URL(window.location.href);
  if (tab === 'in-progress') {
    url.searchParams.delete('tab');
  } else {
    url.searchParams.set('tab', tab);
  }
  window.history.replaceState({}, '', url.toString());
}

function bindTabs() {
  var tabByNav = {
    leads: 'leads',
    'in-progress': 'in-progress',
    closed: 'closed',
    rates: 'rates'
  };

  document.querySelectorAll('.app-nav-link[data-mv-tab]').forEach(function (link) {
    var navKey = link.dataset.mvTab;
    if (!tabByNav[navKey]) return;

    link.addEventListener('click', function (event) {
      event.preventDefault();
      activateTab(tabByNav[navKey]);
    });
  });

  var defaultTab = new URLSearchParams(window.location.search).get('tab') || 'in-progress';
  if (!document.getElementById('tab-' + defaultTab)) {
    defaultTab = 'in-progress';
  }
  activateTab(defaultTab);
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

function setFinalizeButtonsDisabled(isDisabled) {
  document.querySelectorAll('button[data-finalize-contract="1"]').forEach(function (btn) {
    btn.disabled = !!isDisabled;
  });
}

function bindFinalizeContractReload() {
  if (!window.htmx) return;

  document.body.addEventListener('htmx:beforeRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('button[data-finalize-contract="1"]')) return;
    setFinalizeButtonsDisabled(true);
  });

  document.body.addEventListener('htmx:afterRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('button[data-finalize-contract="1"]')) return;
    if (event.detail.successful) {
      // Force a hard refresh so In Progress/Closed lists and loan/deposit
      // status pills reflect the latest server state before another action.
      window.location.reload();
      return;
    }
    setFinalizeButtonsDisabled(false);
  });
}

function initAuthHeader() {
  var user = window.STMC_USER || {};
  var nameEl = document.getElementById('hN');
  var badgeEl = document.getElementById('hA');
  if (nameEl) nameEl.textContent = user.name || '';
  if (badgeEl) badgeEl.textContent = user.initials || initials(user.name);
}

// ── Sales search + filter (mirrors manager.js search/filter) ──────────────

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

function setSalesSearchVisibility(tab) {
  var searchWrap = document.getElementById('job-search-wrap');
  if (!searchWrap) return;
  var visibleTabs = {
    'leads': true,
    'in-progress': true,
    'closed': true,
  };
  searchWrap.style.display = visibleTabs[tab] ? 'flex' : 'none';

  // Closed tab uses live filter mode; the "Find Job" button is redundant
  // there. In Progress + Leads keep the navigate-to-match button.
  var input = document.getElementById('job-search-input');
  var button = document.getElementById('job-search-btn');
  var isClosed = tab === 'closed';
  if (button) button.style.display = isClosed ? 'none' : '';
  if (input) {
    input.placeholder = isClosed
      ? 'Filter by customer, order #, branch…'
      : 'customer, order #, branch';
  }
}

function _salesFilterTargets() {
  return [
    { tab: 'in-progress', panelId: 'tab-in-progress-panel' },
    { tab: 'closed', panelId: 'tab-closed-panel' },
    { tab: 'leads', panelId: 'tab-leads-panel' },
  ];
}

function _salesFilterCards() {
  // Returns ALL filterable elements: card view (.proj-card) AND table rows
  // (.job-table-row). Both carry the same data-* attributes so the same
  // filter logic works against either rendering. The view toggle just
  // hides whichever view isn't active via body class.
  var nodes = [];
  _salesFilterTargets().forEach(function (target) {
    var panel = document.getElementById(target.panelId);
    if (!panel) return;
    panel.querySelectorAll('[data-job-search]').forEach(function (node) {
      nodes.push(node);
    });
  });
  return nodes;
}

function clearJobHit() {
  document.querySelectorAll('.job-search-hit').forEach(function (node) {
    node.classList.remove('job-search-hit');
  });
}

function findSalesJobMatch(query) {
  // Search whichever rendering is currently visible. In cards mode we
  // only consider .proj-card; in table mode we only consider table rows.
  // Both carry data-job-search so the haystack lookup is identical.
  var inTableMode = document.body.classList.contains('view-mode-table');
  var selector = inTableMode
    ? '.table-view tr.job-table-row[data-job-search]'
    : '.cards-view .proj-card[data-job-search]';
  var targets = _salesFilterTargets();
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

function openSalesFoundCard(node) {
  // node may be either a .proj-card (cards view) or a .job-table-row
  // (table view). Each has its own "expand" affordance:
  //   - card: open the surrounding <details> and the card's .proj-body
  //   - table row: expand its paired detail <tr> via the existing toggle
  if (node.classList.contains('job-table-row')) {
    var detail = node._detailRow || node.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail') && detail.hasAttribute('hidden')) {
      _toggleTableRowDetail(node);
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

function _currentSalesTab() {
  return new URLSearchParams(window.location.search).get('tab') || 'in-progress';
}

function runSalesJobSearch() {
  var input = document.getElementById('job-search-input');
  if (!input) return;
  var query = (input.value || '').trim().toLowerCase();
  if (!query) {
    showToast('Type a customer, order #, or branch to search');
    return;
  }
  clearJobHit();
  var match = findSalesJobMatch(query);
  if (!match) {
    showToast('No matching contract or lead found');
    return;
  }

  // If the match is on a different tab, switching tabs triggers an HTMX
  // refresh of the destination panel, which would wipe our match
  // reference. Re-find the row AFTER the swap settles before highlighting.
  if (match.target.tab !== _currentSalesTab()) {
    activateTab(match.target.tab);
    // Wait for the panel swap to complete, then re-find and highlight.
    var panel = document.getElementById(match.target.panelId);
    if (window.htmx && panel) {
      var onSwap = function (event) {
        if (!event.detail || event.detail.target !== panel) return;
        document.body.removeEventListener('htmx:afterSwap', onSwap);
        var fresh = findSalesJobMatch(query);
        if (fresh) _highlightSalesMatch(fresh.card);
      };
      document.body.addEventListener('htmx:afterSwap', onSwap);
    }
  } else {
    // Same tab, no refresh — highlight the existing node directly.
    _highlightSalesMatch(match.card);
  }
  showToast('Match found');
}

function _highlightSalesMatch(node) {
  openSalesFoundCard(node);
  node.classList.add('job-search-hit');
  node.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(function () {
    node.classList.remove('job-search-hit');
  }, 2200);
}

function bindSalesJobSearch() {
  var button = document.getElementById('job-search-btn');
  var input = document.getElementById('job-search-input');
  if (!button || !input) return;
  button.addEventListener('click', runSalesJobSearch);

  // Closed tab: live filter as you type (debounced ~250ms). Other tabs:
  // Enter triggers the navigate-to-match flow. The placeholder + button
  // visibility set in setSalesSearchVisibility() signal which mode is
  // active per tab.
  var liveTimer;
  input.addEventListener('input', function () {
    if (_currentSalesTab() !== 'closed') return;
    clearTimeout(liveTimer);
    liveTimer = setTimeout(applySalesFilters, 250);
  });
  input.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    if (_currentSalesTab() === 'closed') {
      // Already live-filtered; Enter just commits any pending debounce.
      clearTimeout(liveTimer);
      applySalesFilters();
    } else {
      runSalesJobSearch();
    }
  });
}

function _salesNormalize(value) {
  return (value || '').toString().trim().toLowerCase();
}

function _salesPopulateFilterSelect(selectId, values, emptyLabel) {
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

function rebuildSalesFilterOptions() {
  var branches = new Set();
  var plans = new Set();
  var phases = new Set();
  var years = new Set();

  _salesFilterCards().forEach(function (card) {
    var branch = card.dataset.branch || '';
    var plan = card.dataset.plan || '';
    var phase = card.dataset.phase || '';
    var year = card.dataset.year || '';
    if (branch) branches.add(branch);
    if (plan) plans.add(plan);
    if (phase) phases.add(phase);
    if (year) years.add(year);
  });

  _salesPopulateFilterSelect('job-filter-branch', Array.from(branches).sort(), 'All branches');
  _salesPopulateFilterSelect('job-filter-plan', Array.from(plans).sort(), 'All plans');
  _salesPopulateFilterSelect('job-filter-phase', Array.from(phases).sort(), 'All phases');
  _salesPopulateFilterSelect(
    'job-filter-year',
    Array.from(years).sort(function (a, b) { return Number(b) - Number(a); }),
    'All years'
  );
}

function _salesCardSortValue(card) {
  var ts = Number(card.dataset.sortTs || 0);
  if (Number.isFinite(ts) && ts > 0) return ts;
  var order = String(card.dataset.order || '').replace(/\D/g, '');
  return Number(order || 0);
}

function _salesSortGroupCards(group, sortMode) {
  var body = group.querySelector('.project-group-body');
  if (!body) return;
  // Sort within whichever inner wrapper holds the cards (e.g. .closed-list
  // on the closed tab). Fall back to .project-group-body otherwise.
  var listWrappers = body.querySelectorAll('.closed-list');
  var containers = listWrappers.length ? Array.from(listWrappers) : [body];
  containers.forEach(function (container) {
    var cards = Array.from(container.querySelectorAll('.proj-card[data-job-search]'));
    cards.sort(function (a, b) {
      var av = _salesCardSortValue(a);
      var bv = _salesCardSortValue(b);
      return sortMode === 'oldest' ? av - bv : bv - av;
    });
    cards.forEach(function (card) { container.appendChild(card); });
  });
}

function _salesSortTableRows(panel, sortMode) {
  // Mirror the card sort: applies to <tbody> in the panel's .table-view.
  // Each job is TWO rows (summary + detail). We move them as a pair so
  // an expanded detail row stays directly beneath its own summary.
  var tbody = panel.querySelector('.table-view tbody');
  if (!tbody) return;
  var rows = Array.from(tbody.querySelectorAll('tr.job-table-row'));
  rows.sort(function (a, b) {
    var av = _salesCardSortValue(a);
    var bv = _salesCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  rows.forEach(function (row) {
    tbody.appendChild(row);
    var detail = row.nextElementSibling;
    // After the summary moves, its old next-sibling is no longer adjacent;
    // re-find the detail by capturing it before appending. We do that by
    // querying the original DOM: the detail row was the immediate sibling
    // BEFORE we re-appended. Workaround: stash a reference on the row.
    if (row._detailRow) {
      tbody.appendChild(row._detailRow);
    }
  });
}

function _bindRowDetailRefs() {
  // Stash each summary row's paired detail row so sort can move the pair
  // together (since appendChild changes sibling relationships).
  document.querySelectorAll('.table-view tr.job-table-row').forEach(function (row) {
    var detail = row.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail')) {
      row._detailRow = detail;
    }
  });
}

function bindSalesTableRowToggle() {
  // Delegate so newly-swapped panels work without re-binding. Click or
  // keyboard (Enter/Space) on a summary row toggles its detail row.
  // Clicks on actual interactive elements inside the row (a, button,
  // <input>, etc.) are NOT treated as a row-toggle so links/buttons
  // still work normally.
  document.addEventListener('click', function (event) {
    var summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    if (event.target.closest('a, button, input, select, label')) return;
    _toggleTableRowDetail(summary);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    var summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    event.preventDefault();
    _toggleTableRowDetail(summary);
  });
}

function _toggleTableRowDetail(summary) {
  var detail = summary._detailRow || summary.nextElementSibling;
  if (!detail || !detail.classList.contains('job-table-detail')) return;
  var willExpand = detail.hasAttribute('hidden');
  if (willExpand) {
    detail.removeAttribute('hidden');
    detail.style.display = '';
  } else {
    detail.setAttribute('hidden', '');
    detail.style.display = 'none';
  }
  summary.setAttribute('aria-expanded', String(willExpand));
  summary.classList.toggle('is-expanded', willExpand);
  var chev = summary.querySelector('.row-chevron');
  if (chev) chev.textContent = willExpand ? '▾' : '▸';
}

function applySalesFilters() {
  var branch = _salesNormalize(document.getElementById('job-filter-branch') && document.getElementById('job-filter-branch').value);
  var plan = _salesNormalize(document.getElementById('job-filter-plan') && document.getElementById('job-filter-plan').value);
  var phase = _salesNormalize(document.getElementById('job-filter-phase') && document.getElementById('job-filter-phase').value);
  var year = _salesNormalize(document.getElementById('job-filter-year') && document.getElementById('job-filter-year').value);
  var sortMode = _salesNormalize(document.getElementById('job-filter-sort') && document.getElementById('job-filter-sort').value) || 'newest';

  // Search query — live-filter on the Closed tab only. Other panels
  // (In Progress, Leads) ignore the query box; their "Find Job" button
  // does navigate-to-match instead.
  var searchInput = document.getElementById('job-search-input');
  var searchQuery = _salesNormalize(searchInput && searchInput.value);

  _salesFilterTargets().forEach(function (target) {
    var panel = document.getElementById(target.panelId);
    if (!panel) return;

    // Search query gates the closed panel only.
    var panelQuery = (target.tab === 'closed') ? searchQuery : '';

    var panelVisibleCount = 0;
    panel.querySelectorAll('.project-group').forEach(function (group) {
      _salesSortGroupCards(group, sortMode);
      var visibleCount = 0;
      group.querySelectorAll('.proj-card[data-job-search]').forEach(function (card) {
        var matches = true;
        if (branch && _salesNormalize(card.dataset.branch) !== branch) matches = false;
        if (plan && _salesNormalize(card.dataset.plan) !== plan) matches = false;
        if (phase && _salesNormalize(card.dataset.phase) !== phase) matches = false;
        if (year && _salesNormalize(card.dataset.year) !== year) matches = false;
        if (panelQuery && (card.getAttribute('data-job-search') || '').indexOf(panelQuery) === -1) matches = false;
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
    // by default. We hide both in lockstep when a filter excludes the
    // job, otherwise the detail row stays orphaned beneath nothing.
    _salesSortTableRows(panel, sortMode);
    panel.querySelectorAll('.table-view tr.job-table-row').forEach(function (row) {
      var matches = true;
      if (branch && _salesNormalize(row.dataset.branch) !== branch) matches = false;
      if (plan && _salesNormalize(row.dataset.plan) !== plan) matches = false;
      if (phase && _salesNormalize(row.dataset.phase) !== phase) matches = false;
      if (year && _salesNormalize(row.dataset.year) !== year) matches = false;
      if (panelQuery && (row.getAttribute('data-job-search') || '').indexOf(panelQuery) === -1) matches = false;
      row.style.display = matches ? '' : 'none';
      var detail = row.nextElementSibling;
      if (detail && detail.classList.contains('job-table-detail')) {
        if (!matches) {
          // Filter excludes this job: hide both rows.
          detail.style.display = 'none';
        } else {
          // Filter includes this job: detail visibility follows the
          // expanded state stored in the [hidden] attribute.
          detail.style.display = detail.hasAttribute('hidden') ? 'none' : '';
        }
      }
    });

    var sectionCount = panel.querySelector('.group-section-title .group-section-count');
    if (sectionCount) sectionCount.textContent = '(' + panelVisibleCount + ')';

    // Empty state for the Closed tab when search yields zero matches.
    // We render an inline banner so the user knows their query ran but
    // matched nothing — otherwise they just see a blank panel.
    _updateClosedEmptyState(panel, target.tab, panelQuery, panelVisibleCount);
  });
}

function _updateClosedEmptyState(panel, tab, query, visibleCount) {
  if (tab !== 'closed') return;
  var existing = panel.querySelector('.search-empty-state');
  var shouldShow = query && visibleCount === 0;
  if (shouldShow) {
    if (!existing) {
      var msg = document.createElement('div');
      msg.className = 'banner banner-empty search-empty-state';
      msg.textContent = '';
      // Insert right after the section title (or at the top if missing)
      var sectionTitle = panel.querySelector('.group-section-title');
      if (sectionTitle && sectionTitle.nextSibling) {
        sectionTitle.parentNode.insertBefore(msg, sectionTitle.nextSibling);
      } else {
        panel.insertBefore(msg, panel.firstChild);
      }
      existing = msg;
    }
    existing.textContent = 'No closed contracts match "' + query + '".';
  } else if (existing) {
    existing.remove();
  }
}

// ── View toggle (Cards / Table) ──────────────────────────────────────
// Persists across navigation via localStorage. The CSS in browse.css
// controls visibility based on body class `view-mode-table`.
var SALES_VIEW_KEY = 'stmc-sales-view-mode';

function _applySalesViewMode(mode) {
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

function bindSalesViewToggle() {
  var cardsBtn = document.getElementById('job-view-cards');
  var tableBtn = document.getElementById('job-view-table');
  if (!cardsBtn || !tableBtn) return;
  var saved = null;
  try { saved = localStorage.getItem(SALES_VIEW_KEY); } catch (e) { /* private mode */ }
  _applySalesViewMode(saved === 'table' ? 'table' : 'cards');

  cardsBtn.addEventListener('click', function () {
    _applySalesViewMode('cards');
    try { localStorage.setItem(SALES_VIEW_KEY, 'cards'); } catch (e) {}
  });
  tableBtn.addEventListener('click', function () {
    _applySalesViewMode('table');
    try { localStorage.setItem(SALES_VIEW_KEY, 'table'); } catch (e) {}
  });
}

function bindSalesFilters() {
  ['job-filter-branch', 'job-filter-plan', 'job-filter-phase', 'job-filter-year', 'job-filter-sort'].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el || el.dataset.filterBound === '1') return;
    el.dataset.filterBound = '1';
    el.addEventListener('change', applySalesFilters);
  });
}

function bindSalesFilterRefreshOnSwap() {
  if (!window.htmx) return;
  document.body.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target) return;
    var watched = {
      'tab-leads-panel': true,
      'tab-in-progress-panel': true,
      'tab-closed-panel': true,
    };
    if (!watched[target.id]) return;
    rebuildSalesFilterOptions();
    bindSalesFilters();
    _bindRowDetailRefs();
    applySalesFilters();
  });
}

function init() {
  bindTabs();
  bindLogout();
  bindProjectToggles();
  bindFinalizeContractReload();
  bindSalesJobSearch();
  bindSalesFilters();
  bindSalesFilterRefreshOnSwap();
  bindSalesViewToggle();
  bindSalesTableRowToggle();
  _bindRowDetailRefs();
  rebuildSalesFilterOptions();
  applySalesFilters();
  initAuthHeader();
}

init();
