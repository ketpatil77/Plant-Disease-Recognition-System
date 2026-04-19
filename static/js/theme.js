const THEME_KEY = 'agro-theme';
const root = document.documentElement;
const themeMeta = document.getElementById('themeColorMeta');

async function themeAriaLabel(theme) {
  const key = theme === 'light' ? 'app.theme.switch_dark' : 'app.theme.switch_light';
  if (typeof window.getTranslation === 'function') {
    return window.getTranslation(key);
  }
  return theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
}

function syncThemeMeta(theme) {
  if (!themeMeta) return;
  themeMeta.content = theme === 'light' ? '#f2f5fa' : '#0d1117';
}

function syncTheme(theme) {
  root.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
  syncThemeMeta(theme);
  document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
    btn.classList.toggle('is-light', theme === 'light');
    btn.classList.toggle('is-dark',  theme === 'dark');
    themeAriaLabel(theme).then(label => {
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
    });
  });
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'light' || saved === 'dark') {
    syncTheme(saved);
    return;
  }
  // Respect system preference as fallback
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  syncTheme(prefersDark ? 'dark' : 'light');
}

function toggleTheme() {
  syncTheme(root.dataset.theme === 'light' ? 'dark' : 'light');
}

document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
  btn.addEventListener('click', toggleTheme);
});

// Listen for OS-level theme changes if no preference stored
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
  if (!localStorage.getItem(THEME_KEY)) {
    syncTheme(e.matches ? 'dark' : 'light');
  }
});

document.addEventListener('agro:languagechange', () => {
  syncTheme(root.dataset.theme || 'dark');
});

initTheme();
