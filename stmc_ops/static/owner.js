// STMC Ops - Owner role JavaScript
// Auth is handled server-side (Django session + @role_required).
// Template injects window.STMC_USER / LOGIN_URL / LOGOUT_URL / CSRF_TOKEN.

const LOGIN_URL = window.LOGIN_URL;
const LOGOUT_URL = window.LOGOUT_URL;

function _initials(name) {
  return (name || '').split(/\s+/).map(w => w[0] || '').join('').toUpperCase().slice(0, 2) || '?';
}

function switchTab(btn, tab, options) {
  var shouldRefresh = !(options && options.refresh === false);
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.style.display = 'none';
  });
  document.querySelectorAll('.app-nav-link').forEach(link => {
    link.classList.remove('active');
  });

  const target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';
  if (btn) btn.classList.add('active');
  setOwnerSearchVisibility(tab);
  placeOwnerViewToggle(tab);

  if (shouldRefresh) {
    document.body.dispatchEvent(new CustomEvent('owner-' + tab + '-refresh'));
  }
}

function setOwnerSearchVisibility(tab) {
  const searchWrap = document.getElementById('job-search-wrap');
  if (searchWrap) {
    const searchTabs = { 'dashboard': true, 'projects-closed': true };
    searchWrap.style.display = searchTabs[tab] ? 'flex' : 'none';
  }
  const toggle = document.querySelector('.job-view-toggle');
  if (toggle) {
    const toggleTabs = { 'dashboard': true, 'projects-closed': true };
    toggle.style.display = toggleTabs[tab] ? 'inline-flex' : 'none';
  }
}

function _ownerActiveTab() {
  const active = document.querySelector('.app-nav-link.active[data-tab]');
  return active ? active.dataset.tab : 'dashboard';
}

function parkOwnerViewToggle() {
  const toggle = document.querySelector('.job-view-toggle');
  const home = document.getElementById('owner-view-toggle-home');
  if (!toggle || !home) return;
  if (toggle.parentNode !== home) {
    home.appendChild(toggle);
  }
}

function placeOwnerViewToggle(tab) {
  const toggle = document.querySelector('.job-view-toggle');
  if (!toggle) return;

  const activeTab = tab || _ownerActiveTab();
  const anchorId = activeTab === 'projects-closed'
    ? 'owner-closed-view-toggle-anchor'
    : 'owner-dashboard-view-toggle-anchor';
  const anchor = document.getElementById(anchorId);
  if (!anchor || !anchor.parentNode) {
    parkOwnerViewToggle();
    return;
  }

  // Keep a single toggle instance in the DOM and move it right under
  // the current panel's anchor (above the section header).
  anchor.insertAdjacentElement('afterend', toggle);
}

function bindTabNavigation() {
  document.querySelectorAll('.app-nav-link[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn, btn.dataset.tab);
    });
  });
}

function bindLogout() {
  document.querySelectorAll('.logout-link').forEach(btn => {
    btn.addEventListener('click', () => {
      fetch(LOGOUT_URL, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': window.CSRF_TOKEN },
      }).finally(() => { window.location.href = LOGIN_URL; });
    });
  });
}

function bindProjectToggles() {
  document.addEventListener('click', event => {
    const header = event.target.closest('.proj-hdr');
    if (!header) return;

    const body = header.nextElementSibling;
    const chevron = header.querySelector('.chevron');
    if (body) body.classList.toggle('open');
    if (chevron) chevron.classList.toggle('open');
  });
}

function _clampWidth(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, number));
}

function applyExecDataWidths(root) {
  (root || document).querySelectorAll('[data-width-pct]').forEach(el => {
    el.style.width = _clampWidth(el.dataset.widthPct) + '%';
  });
}

function toggleExecJob(jobId, forceOpen) {
  const detail = document.getElementById('exec-job-body-' + jobId);
  const arrow = document.querySelector('[data-exec-arrow="' + jobId + '"]');
  const trigger = document.querySelector('[data-exec-toggle="' + jobId + '"]');
  if (!detail) return;

  const shouldOpen = (typeof forceOpen === 'boolean') ? forceOpen : !detail.classList.contains('open');
  detail.classList.toggle('open', shouldOpen);
  if (arrow) arrow.classList.toggle('open', shouldOpen);
  if (trigger) trigger.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
}

