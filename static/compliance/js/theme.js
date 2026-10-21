/* ═══════════════════════════════════════════════════════════
   Theme toggle — persists via localStorage, applies to <html>.
   ═══════════════════════════════════════════════════════════ */

(function () {
  const STORAGE_KEY = 'drc-expat-theme';
  const html = document.documentElement;

  function applyTheme(theme) {
    if (theme === 'dark') {
      html.setAttribute('data-theme', 'dark');
    } else {
      html.removeAttribute('data-theme');
    }
    const icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    const label = document.getElementById('theme-label');
    if (label) label.textContent = theme === 'dark' ? 'Light' : 'Dark';
  }

  // Initial apply (run before DOM ready to avoid flash)
  const saved = localStorage.getItem(STORAGE_KEY)
    || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  // Notify listeners (charts, etc.)
window.dispatchEvent(new Event('theme-changed'));
  applyTheme(saved);

  // Hook toggle
  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(saved);

    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      btn.addEventListener('click', function () {
        const current = html.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
      });
    }
  });
})();