// STMC Ops - Owner role JavaScript
// Auth is handled server-side (Django session + @role_required).
// Template injects window.STMC_USER / LOGIN_URL / LOGOUT_URL / CSRF_TOKEN.

const LOGIN_URL = window.LOGIN_URL;
const LOGOUT_URL = window.LOGOUT_URL;

function _initials(name) {
  return (name || '').split(/\s+/).map(w => w[0] || '').join('').toUpperCase().slice(0, 2) || '?';
}

function switchTab(btn, tab) {
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.style.display = 'none';
  });
  document.querySelectorAll('.app-nav-link').forEach(link => {
    link.classList.remove('active');
  });

  const target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';
  if (btn) btn.classList.add('active');

  document.body.dispatchEvent(new CustomEvent('owner-' + tab + '-refresh'));
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
  initAuthHeader();
  initExecDashboard();
}

init();
