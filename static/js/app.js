if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js').catch(function () {});
  });
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form input:not([type=checkbox]):not([type=radio]), form select, form textarea').forEach(function (el) {
    if (!el.classList.contains('form-control') && !el.classList.contains('form-select') && el.type !== 'color' && el.type !== 'hidden') {
      el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
    }
  });

  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebarOverlay');
  var toggle = document.getElementById('sidebarToggle');
  var closeBtn = document.getElementById('sidebarClose');

  function openSidebar() {
    document.body.classList.add('sidebar-open');
  }

  function closeSidebar() {
    document.body.classList.remove('sidebar-open');
  }

  if (toggle) toggle.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);

  if (sidebar) {
    sidebar.querySelectorAll('.sidebar-link').forEach(function (link) {
      link.addEventListener('click', function () {
        if (window.innerWidth < 992) closeSidebar();
      });
    });
  }
});
