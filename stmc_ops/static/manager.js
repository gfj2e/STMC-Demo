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

function activateTab(button, tab, options) {
  var shouldRefresh = !(options && options.refresh === false);
  document.querySelectorAll('.tab-panel').forEach(function (panel) {
    panel.style.display = 'none';
  });
  document.querySelectorAll('.app-nav-link[data-tab]').forEach(function (link) {
    link.classList.remove('active');
  });

  var target = document.getElementById('tab-' + tab);
  if (target) target.style.display = '';
  if (button) button.classList.add('active');
  setManagerSearchVisibility(tab);

  if (shouldRefresh) {
    document.body.dispatchEvent(new CustomEvent('manager-' + tab + '-refresh'));
  }
}

function setManagerSearchVisibility(tab) {
  var searchWrap = document.getElementById('job-search-wrap');
  if (!searchWrap) return;
  var visibleTabs = {
    'builds-active': true,
    'builds-closed': true,
  };
  searchWrap.style.display = visibleTabs[tab] ? 'flex' : 'none';
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
    if (event.detail.successful) {
      // The draw panel is swapped via hx-target, so explicitly clear the
      // shared modal host after a successful complete action.
      closeChangeOrderModal();
      return;
    }
    if (!event.detail.successful) {
      showToast('Error saving - try again');
      // Restore the button label if the request failed. On success the
      // server swaps #tab-draws-panel so the button element is replaced
      // entirely and this restore is moot.
      restoreCompleteLabel(elt);
    }
  });
}

function restoreCompleteLabel(form) {
  var label = form.querySelector('.btn-complete-label');
  if (label && label.dataset.originalLabel) {
    label.textContent = label.dataset.originalLabel;
  }
}

function bindCompleteBusyLabel() {
  // When the Mark Complete form fires off, swap the label to "Sending..."
  // so the PM gets immediate feedback that the click registered. Combined
  // with hx-disabled-elt on the button this gives us both visual busy
  // state AND hard debounce — impossible to double-submit.
  document.body.addEventListener('htmx:beforeRequest', function (event) {
    var elt = event.detail && event.detail.elt;
    if (!elt || !elt.matches('form[data-complete-form="1"]')) return;
    var button = elt.querySelector('.btn-complete');
    var label = elt.querySelector('.btn-complete-label');
    if (!button || !label) return;
    var busyText = button.getAttribute('data-busy-label') || 'Sending...';
    if (!label.dataset.originalLabel) {
      label.dataset.originalLabel = label.textContent;
    }
    label.textContent = busyText;
  });
}

