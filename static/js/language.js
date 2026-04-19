const LANG_KEY = 'agro-lang';
const DEFAULT_LANG = 'mr';
let currentLang = localStorage.getItem(LANG_KEY) || DEFAULT_LANG;
let cache = {};

async function loadTranslations(lang) {
  if (cache[lang]) return cache[lang];
  const file = lang === 'en' ? 'eng' : 'mar';
  try {
    const res = await fetch(`/static/lang/${file}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    cache[lang] = data;
    return data;
  } catch (err) {
    console.warn('Translation load failed:', err);
    return null;
  }
}

function applyTranslations(dict) {
  if (!dict) return;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    const val = dict[key];
    if (val != null) el.textContent = val;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    const val = dict[key];
    if (val != null) el.placeholder = val;
  });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    const key = el.dataset.i18nAria;
    const val = dict[key];
    if (val != null) el.setAttribute('aria-label', val);
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.dataset.i18nTitle;
    const val = dict[key];
    if (val != null) el.setAttribute('title', val);
  });
  document.querySelectorAll('[data-i18n-alt]').forEach(el => {
    const key = el.dataset.i18nAlt;
    const val = dict[key];
    if (val != null) el.setAttribute('alt', val);
  });
  document.querySelectorAll('[data-i18n-content]').forEach(el => {
    const key = el.dataset.i18nContent;
    const val = dict[key];
    if (val != null) el.setAttribute('content', val);
  });
  document.querySelectorAll('[data-i18n-value]').forEach(el => {
    const key = el.dataset.i18nValue;
    const val = dict[key];
    if (val != null) el.value = val;
  });
  document.documentElement.lang = currentLang === 'en' ? 'en' : 'mr';
  document.documentElement.dataset.language = currentLang;
  // Sync lang-toggle buttons
  document.querySelectorAll('[data-lang]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLang);
  });
  // Sync settings radio inputs
  document.querySelectorAll('[data-lang-option]').forEach(input => {
    input.checked = input.value === currentLang;
  });
}

async function refreshLanguage() {
  const dict = await loadTranslations(currentLang);
  applyTranslations(dict);
  document.dispatchEvent(new CustomEvent('agro:translationsapplied', { detail: { lang: currentLang, dict } }));
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem(LANG_KEY, lang);
  refreshLanguage();
  document.dispatchEvent(new CustomEvent('agro:languagechange', { detail: { lang } }));
}

document.addEventListener('DOMContentLoaded', () => {
  // Preload both languages to warm cache
  loadTranslations(currentLang);

  refreshLanguage();

  document.querySelectorAll('[data-lang]').forEach(btn => {
    btn.addEventListener('click', () => setLang(btn.dataset.lang));
  });

  document.querySelectorAll('[data-lang-option]').forEach(input => {
    input.addEventListener('change', () => {
      if (input.checked) setLang(input.value);
    });
  });
});

// Expose globally for other scripts
window.getCurrentLang = () => currentLang;
window.getTranslation = async function(key, vars) {
  const dict = await loadTranslations(currentLang);
  let value = dict?.[key] ?? key;
  if (vars && value && typeof value === 'string') {
    Object.entries(vars).forEach(([name, replacement]) => {
      value = value.replaceAll(`{${name}}`, replacement);
    });
  }
  return value;
};
window.refreshLanguage = refreshLanguage;
