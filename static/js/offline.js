const STORAGE_KEY = 'agro-last-reports';

async function t(key, vars, fallback) {
  if (typeof window.getTranslation === 'function') {
    const value = await window.getTranslation(key, vars);
    if (value && value !== key) return value;
  }
  let resolved = fallback ?? key;
  if (vars && typeof resolved === 'string') {
    Object.entries(vars).forEach(([name, replacement]) => {
      resolved = resolved.replaceAll(`{${name}}`, replacement);
    });
  }
  return resolved;
}

function initOfflineStatus() {
  const badge = document.querySelector('[data-offline-status]') || document.querySelector('[data-offline-weather]');
  if (!badge) return;
  const update = async () => {
    const key = navigator.onLine ? '' : 'footer.offline';
    if (!key) {
      badge.textContent = '';
      badge.classList.remove('is-offline');
      return;
    }
    const text = typeof window.getTranslation === 'function' ? await window.getTranslation(key) : 'Connection unavailable';
    badge.textContent = text;
    badge.classList.toggle('is-offline', !navigator.onLine);
  };
  window.addEventListener('online', update);
  window.addEventListener('offline', update);
  document.addEventListener('agro:languagechange', update);
  update();
}

function storeLastReport(report) {
  if (!report) return;
  const existing = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  const trimmed = existing.filter((item) => item.disease !== report.disease || item.crop !== report.crop);
  trimmed.unshift(report);
  trimmed.splice(5);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

function getCachedReports() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch (err) {
    return [];
  }
}

async function populateOfflineHistory(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;
  container.querySelectorAll('.offline-entry').forEach(card => card.remove());
  const cache = getCachedReports();
  const offlineBadge = await t('history.offline.badge', {}, 'Offline cache');
  cache.forEach((report) => {
    const card = document.createElement('article');
    const severity = (report.severity || 'medium').toLowerCase();
    card.className = 'history-card offline-entry';
    card.dataset.reportCrop = report.crop || '';
    card.dataset.reportDisease = report.disease || '';
    card.dataset.reportDate = report.time || '';
    card.innerHTML = `
      <div class="history-main">
        <p class="report-time">${report.time || '—'}</p>
        <span class="badge badge-info">${offlineBadge}</span>
        <h3>${report.crop}</h3>
        <p class="history-disease">${report.disease}</p>
      </div>
      <div class="history-meta">
        <span class="badge badge-severity-${severity}">${severity === 'high' ? 'High' : severity === 'low' ? 'Low' : 'Medium'}</span>
        <span class="confidence">${report.confidence || '0'}%</span>
      </div>
    `;
    container.appendChild(card);
  });

  const severityLabels = {
    high: await t('common.level.high', {}, 'High'),
    medium: await t('common.level.medium', {}, 'Medium'),
    low: await t('common.level.low', {}, 'Low'),
  };
  container.querySelectorAll('.offline-entry .badge-severity-high').forEach(el => { el.textContent = severityLabels.high; });
  container.querySelectorAll('.offline-entry .badge-severity-medium').forEach(el => { el.textContent = severityLabels.medium; });
  container.querySelectorAll('.offline-entry .badge-severity-low').forEach(el => { el.textContent = severityLabels.low; });
}

export { initOfflineStatus, storeLastReport, populateOfflineHistory };