function activateExecTab(jobId, tabName) {
  const tabs = document.querySelectorAll('.exec-tab[data-job-id="' + jobId + '"]');
  const panels = document.querySelectorAll('.exec-tab-panel[data-job-id="' + jobId + '"]');
  tabs.forEach(tab => {
    tab.classList.toggle('is-active', tab.dataset.jobTab === tabName);
  });
  panels.forEach(panel => {
    panel.hidden = panel.dataset.jobPanel !== tabName;
  });
}

function bindExecDashboardEvents() {
  document.addEventListener('click', event => {
    const toggle = event.target.closest('[data-exec-toggle]');
    if (toggle) {
      toggleExecJob(toggle.dataset.execToggle);
      return;
    }

    const tab = event.target.closest('.exec-tab');
    if (tab) {
      activateExecTab(tab.dataset.jobId, tab.dataset.jobTab);
    }
  });
}

function initExecDashboard() {
  const dashboardPanel = document.getElementById('tab-dashboard-panel');
  if (!dashboardPanel) return;

  applyExecDataWidths(dashboardPanel);

  const firstCard = dashboardPanel.querySelector('.exec-job-card[data-exec-job-id]');
  if (!firstCard) return;

  const jobId = firstCard.dataset.execJobId;
  if (!dashboardPanel.querySelector('.exec-detail.open')) {
    toggleExecJob(jobId, true);
  }
  activateExecTab(jobId, 'bills');
}

function bindHtmxFeedback() {
  if (!window.htmx) return;

  document.body.addEventListener('htmx:beforeSwap', event => {
    const target = event.detail && event.detail.target;
    if (!target) return;
    if (target.id === 'tab-dashboard-panel' || target.id === 'tab-projects-closed-panel') {
      parkOwnerViewToggle();
    }
  });

  document.body.addEventListener('htmx:afterSwap', event => {
    const target = event.detail && event.detail.target;
    if (!target) return;
    if (target.id === 'tab-dashboard-panel') {
      initExecDashboard();
      placeOwnerViewToggle('dashboard');
    }
    // When the bell button reloads (30s poll OR explicit refresh), compare
    // the unread count to the previous tick. A bump = a new invoice landed
    // while the exec is on the page — fire a toast for the "it just
    // happened" feel, matching what the PM sees on the manager side.
    if (target.id === 'owner-bell-wrap') {
      handleBellRefresh(target);
    }
  });

  // QB Sync refresh: swap the button label while the pull is in-flight
  // so the exec sees "Refreshing..." instead of a silent hang while QB
  // takes a second or two to answer.
  document.body.addEventListener('htmx:beforeRequest', event => {
    const elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-qb-refresh-form="1"]')) return;
    const button = elt.querySelector('button[data-busy-label]');
    const label = elt.querySelector('.qb-btn-label');
    if (!button || !label) return;
    const busy = button.getAttribute('data-busy-label') || 'Refreshing...';
    if (!label.dataset.originalLabel) label.dataset.originalLabel = label.textContent;
    label.textContent = busy;
  });

  // After the server returns a JSON HX-Trigger with qb-sync-refreshed
  // details, fire a toast summarizing the result.
  document.body.addEventListener('qb-sync-refreshed', event => {
    const d = (event && event.detail) || {};
    if (d.status === 'ok') {
      showToast('QuickBooks synced — $' + (d.payments || '0') + ' pulled');
    } else if (d.status === 'stale') {
      showToast('QuickBooks sync failed — showing last known values');
    } else {
      showToast('QuickBooks is not connected');
    }
  });
}

// ── Toast ───────────────────────────────────────────────────
// Copy of manager.js showToast (same shape, same 3.2s fade) so the
// QB-invoice live indicator reads identically across roles.

function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => { toast.classList.remove('show'); }, 3200);
}

// ── Bell dropdown ───────────────────────────────────────────

let _lastBellCount = null;  // tracks unread count across 30s polls

