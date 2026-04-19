import { syncForecastWidget } from './forecast.js';

const STORED_COORDS_KEY = 'agro-live-weather-coords';

let elementsCache = null;
let lastSnapshot = null;
let lastStatus = { key: 'home.weather.status.locating', fallback: 'डिव्हाइसचे स्थान शोधत आहे...' };
let statusMode = 'message';
let isRefreshing = false;

function getElements() {
  if (elementsCache) return elementsCache;

  const panel = document.querySelector('[data-weather-panel]');
  if (!panel) return null;

  elementsCache = {
    panel,
    refreshButton: panel.querySelector('[data-weather-refresh]'),
    riskBadge: panel.querySelector('[data-weather-risk-badge]'),
    location: panel.querySelector('[data-weather-location]'),
    status: panel.querySelector('[data-weather-status]'),
    temperature: panel.querySelector('[data-weather-temp]'),
    humidity: panel.querySelector('[data-weather-humidity]'),
    rain: panel.querySelector('[data-weather-rain]'),
    wind: panel.querySelector('[data-weather-wind]'),
    summary: panel.querySelector('[data-weather-summary]'),
    tip: panel.querySelector('[data-weather-tip]'),
    advisoryRiskBadge: document.querySelector('[data-advisory-risk-badge]'),
    advisorySummary: document.querySelector('[data-advisory-summary]'),
    advisoryTip: document.querySelector('[data-advisory-tip]'),
    forecastContext: document.querySelector('[data-forecast-context]'),
    forecastItems: Array.from(document.querySelectorAll('[data-forecast-item]')),
  };

  return elementsCache;
}

async function translate(key, fallback) {
  if (typeof window.getTranslation === 'function') {
    try {
      const value = await window.getTranslation(key);
      if (value && value !== key) return value;
    } catch (_error) {
      // Ignore translation failures and use the English fallback.
    }
  }
  return fallback;
}

function setText(element, value) {
  if (!element) return;
  element.textContent = value;
}

async function riskLabel(risk) {
  const level = (risk || 'medium').toLowerCase();
  return translate(`common.level.${level}`, level === 'high' ? 'उच्च' : level === 'low' ? 'कमी' : 'मध्यम');
}

async function applyRiskBadge(element, risk) {
  if (!element) return;
  element.classList.remove('low', 'medium', 'high');
  element.classList.add(risk);
  element.textContent = await riskLabel(risk);
}

async function applyAdvisoryBadge(element, risk) {
  if (!element) return;
  element.classList.remove('badge-danger', 'badge-warning', 'badge-success');
  if (risk === 'high') element.classList.add('badge-danger');
  else if (risk === 'medium') element.classList.add('badge-warning');
  else element.classList.add('badge-success');
  element.textContent = await riskLabel(risk);
}

