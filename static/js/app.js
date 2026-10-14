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
  var themeToggle = document.getElementById('themeToggle');

  function setTheme(theme) {
    var isDark = theme !== 'light';
    document.documentElement.dataset.bsTheme = isDark ? 'dark' : 'light';
    if (themeToggle) {
      themeToggle.setAttribute('aria-pressed', String(isDark));
      themeToggle.querySelector('.theme-toggle-label').textContent = isDark ? 'Тёмная тема' : 'Светлая тема';
      themeToggle.querySelector('.theme-toggle-icon i').className = isDark ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    }
    try { localStorage.setItem('ds-theme', isDark ? 'dark' : 'light'); } catch (e) {}
  }

  if (themeToggle) {
    setTheme(document.documentElement.dataset.bsTheme);
    themeToggle.addEventListener('click', function () {
      setTheme(document.documentElement.dataset.bsTheme === 'dark' ? 'light' : 'dark');
    });
  }

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
