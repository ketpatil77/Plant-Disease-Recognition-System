/* global Chart */

const TRENDS_URL = '/static/data/trends.json';
let _trendData = null;

async function loadTrendsData() {
  if (_trendData) return _trendData;
  try {
    const res = await fetch(TRENDS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    _trendData = await res.json();
    return _trendData;
  } catch (err) {
    console.warn('[TrendChart] Failed to load:', err.message);
    return null;
  }
}

function getThemeTokens() {
  const root = document.documentElement;
  const style = getComputedStyle(root);
  const isDark = root.dataset.theme !== 'light';
  return {
    surfaceColor: style.getPropertyValue('--bg-overlay').trim() || (isDark ? '#1c2333' : '#ffffff'),
    borderColor: style.getPropertyValue('--border-default').trim() || (isDark ? 'rgba(255,255,255,0.11)' : 'rgba(15,23,42,0.1)'),
    titleColor: style.getPropertyValue('--text-primary').trim() || (isDark ? '#e8eef8' : '#0b1120'),
    textColor:  isDark ? '#94a3b8' : '#44546a',
    gridColor:  isDark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.06)',
    bgColor:    isDark ? 'rgba(22,27,36,0)' : 'rgba(255,255,255,0)',
    green:  isDark ? '#34d399' : '#059669',
    blue:   isDark ? '#38bdf8' : '#0ea5e9',
    amber:  isDark ? '#fbbf24' : '#d97706',
  };
}

async function translate(key, fallback) {
  if (typeof window.getTranslation === 'function') {
    return window.getTranslation(key);
  }
  return fallback || key;
}

function buildDataset(months, key, color, label) {
  const alpha = color + '22';   // 13% opacity fill
  return {
    label,
    data: months.map((m) => m[key] ?? 0),
    borderColor: color,
    backgroundColor: alpha,
    fill: true,
    tension: 0.4,
    pointRadius: 3,
    pointHoverRadius: 5,
    pointBackgroundColor: color,
    pointBorderColor: 'transparent',
    borderWidth: 2,
  };
}

export async function initTrendChart(canvasSelector, districtSelector) {
  const canvas = document.querySelector(canvasSelector);
  const select = document.querySelector(districtSelector);
  if (!canvas) return;

  const trendData = await loadTrendsData();
  if (!trendData) {
    // Show graceful empty state
    const wrapper = canvas.closest('.trend-chart');
    if (wrapper) {
      const emptyText = await translate('home.analytics.empty', 'No trend data available.');
      wrapper.innerHTML = `<p style="text-align:center;color:var(--text-muted);padding:var(--sp-6) 0;font-size:var(--text-sm);">${emptyText}</p>`;
    }
    return;
  }

  let chart = null;

  async function render(districtName) {
    const district = (trendData.districts || []).find((d) => d.name === districtName)
      || (trendData.districts || [])[0];
    if (!district) return;

    const months = district.monthly || [];
    const tk = getThemeTokens();
    const fungalLabel = await translate('home.analytics.fungal', 'Fungal');
    const viralLabel = await translate('home.analytics.viral', 'Viral');
    const bacterialLabel = await translate('home.analytics.bacterial', 'Bacterial');

    const config = {
      type: 'line',
      data: {
        labels: months.map((m) => m.month),
        datasets: [
          buildDataset(months, 'fungal',    tk.green, fungalLabel),
          buildDataset(months, 'viral',     tk.blue,  viralLabel),
          buildDataset(months, 'bacterial', tk.amber, bacterialLabel),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600 },
        interaction: { mode: 'index', intersect: false },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: {
              color: tk.textColor,
              font: { size: 11 },
              maxTicksLimit: 5,
            },
            grid: { color: tk.gridColor, lineWidth: 1 },
            border: { display: false },
          },
          x: {
            ticks: {
              color: tk.textColor,
              font: { size: 11 },
              maxRotation: 0,
            },
            grid: { display: false },
            border: { display: false },
          },
        },
        plugins: {
          legend: { display: false },  // We use custom CSS legend
          tooltip: {
            backgroundColor: tk.surfaceColor,
            borderColor: tk.borderColor,
            borderWidth: 1,
            titleColor: tk.titleColor,
            bodyColor: tk.textColor,
            padding: 10,
            callbacks: {
              label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`,
            },
          },
        },
      },
    };

    if (chart) { chart.destroy(); chart = null; }
    chart = new Chart(canvas.getContext('2d'), config);
  }

  const initialDistrict = select?.value || (trendData.districts?.[0]?.name);
  render(initialDistrict);

  select?.addEventListener('change', (e) => render(e.target.value));

  // Re-render when theme changes
  new MutationObserver(() => {
    if (select) render(select.value);
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  document.addEventListener('agro:languagechange', () => {
    if (select) render(select.value);
  });
}