function handleBellRefresh(wrap) {
  const btn = wrap.querySelector('.bell-btn');
  if (!btn) return;
  const count = Number(btn.dataset.unreadCount || 0);
  if (_lastBellCount !== null && count > _lastBellCount) {
    // New invoice arrived since the previous poll — surface it live.
    showToast('New QuickBooks invoice received');
  }
  _lastBellCount = count;
}

window.toggleBellDropdown = function () {
  const dropdown = document.getElementById('owner-bell-dropdown');
  if (!dropdown) return;
  dropdown.classList.toggle('bell-dropdown-open');
};

function closeBellDropdown() {
  const dropdown = document.getElementById('owner-bell-dropdown');
  if (!dropdown) return;
  dropdown.classList.remove('bell-dropdown-open');
}

function bindBellClickOutside() {
  // Auto-close the dropdown when the user clicks anywhere else. We ignore
  // clicks inside the bell container (the button itself, dropdown rows,
  // mark-read forms) so interactions there don't self-dismiss.
  document.addEventListener('click', event => {
    const inBell = event.target.closest('.bell-container');
    if (!inBell) closeBellDropdown();
  });

  // Also close on Escape for keyboard users.
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeBellDropdown();
  });
}

function clearJobHit() {
  document.querySelectorAll('.job-search-hit').forEach(node => {
    node.classList.remove('job-search-hit');
  });
}

function findOwnerJobMatch(query) {
  // Search whichever rendering is currently visible. In cards mode look
  // at the card elements (.card on legacy templates, .exec-job-card on
  // the dashboard / closed-projects rewrites); in table mode look at
  // tr.job-table-row. All three carry data-job-search so the lookup is
  // identical.
  const inTableMode = document.body.classList.contains('view-mode-table');
  const selector = inTableMode
    ? '.table-view tr.job-table-row[data-job-search]'
    : '.cards-view .card[data-job-search], .cards-view .exec-job-card[data-job-search]';
  const targets = [
    { tab: 'dashboard', panelId: 'tab-dashboard-panel' },
    { tab: 'projects-closed', panelId: 'tab-projects-closed-panel' },
  ];

  // Prefer the tab the user is on so a search from Active stays on
  // Active rather than jumping to Closed (and vice versa).
  const activeTab = _ownerActiveTab();
  if (activeTab) {
    targets.sort((a, b) => {
      if (a.tab === activeTab) return -1;
      if (b.tab === activeTab) return 1;
      return 0;
    });
  }

  for (const target of targets) {
    const panel = document.getElementById(target.panelId);
    if (!panel) continue;
    const nodes = panel.querySelectorAll(selector);
    for (const card of nodes) {
      const haystack = (card.getAttribute('data-job-search') || card.textContent || '').toLowerCase();
      if (haystack.includes(query)) {
        return { target, card };
      }
    }
  }
  return null;
}

function runOwnerJobSearch() {
  const input = document.getElementById('job-search-input');
  if (!input) return;

  const query = (input.value || '').trim().toLowerCase();
  if (!query) {
    showToast('Type a job name, order number, or branch to search');
    return;
  }

  clearJobHit();
  const match = findOwnerJobMatch(query);
  if (!match) {
    showToast('No matching job found');
    return;
  }

  const button = document.querySelector('.app-nav-link[data-tab="' + match.target.tab + '"]');
  switchTab(button, match.target.tab, { refresh: false });

  if (match.card.classList.contains('job-table-row')) {
    const detail = match.card._detailRow || match.card.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail') && detail.hasAttribute('hidden')) {
      _toggleOwnerTableRowDetail(match.card);
    }
  } else {
    const details = match.card.closest('details');
    if (details) details.open = true;
    // Expand the .exec-job-card body if it has the expand affordance.
    const toggleBtn = match.card.querySelector('[data-exec-toggle]');
    if (toggleBtn && toggleBtn.getAttribute('aria-expanded') !== 'true') {
      toggleBtn.click();
    }
  }

  match.card.classList.add('job-search-hit');
  match.card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(() => {
    match.card.classList.remove('job-search-hit');
  }, 2200);
  showToast('Job found');
}

