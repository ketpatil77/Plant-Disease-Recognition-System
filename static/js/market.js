/**
 * market.js — Enhanced Market Rates Widget
 * Fetches live Agmarknet prices via /api/market-rates
 * Falls back gracefully to static data if the API is unreachable.
 */

const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // auto-refresh every 5 min

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

export function initMarketWidget() {
  const card     = document.getElementById('marketCard');
  if (!card) return;

  const select   = document.getElementById('districtSelect');
  const searchEl = document.getElementById('marketSearch');
  const tableEl  = document.getElementById('marketTableBody');
  const headEl   = document.getElementById('marketTableHead');
  const badgeEl  = document.getElementById('marketSourceBadge');
  const timeEl   = document.getElementById('marketUpdatedAt');
  const refreshBtn = document.getElementById('marketRefreshBtn');
  const spinner  = document.getElementById('marketSpinner');
  const priceUnit = document.getElementById('marketPriceUnit');

  let currentData  = [];
  let currentFilter = '';
  let refreshTimer  = null;
  let currentSource = '';
  let currentFetchedAt = '';

  // ── Fetch ──────────────────────────────────────────────────────────────
  async function fetchRates(district) {
    setLoading(true);
    try {
      const url = `/api/market-rates?district=${encodeURIComponent(district)}`;
      const res  = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      currentData = json.data || [];
      await updateSourceBadge(json.source, json.fetched_at);
      await renderTable(currentData, currentFilter);
    } catch (err) {
      console.warn('[market] fetch failed:', err);
      await renderError();
    } finally {
      setLoading(false);
    }
  }

  // ── Render Table ────────────────────────────────────────────────────────
  async function renderTable(data, filter) {
    const filtered = filter
      ? data.filter(r => r.crop.toLowerCase().includes(filter.toLowerCase()))
      : data;

    if (!filtered.length) {
      const emptyText = await t(
        'home.market.empty_results',
        { query: filter },
        `No crops found for "${filter}"`,
      );
      tableEl.innerHTML = `
        <div class="market-empty">
          <span>🔍</span>
          <p>${emptyText}</p>
        </div>`;
      return;
    }

    // Compute max price for bar width
    const maxPrice = Math.max(...filtered.map(r => parseInt(r.price) || 0), 1);

    const rows = await Promise.all(filtered.map(async row => {
      const price    = parseInt(row.price) || 0;
      const pct      = Math.min(Math.round((price / maxPrice) * 100), 100);
      const trendCls = row.trend === 'up' ? 'trend-up' : row.trend === 'down' ? 'trend-down' : '';
      const trendIcon= row.trend === 'up' ? '▲' : row.trend === 'down' ? '▼' : '—';
      const trendLabel = await t(`common.trend.${row.trend || 'steady'}`, {}, row.trend || 'steady');
      const minMax   = (row.min_price && row.max_price)
        ? `<span class="price-range" title="${await t('home.market.range_title', { min: row.min_price, max: row.max_price }, `Min ₹${row.min_price} / Max ₹${row.max_price}`)}">↔ ₹${row.min_price}–${row.max_price}</span>`
        : '';
      const mandi    = row.mandi ? `<span class="mandi-tag">🏪 ${row.mandi}</span>` : '';
      const variety  = row.variety ? `<span class="variety-tag">${row.variety}</span>` : '';

      return `
        <div class="table-row market-row" data-crop="${row.crop}">
          <div class="crop-info">
            <span class="crop-name">${row.crop}</span>
            <div class="crop-meta">${variety}${mandi}</div>
          </div>
          <div class="price-col">
            <div class="price-bar-wrap">
              <div class="price-bar" style="width:${pct}%"></div>
            </div>
            <span class="price-value">
              ₹${row.price || '—'}
              <span class="trend-icon ${trendCls}" aria-label="${trendLabel}">${trendIcon}</span>
            </span>
            ${minMax}
          </div>
        </div>`;
    }));
    tableEl.innerHTML = rows.join('');
  }

  // ── Source badge ────────────────────────────────────────────────────────
  async function updateSourceBadge(source, fetchedAt) {
    currentSource = source || '';
    currentFetchedAt = fetchedAt || '';
    const isLive = source === 'agmarknet_live';
    if (badgeEl) {
      badgeEl.textContent = isLive
        ? `🟢 ${await t('home.market.source.live_badge', {}, 'Live - Agmarknet')}`
        : `🟡 ${await t('home.market.source.cached_badge', {}, 'Cached data')}`;
      badgeEl.className      = `market-source-badge ${isLive ? 'live' : 'fallback'}`;
      badgeEl.title = isLive
        ? await t('home.market.source.live_title', {}, 'Prices from data.gov.in Agmarknet API')
        : await t('home.market.source.cached_title', {}, 'Live API unreachable, showing saved reference prices');
    }
    if (timeEl && fetchedAt) {
      timeEl.textContent = await t('common.updated_at', { value: fetchedAt }, `Updated ${fetchedAt}`);
    }
    if (priceUnit) priceUnit.textContent = await t('home.market.price', {}, '₹/quintal');
  }

  // ── Loading / Error ──────────────────────────────────────────────────────
  function setLoading(on) {
    if (spinner)  spinner.style.display = on ? 'flex' : 'none';
    if (tableEl && on) {
      tableEl.innerHTML = `
        ${['','','','',''].map(() => `
          <div class="table-row skeleton-row">
            <div class="skeleton" style="width:45%;height:14px;border-radius:4px;"></div>
            <div class="skeleton" style="width:25%;height:14px;border-radius:4px;"></div>
          </div>`).join('')}`;
    }
    if (refreshBtn) refreshBtn.disabled = on;
  }

  async function renderError() {
    if (tableEl) {
      tableEl.innerHTML = `
        <div class="market-empty">
          <span>⚠️</span>
          <p>${await t('home.market.error', {}, 'Could not load rates. Retrying soon...')}</p>
        </div>`;
    }
  }

  // ── Auto-refresh ─────────────────────────────────────────────────────────
  function scheduleRefresh(district) {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => fetchRates(district), REFRESH_INTERVAL_MS);
  }

  // ── Events ────────────────────────────────────────────────────────────────
  if (select) {
    select.addEventListener('change', e => {
      e.preventDefault();
      const d = select.value;
      fetchRates(d);
      scheduleRefresh(d);
    });
  }

  if (searchEl) {
    searchEl.addEventListener('input', () => {
      currentFilter = searchEl.value.trim();
      renderTable(currentData, currentFilter);
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      const d = select ? select.value : '';
      fetchRates(d);
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  const initialDistrict = select ? select.value : '';
  fetchRates(initialDistrict);
  scheduleRefresh(initialDistrict);

  document.addEventListener('agro:languagechange', async () => {
    await updateSourceBadge(currentSource, currentFetchedAt);
    await renderTable(currentData, currentFilter);
  });
}
