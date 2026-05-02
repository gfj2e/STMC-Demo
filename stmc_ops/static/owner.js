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

  if (shouldRefresh) {
    document.body.dispatchEvent(new CustomEvent('owner-' + tab + '-refresh'));
  }
}

function setOwnerSearchVisibility(tab) {
  const searchWrap = document.getElementById('job-search-wrap');
  if (!searchWrap) return;
  const visibleTabs = {
    'projects-closed': true,
  };
  searchWrap.style.display = visibleTabs[tab] ? 'flex' : 'none';
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

  document.body.addEventListener('htmx:afterSwap', event => {
    const target = event.detail && event.detail.target;
    if (!target) return;
    if (target.id === 'tab-dashboard-panel') {
      initExecDashboard();
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
  const targets = [
    { tab: 'projects-closed', panelId: 'tab-projects-closed-panel' },
  ];

  for (const target of targets) {
    const panel = document.getElementById(target.panelId);
    if (!panel) continue;
    const cards = panel.querySelectorAll('.card');
    for (const card of cards) {
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

  const details = match.card.closest('details');
  if (details) details.open = true;

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
  return ['tab-projects-closed-panel'];
}

function _ownerFilterCards() {
  const cards = [];
  _ownerFilterPanels().forEach(panelId => {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.querySelectorAll('.card[data-job-search]').forEach(card => {
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
      group.querySelectorAll('.card[data-job-search]').forEach(card => {
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

    const sectionCount = panel.querySelector('.group-section-title .group-section-count');
    if (sectionCount) sectionCount.textContent = '(' + panelVisibleCount + ')';
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
    if (target.id !== 'tab-projects-closed-panel') return;
    rebuildOwnerFilterOptions();
    bindOwnerFilters();
    applyOwnerFilters();
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
  rebuildOwnerFilterOptions();
  applyOwnerFilters();
  initAuthHeader();
  initExecDashboard();
  setOwnerSearchVisibility('dashboard');
}

init();