function formatObservedTime(isoValue) {
  if (!isoValue) return '';
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('mr-IN', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function readStoredCoords() {
  try {
    const raw = localStorage.getItem(STORED_COORDS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!Number.isFinite(parsed?.lat) || !Number.isFinite(parsed?.lon)) return null;
    return parsed;
  } catch (_error) {
    return null;
  }
}

function writeStoredCoords(coords) {
  localStorage.setItem(
    STORED_COORDS_KEY,
    JSON.stringify({
      lat: coords.lat,
      lon: coords.lon,
      savedAt: Date.now(),
    }),
  );
}

function currentCoordsLabel(snapshot) {
  return snapshot?.location?.label || '—';
}

function formatRain(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return `${numeric.toFixed(1)} mm / 24h`;
}

function formatWind(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return `${Math.round(numeric)} km/h`;
}

async function updateForecast(snapshot, elements) {
  const forecast = Array.isArray(snapshot?.forecast) ? snapshot.forecast : [];

  for (const [index, item] of elements.forecastItems.entries()) {
    const day = forecast[index];
    if (!day) continue;

    const dayLabel = item.querySelector('[data-forecast-day]');
    const icon = item.querySelector('[data-forecast-icon]');
    const level = item.querySelector('[data-forecast-level]');
    const progress = item.querySelector('[data-forecast-progress]');
    const description = item.querySelector('[data-forecast-description]');

    setText(dayLabel, day.day || `Day ${index + 1}`);
    setText(icon, day.icon || '🌥️');
    if (level) {
      level.classList.remove('low', 'medium', 'high');
      level.classList.add(day.level || 'medium');
      level.textContent = await riskLabel(day.level || 'medium');
    }
    if (progress) {
      progress.dataset.level = day.level || 'medium';
      progress.dataset.score = String(day.risk_score ?? '');
    }
    setText(description, day.description || 'लाइव्ह हवामानाची माहिती अद्ययावत होत आहे.');
  }

  syncForecastWidget(document);
}

async function renderStatus(snapshot) {
  const elements = getElements();
  if (!elements?.status) return;

  if (snapshot && statusMode === 'snapshot') {
    const updatedPrefix = await translate('home.weather.status.updated', 'अपडेट');
    const observedAt = formatObservedTime(snapshot.current?.observed_at);
    const cachedSuffix = snapshot.cached ? ' · जतन केलेला डेटा' : '';
    const statusText = observedAt ? `${updatedPrefix} ${observedAt}${cachedSuffix}` : updatedPrefix;
    setText(elements.status, statusText);
    return;
  }

  setText(elements.status, await translate(lastStatus.key, lastStatus.fallback));
}

async function renderSnapshot(snapshot) {
  const elements = getElements();
  if (!elements) return;

  lastSnapshot = snapshot;
  statusMode = 'snapshot';
  await applyRiskBadge(elements.riskBadge, snapshot.current?.risk || 'medium');
  await applyAdvisoryBadge(elements.advisoryRiskBadge, snapshot.current?.risk || 'medium');

  setText(
    elements.location,
    `${await translate('home.weather.location.live', 'Live machine location')}: ${currentCoordsLabel(snapshot)}`,
  );
  setText(elements.temperature, `${snapshot.current?.temperature ?? '—'}°C`);
  setText(elements.humidity, `${snapshot.current?.humidity ?? '—'}%`);
  setText(elements.rain, formatRain(snapshot.current?.rain_mm_24h));
  setText(elements.wind, formatWind(snapshot.current?.wind_speed));
  setText(elements.summary, snapshot.current?.summary || 'लाइव्ह हवामान सक्रिय आहे.');
  setText(elements.tip, snapshot.current?.tip || 'नियमित पाहणी सुरू ठेवा आणि हवामानानुसार शेतातील काम समायोजित करा.');
  setText(elements.advisorySummary, snapshot.current?.summary || 'रोगदाब लक्षात ठेवा आणि पिकांची लवकर पाहणी करा.');
  setText(elements.advisoryTip, snapshot.current?.tip || 'नियमित पाहणी सुरू ठेवा.');
  setText(
    elements.forecastContext,
    await translate('home.forecast.source.live', 'Live forecast from your machine location.'),
  );

  await updateForecast(snapshot, elements);
  await renderStatus(snapshot);
}

async function setPendingStatus(key, fallback) {
  lastStatus = { key, fallback };
  statusMode = 'message';
  await renderStatus(lastSnapshot);
}

async function loadWeather(coords) {
  const response = await fetch(`/api/weather?lat=${encodeURIComponent(coords.lat)}&lon=${encodeURIComponent(coords.lon)}`, {
    headers: {
      Accept: 'application/json',
    },
    cache: 'no-store',
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch (_error) {
    payload = null;
  }

  if (!response.ok || !payload?.ok) {
    throw new Error(payload?.error || `Weather request failed (${response.status})`);
  }

  await renderSnapshot(payload);
}

function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 300000,
    });
  });
}

async function refreshLiveWeather() {
  if (isRefreshing) return;
  const elements = getElements();
  if (!elements) return;

  if (!navigator.geolocation) {
    lastStatus = {
      key: 'home.weather.status.unsupported',
      fallback: 'या ब्राउझरमध्ये स्थान सुविधा उपलब्ध नाही. फॉलबॅक माहिती दाखवली जाते.',
    };
    await renderStatus(null);
    return;
  }

  isRefreshing = true;
  if (elements.refreshButton) elements.refreshButton.disabled = true;

  try {
    await setPendingStatus('home.weather.status.refreshing', 'लाइव्ह हवामान रीफ्रेश करत आहे...');
    const position = await getCurrentPosition();
    const coords = {
      lat: position.coords.latitude,
      lon: position.coords.longitude,
    };
    writeStoredCoords(coords);
    await loadWeather(coords);
  } catch (error) {
    const isPermissionError = error && typeof error === 'object' && error.code === 1;
    lastStatus = isPermissionError
      ? {
          key: 'home.weather.status.denied',
          fallback: 'स्थान परवानगी नाकारली. जतन केलेली माहिती दाखवली जाते.',
        }
      : {
          key: 'home.weather.status.error',
          fallback: 'लाइव्ह हवामान सध्या लोड होत नाही.',
        };
    await renderStatus(lastSnapshot);
  } finally {
    isRefreshing = false;
    if (elements.refreshButton) elements.refreshButton.disabled = false;
  }
}

async function warmFromStoredCoords() {
  const stored = readStoredCoords();
  if (!stored) return;

  try {
    await setPendingStatus('home.weather.status.refreshing', 'लाइव्ह हवामान रीफ्रेश करत आहे...');
    await loadWeather(stored);
  } catch (_error) {
    // Ignore stale cache failures and fall back to live geolocation.
  }
}

export default function initWeatherPanel() {
  const elements = getElements();
  if (!elements) return;

  elements.refreshButton?.addEventListener('click', () => {
    refreshLiveWeather();
  });

  document.addEventListener('agro:languagechange', () => {
    if (lastSnapshot) {
      renderSnapshot(lastSnapshot);
      return;
    }
    renderStatus(null);
  });

  warmFromStoredCoords().finally(() => {
    refreshLiveWeather();
  });
}