function bindJobSearch() {
  const button = document.getElementById('job-search-btn');
  const input = document.getElementById('job-search-input');
  if (!button || !input) return;

  button.addEventListener('click', runOwnerJobSearch);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runOwnerJobSearch();
    }
  });
}

function _ownerNormalize(value) {
  return (value || '').toString().trim().toLowerCase();
}

function _ownerFilterPanels() {
  return ['tab-dashboard-panel', 'tab-projects-closed-panel'];
}

function _ownerFilterCards() {
  // Active dashboard cards are .exec-job-card; closed-project cards are
  // also .exec-job-card (after the rewrite that gave closed contracts the
  // same tabbed detail). Both carry data-job-search + data-branch / plan
  // / phase / year so filters apply uniformly.
  const cards = [];
  _ownerFilterPanels().forEach(panelId => {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.querySelectorAll('.card[data-job-search], .exec-job-card[data-job-search]').forEach(card => {
      cards.push(card);
    });
  });
  return cards;
}

function _ownerPopulateFilterSelect(selectId, values, emptyLabel) {
  const select = document.getElementById(selectId);
  if (!select) return;
  const selected = select.value;
  const options = ['<option value="' + '' + '">' + emptyLabel + '</option>'];
  values.forEach(value => {
    options.push('<option value="' + value + '">' + value + '</option>');
  });
  select.innerHTML = options.join('');
  select.value = values.includes(selected) ? selected : '';
}

function rebuildOwnerFilterOptions() {
  const branches = new Set();
  const plans = new Set();
  const phases = new Set();
  const years = new Set();

  _ownerFilterCards().forEach(card => {
    const branch = card.dataset.branch || '';
    const plan = card.dataset.plan || '';
    const phase = card.dataset.phase || '';
    const year = card.dataset.year || '';
    if (branch) branches.add(branch);
    if (plan) plans.add(plan);
    if (phase) phases.add(phase);
    if (year) years.add(year);
  });

  _ownerPopulateFilterSelect('job-filter-branch', Array.from(branches).sort(), 'All branches');
  _ownerPopulateFilterSelect('job-filter-plan', Array.from(plans).sort(), 'All plans');
  _ownerPopulateFilterSelect('job-filter-phase', Array.from(phases).sort(), 'All phases');
  _ownerPopulateFilterSelect(
    'job-filter-year',
    Array.from(years).sort((a, b) => Number(b) - Number(a)),
    'All years'
  );
}

function _ownerCardSortValue(card) {
  const ts = Number(card.dataset.sortTs || 0);
  if (Number.isFinite(ts) && ts > 0) return ts;
  const order = String(card.dataset.order || '').replace(/\D/g, '');
  return Number(order || 0);
}

