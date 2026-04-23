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

function initAuthHeader() {
  var user = window.STMC_USER || {};
  var nameEl = document.getElementById('hN');
  var badgeEl = document.getElementById('hA');
  if (nameEl) nameEl.textContent = user.name || '';
  if (badgeEl) badgeEl.textContent = user.initials || initials(user.name);
}

function init() {
  bindTabs();
  bindLogout();
  bindProjectToggles();
  initAuthHeader();
}

init();
