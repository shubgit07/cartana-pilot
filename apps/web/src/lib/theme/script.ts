// Inline script that runs *before* React hydrates. Reads the persisted
// theme preference (or system default) and adds the `dark` class to
// <html> so paint colors are correct on first render — no FOUC.

export const themeScript = `
(function () {
  try {
    var storageKey = 'cartana-theme';
    var stored = localStorage.getItem(storageKey);
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var resolved = stored === 'light' || stored === 'dark'
      ? stored
      : (prefersDark ? 'dark' : 'light');
    var root = document.documentElement;
    if (resolved === 'dark') root.classList.add('dark');
    else root.classList.remove('dark');
    root.style.colorScheme = resolved;
    root.dataset.theme = resolved;
  } catch (_) { /* localStorage unavailable */ }
})();
`.trim();
