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
    if (!event.detail.successful) {
      showToast('Error saving - try again');
    }
  });
}

function bindQbInvoiceToast() {
  // Fired by the server's HX-Trigger: {"qb-invoice-sent": {...}} response
  // header after manager_panel_mark_complete_view. Detail payload:
  //   { invoice_number, team, amount, status, url }
  // status is "sent" (real QB invoice) or "failed_fallback" (local only).
  document.body.addEventListener('qb-invoice-sent', function (event) {
    var d = (event && event.detail) || {};
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

function init() {
  bindTabs();
  bindLogout();
  bindProjectToggles();
  bindHtmxFeedback();
  bindQbInvoiceToast();
  initAuthHeader();
}

init();