function bindQbInvoiceToast() {
  // Fired by the server's HX-Trigger: {"qb-invoice-sent": {...}} response
  // header after manager_panel_mark_complete_view. Detail payload:
  //   { invoice_number, team, amount, status, url }
  // status is "sent" (real QB invoice) or "failed_fallback" (local only).
  document.body.addEventListener('qb-invoice-sent', function (event) {
    var d = (event && event.detail) || {};
    // Phase 4 refresh path supplies a pre-formatted `message`; prefer that
    // over the per-event invoice_number/team format used by mark-complete.
    if (d.message) {
      showToast(d.message);
      return;
    }
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

function closeChangeOrderModal() {
  var host = document.getElementById('manager-modal-host');
  if (host) host.innerHTML = '';
}

function bindChangeOrderModal() {
  // Close on overlay click (outside the inner .modal box) or Cancel button.
  document.addEventListener('click', function (event) {
    var cancel = event.target.closest('[data-co-cancel]');
    if (cancel) {
      event.preventDefault();
      closeChangeOrderModal();
      return;
    }
    var overlay = event.target.closest('[data-co-modal]');
    if (overlay && event.target === overlay) {
      closeChangeOrderModal();
    }
  });

  // Close on Esc.
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    if (document.querySelector('[data-co-modal]')) closeChangeOrderModal();
  });

  // Server fires a JSON HX-Trigger {"change-order-created": {...}} after a
  // successful POST. The response body re-renders #tab-builds-active-panel; we
  // close the modal here and show a confirmation toast.
  document.body.addEventListener('change-order-created', function (event) {
    var d = (event && event.detail) || {};
    closeChangeOrderModal();
    var amt = parseFloat((d.amount || '0').replace(/,/g, ''));
    var sign = amt < 0 ? '-' : '+';
    var pretty = Math.abs(amt).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    showToast(
      'Change Order #' + (d.number || '?') + ' added to ' +
      (d.customer || 'build') + ' (' + sign + '$' + pretty + ')'
    );
  });
}

function clearJobHit() {
  document.querySelectorAll('.job-search-hit').forEach(function (node) {
    node.classList.remove('job-search-hit');
  });
}

function findManagerJobMatch(query) {
  var targets = [
    { tab: 'builds-active', panelId: 'tab-builds-active-panel' },
    { tab: 'builds-closed', panelId: 'tab-builds-closed-panel' },
  ];

  for (var i = 0; i < targets.length; i++) {
    var target = targets[i];
    var panel = document.getElementById(target.panelId);
    if (!panel) continue;

    var cards = panel.querySelectorAll('.proj-card');
    for (var j = 0; j < cards.length; j++) {
      var card = cards[j];
      var haystack = (card.getAttribute('data-job-search') || card.textContent || '').toLowerCase();
      if (haystack.indexOf(query) !== -1) {
        return { target: target, card: card };
      }
    }
  }
  return null;
}

function openManagerFoundCard(card) {
  var details = card.closest('details');
  if (details) details.open = true;

  var body = card.querySelector('.proj-body');
  var chevron = card.querySelector('.chevron');
  if (body) body.classList.add('open');
  if (chevron) chevron.classList.add('open');
}

function runManagerJobSearch() {
  var input = document.getElementById('job-search-input');
  if (!input) return;

  var query = (input.value || '').trim().toLowerCase();
  if (!query) {
    showToast('Type a job name, order number, or branch to search');
    return;
  }

  clearJobHit();
  var match = findManagerJobMatch(query);
  if (!match) {
    showToast('No matching job found');
    return;
  }

  var button = document.querySelector('.app-nav-link[data-tab="' + match.target.tab + '"]');
  activateTab(button, match.target.tab, { refresh: false });
  openManagerFoundCard(match.card);
  match.card.classList.add('job-search-hit');
  match.card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setTimeout(function () {
    match.card.classList.remove('job-search-hit');
  }, 2200);
  showToast('Job found');
}

function bindJobSearch() {
  var button = document.getElementById('job-search-btn');
  var input = document.getElementById('job-search-input');
  if (!button || !input) return;

  button.addEventListener('click', runManagerJobSearch);
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      runManagerJobSearch();
    }
  });
}

function _managerNormalize(value) {
  return (value || '').toString().trim().toLowerCase();
}

function _managerFilterPanels() {
  return ['tab-builds-active-panel', 'tab-builds-closed-panel'];
}

function _managerFilterCards() {
  var cards = [];
  _managerFilterPanels().forEach(function (panelId) {
    var panel = document.getElementById(panelId);
    if (!panel) return;
    panel.querySelectorAll('.proj-card[data-job-search]').forEach(function (card) {
      cards.push(card);
    });
  });
  return cards;
}

