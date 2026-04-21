// STMC Ops - Manager role JavaScript
// window.LOGIN_URL must be set by the HTML template before this script runs.

const SEED = '/stmc_ops/app/seed-data/';
const LOGIN_URL = window.LOGIN_URL;

if (!localStorage.getItem('stmc_user')) {
  window.location.href = LOGIN_URL;
}

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

function activateTab(button, tab) {
  document.querySelectorAll('.tab-panel').forEach(function (panel) {
    panel.style.display = 'none';
  });
  document.querySelectorAll('.app-nav-link[data-tab]').forEach(function (link) {
    link.classList.remove('active');
  });

  var target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';
  if (button) button.classList.add('active');

  document.body.dispatchEvent(new CustomEvent('manager-' + tab + '-refresh'));
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
      localStorage.removeItem('stmc_user');
      localStorage.removeItem('stmc_region');
      window.location.href = LOGIN_URL;
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

  document.body.addEventListener('htmx:afterRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-complete-form="1"]')) return;

    if (event.detail.successful) {
      showToast('Draw marked complete');
      return;
    }
    showToast('Error saving - try again');
  });
}

function initAuthHeader() {
  var userId = localStorage.getItem('stmc_user');
  var nameEl = document.getElementById('hN');
  var badgeEl = document.getElementById('hA');

  var displayName = userId;
  var displayInitials = initials(userId);

  fetch(SEED)
    .then(function (response) {
      if (!response.ok) return null;
      return response.json();
    })
    .then(function (data) {
      if (!data) return;
      var users = data.users || [];
      var user = users.find(function (item) {
        return item.id === userId;
      });
      if (!user) return;

      displayName = user.name || displayName;
      displayInitials = user.initials || initials(displayName);
    })
    .catch(function () {
      // Keep localStorage fallback values.
    })
    .finally(function () {
      if (nameEl) nameEl.textContent = displayName || '';
      if (badgeEl) badgeEl.textContent = displayInitials || '?';
    });
}

function init() {
  bindTabs();
  bindLogout();
  bindProjectToggles();
  bindHtmxFeedback();
  initAuthHeader();
}

init();