function _ownerSortGroupCards(group, sortMode) {
  const body = group.querySelector('.project-group-body');
  if (!body) return;
  const cards = Array.from(body.querySelectorAll('.card[data-job-search]'));
  cards.sort((a, b) => {
    const av = _ownerCardSortValue(a);
    const bv = _ownerCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  cards.forEach(card => body.appendChild(card));
}

function _ownerSortTableRows(panel, sortMode) {
  // Each project is TWO rows (summary + detail). Sort moves them as a
  // pair so an expanded detail row stays beneath its own summary.
  const tbody = panel.querySelector('.table-view tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr.job-table-row'));
  rows.sort((a, b) => {
    const av = _ownerCardSortValue(a);
    const bv = _ownerCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  rows.forEach(row => {
    tbody.appendChild(row);
    if (row._detailRow) tbody.appendChild(row._detailRow);
  });
}

function applyOwnerFilters() {
  const branch = _ownerNormalize(document.getElementById('job-filter-branch') && document.getElementById('job-filter-branch').value);
  const plan = _ownerNormalize(document.getElementById('job-filter-plan') && document.getElementById('job-filter-plan').value);
  const phase = _ownerNormalize(document.getElementById('job-filter-phase') && document.getElementById('job-filter-phase').value);
  const year = _ownerNormalize(document.getElementById('job-filter-year') && document.getElementById('job-filter-year').value);
  const sortMode = _ownerNormalize(document.getElementById('job-filter-sort') && document.getElementById('job-filter-sort').value) || 'newest';

  _ownerFilterPanels().forEach(panelId => {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    let panelVisibleCount = 0;
    panel.querySelectorAll('.project-group').forEach(group => {
      _ownerSortGroupCards(group, sortMode);
      let visibleCount = 0;
      group.querySelectorAll('.card[data-job-search], .exec-job-card[data-job-search]').forEach(card => {
        let matches = true;
        if (branch && _ownerNormalize(card.dataset.branch) !== branch) matches = false;
        if (plan && _ownerNormalize(card.dataset.plan) !== plan) matches = false;
        if (phase && _ownerNormalize(card.dataset.phase) !== phase) matches = false;
        if (year && _ownerNormalize(card.dataset.year) !== year) matches = false;
        card.style.display = matches ? '' : 'none';
        if (matches) visibleCount += 1;
      });

      const countEl = group.querySelector('.project-group-count');
      if (countEl) countEl.textContent = String(visibleCount);
      group.style.display = visibleCount ? '' : 'none';
      panelVisibleCount += visibleCount;
    });

    // Active dashboard renders cards flat (no <details> wrapper), so
    // also filter direct .exec-job-card descendants of .cards-view that
    // are not inside any group.
    panel.querySelectorAll('.cards-view > .exec-job-card[data-job-search]').forEach(card => {
      let matches = true;
      if (branch && _ownerNormalize(card.dataset.branch) !== branch) matches = false;
      if (plan && _ownerNormalize(card.dataset.plan) !== plan) matches = false;
      if (phase && _ownerNormalize(card.dataset.phase) !== phase) matches = false;
      if (year && _ownerNormalize(card.dataset.year) !== year) matches = false;
      card.style.display = matches ? '' : 'none';
      if (matches) panelVisibleCount += 1;
    });

    // Mirror the same filter on the flat table view. Each job has TWO
    // <tr>s (summary + paired detail hidden by default). Hide both
    // together when a filter excludes the job.
    _ownerSortTableRows(panel, sortMode);
    panel.querySelectorAll('.table-view tr.job-table-row').forEach(row => {
      let matches = true;
      if (branch && _ownerNormalize(row.dataset.branch) !== branch) matches = false;
      if (plan && _ownerNormalize(row.dataset.plan) !== plan) matches = false;
      if (phase && _ownerNormalize(row.dataset.phase) !== phase) matches = false;
      if (year && _ownerNormalize(row.dataset.year) !== year) matches = false;
      row.style.display = matches ? '' : 'none';
      const detail = row.nextElementSibling;
      if (detail && detail.classList.contains('job-table-detail')) {
        // Filter excludes: hide via inline display. Filter includes: clear
        // the override and let CSS drive the open/close transition off
        // [hidden].
        detail.style.display = matches ? '' : 'none';
      }
    });

    const sectionCount = panel.querySelector('.group-section-title .group-section-count');
    if (sectionCount) sectionCount.textContent = '(' + panelVisibleCount + ')';
  });
}

// ── Table-row expand / collapse (delegated) ─────────────────────────
function _bindOwnerRowDetailRefs() {
  document.querySelectorAll('.table-view tr.job-table-row').forEach(row => {
    const detail = row.nextElementSibling;
    if (detail && detail.classList.contains('job-table-detail')) {
      row._detailRow = detail;
    }
  });
}

function _toggleOwnerTableRowDetail(summary) {
  const detail = summary._detailRow || summary.nextElementSibling;
  if (!detail || !detail.classList.contains('job-table-detail')) return;
  const willExpand = detail.hasAttribute('hidden');
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
  const chev = summary.querySelector('.row-chevron');
  if (chev) chev.textContent = willExpand ? '▾' : '▸';

  // The expanded detail card may contain widths driven by data-width-pct
  // (budget bars). Apply now that the row is visible.
  if (willExpand && typeof applyExecDataWidths === 'function') {
    applyExecDataWidths(detail);
  }
}

function bindOwnerTableRowToggle() {
  document.addEventListener('click', event => {
    const summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    if (event.target.closest('a, button, input, select, label, .exec-tab')) return;
    _toggleOwnerTableRowDetail(summary);
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const summary = event.target.closest('tr.job-table-row');
    if (!summary) return;
    event.preventDefault();
    _toggleOwnerTableRowDetail(summary);
  });
}

// ── View toggle (Table / Cards) ─────────────────────────────────────
// Persists across navigation via localStorage. CSS controls visibility
// based on body class `view-mode-table`. Default for the owner role is
// table mode (matches the rest of the suite's expected behavior).
const OWNER_VIEW_KEY = 'stmc-owner-view-mode';

function _applyOwnerViewMode(mode) {
  const isTable = mode === 'table';
  document.body.classList.toggle('view-mode-table', isTable);
  const cardsBtn = document.getElementById('job-view-cards');
  const tableBtn = document.getElementById('job-view-table');
  if (cardsBtn) {
    cardsBtn.classList.toggle('active', !isTable);
    cardsBtn.setAttribute('aria-pressed', String(!isTable));
  }
  if (tableBtn) {
    tableBtn.classList.toggle('active', isTable);
    tableBtn.setAttribute('aria-pressed', String(isTable));
  }
}

function bindOwnerViewToggle() {
  const cardsBtn = document.getElementById('job-view-cards');
  const tableBtn = document.getElementById('job-view-table');
  if (!cardsBtn || !tableBtn) return;

  // Owner default: always land on table mode when opening the page.
  _applyOwnerViewMode('table');
  try { localStorage.setItem(OWNER_VIEW_KEY, 'table'); } catch (e) { /* private mode */ }

  cardsBtn.addEventListener('click', () => {
    _applyOwnerViewMode('cards');
    try { localStorage.setItem(OWNER_VIEW_KEY, 'cards'); } catch (e) {}
  });
  tableBtn.addEventListener('click', () => {
    _applyOwnerViewMode('table');
    try { localStorage.setItem(OWNER_VIEW_KEY, 'table'); } catch (e) {}
  });
}

function bindOwnerFilters() {
  ['job-filter-branch', 'job-filter-plan', 'job-filter-phase', 'job-filter-year', 'job-filter-sort'].forEach(id => {
    const el = document.getElementById(id);
    if (!el || el.dataset.filterBound === '1') return;
    el.dataset.filterBound = '1';
    el.addEventListener('change', applyOwnerFilters);
  });
}

function bindOwnerFilterRefreshOnSwap() {
  if (!window.htmx) return;
  document.body.addEventListener('htmx:afterSwap', event => {
    const target = event.detail && event.detail.target;
    if (!target) return;
    if (target.id === 'tab-projects-closed-panel') {
      rebuildOwnerFilterOptions();
      bindOwnerFilters();
      // Cache summary→detail refs BEFORE applyOwnerFilters runs, because
      // its internal _ownerSortTableRows uses row._detailRow to keep each
      // detail row paired with its summary during reorder. Without this,
      // sort moves only summary rows and the pairing breaks — clicking
      // a row then expands the wrong sibling.
      _bindOwnerRowDetailRefs();
      applyOwnerFilters();
      placeOwnerViewToggle('projects-closed');
    }
    if (target.id === 'tab-dashboard-panel') {
      rebuildOwnerFilterOptions();
      bindOwnerFilters();
      _bindOwnerRowDetailRefs();
      applyOwnerFilters();
      placeOwnerViewToggle('dashboard');
    }
  });
}

function initAuthHeader() {
  const user = window.STMC_USER || {};
  const nameEl = document.getElementById('hN');
  const badgeEl = document.getElementById('hA');
  if (nameEl) nameEl.textContent = user.name || '';
  if (badgeEl) badgeEl.textContent = user.initials || _initials(user.name);
}

function init() {
  bindTabNavigation();
  bindLogout();
  bindProjectToggles();
  bindExecDashboardEvents();
  bindHtmxFeedback();
  bindBellClickOutside();
  bindJobSearch();
  bindOwnerFilters();
  bindOwnerFilterRefreshOnSwap();
  bindOwnerTableRowToggle();
  bindOwnerViewToggle();
  rebuildOwnerFilterOptions();
  applyOwnerFilters();
  initAuthHeader();
  initExecDashboard();
  setOwnerSearchVisibility('dashboard');
  placeOwnerViewToggle('dashboard');
}

init();
