// STMC Ops - Sales role JavaScript
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

function updateHeaderTitle(tab) {
  var titles = {
    projects: 'My Projects',
    models: 'Models',
    rates: 'Rate Card'
  };
  var titleEl = document.querySelector('.header-title');
  if (titleEl) titleEl.textContent = titles[tab] || 'Sales';
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
    projects: 'my-projects',
    models: 'models',
    rates: 'rates'
  };
  var navLink = document.querySelector('.app-nav-link[data-mv-tab="' + navMap[tab] + '"]');
  if (navLink) navLink.classList.add('active');

  updateHeaderTitle(tab);
  document.body.dispatchEvent(new CustomEvent('sales-' + tab + '-refresh'));

  var url = new URL(window.location.href);
  if (tab === 'projects') {
    url.searchParams.delete('tab');
  } else {
    url.searchParams.set('tab', tab);
  }
  window.history.replaceState({}, '', url.toString());
}

function bindTabs() {
  var tabByNav = {
    'my-projects': 'projects',
    models: 'models',
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

  var defaultTab = new URLSearchParams(window.location.search).get('tab') || 'projects';
  if (!document.getElementById('tab-' + defaultTab)) {
    defaultTab = 'projects';
  }
  activateTab(defaultTab);
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
  initAuthHeader();
}

init();