function _managerPopulateFilterSelect(selectId, values, emptyLabel) {
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

function rebuildManagerFilterOptions() {
  var branches = new Set();
  var plans = new Set();
  var phases = new Set();
  var years = new Set();

  _managerFilterCards().forEach(function (card) {
    var branch = card.dataset.branch || '';
    var plan = card.dataset.plan || '';
    var phase = card.dataset.phase || '';
    var year = card.dataset.year || '';
    if (branch) branches.add(branch);
    if (plan) plans.add(plan);
    if (phase) phases.add(phase);
    if (year) years.add(year);
  });

  _managerPopulateFilterSelect('job-filter-branch', Array.from(branches).sort(), 'All branches');
  _managerPopulateFilterSelect('job-filter-plan', Array.from(plans).sort(), 'All plans');
  _managerPopulateFilterSelect('job-filter-phase', Array.from(phases).sort(), 'All phases');
  _managerPopulateFilterSelect(
    'job-filter-year',
    Array.from(years).sort(function (a, b) { return Number(b) - Number(a); }),
    'All years'
  );
}

function _managerCardSortValue(card) {
  var ts = Number(card.dataset.sortTs || 0);
  if (Number.isFinite(ts) && ts > 0) return ts;
  var order = String(card.dataset.order || '').replace(/\D/g, '');
  return Number(order || 0);
}

function _managerSortGroupCards(group, sortMode) {
  var body = group.querySelector('.project-group-body');
  if (!body) return;
  var cards = Array.from(body.querySelectorAll('.proj-card[data-job-search]'));
  cards.sort(function (a, b) {
    var av = _managerCardSortValue(a);
    var bv = _managerCardSortValue(b);
    return sortMode === 'oldest' ? av - bv : bv - av;
  });
  cards.forEach(function (card) { body.appendChild(card); });
}

function applyManagerFilters() {
  var branch = _managerNormalize(document.getElementById('job-filter-branch') && document.getElementById('job-filter-branch').value);
  var plan = _managerNormalize(document.getElementById('job-filter-plan') && document.getElementById('job-filter-plan').value);
  var phase = _managerNormalize(document.getElementById('job-filter-phase') && document.getElementById('job-filter-phase').value);
  var year = _managerNormalize(document.getElementById('job-filter-year') && document.getElementById('job-filter-year').value);
  var sortMode = _managerNormalize(document.getElementById('job-filter-sort') && document.getElementById('job-filter-sort').value) || 'newest';

  _managerFilterPanels().forEach(function (panelId) {
    var panel = document.getElementById(panelId);
    if (!panel) return;

    var panelVisibleCount = 0;
    panel.querySelectorAll('.project-group').forEach(function (group) {
      _managerSortGroupCards(group, sortMode);
      var visibleCount = 0;
      group.querySelectorAll('.proj-card[data-job-search]').forEach(function (card) {
        var matches = true;
        if (branch && _managerNormalize(card.dataset.branch) !== branch) matches = false;
        if (plan && _managerNormalize(card.dataset.plan) !== plan) matches = false;
        if (phase && _managerNormalize(card.dataset.phase) !== phase) matches = false;
        if (year && _managerNormalize(card.dataset.year) !== year) matches = false;
        card.style.display = matches ? '' : 'none';
        if (matches) visibleCount += 1;
      });

      var countEl = group.querySelector('.project-group-count');
      if (countEl) countEl.textContent = String(visibleCount);
      group.style.display = visibleCount ? '' : 'none';
      panelVisibleCount += visibleCount;
    });

    var sectionCount = panel.querySelector('.group-section-title .group-section-count');
    if (sectionCount) sectionCount.textContent = '(' + panelVisibleCount + ')';
  });
}

function bindManagerFilters() {
  ['job-filter-branch', 'job-filter-plan', 'job-filter-phase', 'job-filter-year', 'job-filter-sort'].forEach(function (id) {
    var el = document.getElementById(id);
    if (!el || el.dataset.filterBound === '1') return;
    el.dataset.filterBound = '1';
    el.addEventListener('change', applyManagerFilters);
  });
}

function bindManagerFilterRefreshOnSwap() {
  if (!window.htmx) return;
  document.body.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target) return;
    if (target.id !== 'tab-builds-active-panel' && target.id !== 'tab-builds-closed-panel') return;
    rebuildManagerFilterOptions();
    bindManagerFilters();
    applyManagerFilters();
  });
}

function init() {
  bindTabs();
  bindLogout();
  bindProjectToggles();
  bindHtmxFeedback();
  bindCompleteBusyLabel();
  bindQbInvoiceToast();
  bindChangeOrderModal();
  bindJobSearch();
  bindManagerFilters();
  bindManagerFilterRefreshOnSwap();
  rebuildManagerFilterOptions();
  applyManagerFilters();
  initAuthHeader();
  setManagerSearchVisibility('builds-active');
}

init();
