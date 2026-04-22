// STMC Ops - Owner role JavaScript
// Auth is handled server-side (Django session + @role_required).
// Template injects window.STMC_USER / LOGIN_URL / LOGOUT_URL / CSRF_TOKEN.

const LOGIN_URL = window.LOGIN_URL;
const LOGOUT_URL = window.LOGOUT_URL;

function _initials(name) {
  return (name || '').split(/\s+/).map(w => w[0] || '').join('').toUpperCase().slice(0, 2) || '?';
}

function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;

  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove('show'), 3200);
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

function bindHtmxFeedback() {
  if (!window.htmx) return;

  document.body.addEventListener('htmx:afterRequest', event => {
    const elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-complete-form="1"]')) return;

    if (event.detail.successful) {
      showToast('Draw marked complete');
    } else {
      showToast('Error saving - try again');
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
  bindHtmxFeedback();
  initAuthHeader();
}

init();
