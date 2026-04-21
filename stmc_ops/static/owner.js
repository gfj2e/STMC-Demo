// STMC Ops - Owner role JavaScript
// window.LOGIN_URL must be set by the HTML template before this script runs.

const SEED = '/stmc_ops/app/seed-data/';
const LOGIN_URL = window.LOGIN_URL;

// Redirect immediately if no session
if (!localStorage.getItem('stmc_user')) {
  window.location.href = LOGIN_URL;
}

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
      localStorage.removeItem('stmc_user');
      localStorage.removeItem('stmc_region');
      window.location.href = LOGIN_URL;
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

async function initAuthHeader() {
  const userId = localStorage.getItem('stmc_user');
  const nameEl = document.getElementById('hN');
  const badgeEl = document.getElementById('hA');

  let name = userId;
  let initials = _initials(userId);

  try {
    const res = await fetch(SEED);
    if (res.ok) {
      const data = await res.json();
      const users = (data && data.users) || [];
      const user = users.find(u => u.id === userId);
      if (user) {
        name = user.name || name;
        initials = user.initials || _initials(name);
      }
    }
  } catch (err) {
    console.error(err);
  }

  if (nameEl) nameEl.textContent = name || '';
  if (badgeEl) badgeEl.textContent = initials || '?';
}

function init() {
  bindTabNavigation();
  bindLogout();
  bindProjectToggles();
  bindHtmxFeedback();
  initAuthHeader();
}

init();
