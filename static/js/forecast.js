const widthMap = { low: 40, medium: 65, high: 90 };
const colorMap = { low: 'var(--leaf-green)', medium: 'var(--crop-yellow)', high: '#ff5f40' };

function resolveProgressWidth(bar, level) {
  const score = Number(bar.dataset.score);
  if (Number.isFinite(score) && score > 0) {
    return Math.max(18, Math.min(100, Math.round(score)));
  }
  return widthMap[level] || 40;
}

function bindForecastHover(parent) {
  if (!parent || parent.dataset.forecastBound === 'true') return;
  parent.dataset.forecastBound = 'true';
  parent.addEventListener('mouseenter', () => {
    parent.classList.add('is-active');
  });
  parent.addEventListener('mouseleave', () => {
    parent.classList.remove('is-active');
  });
}

export function syncForecastWidget(root = document) {
  const bars = root.querySelectorAll('[data-forecast-progress], .forecast-progress');
  bars.forEach((bar) => {
    const level = bar.dataset.level || 'low';
    const width = resolveProgressWidth(bar, level);
    const color = colorMap[level] || 'var(--leaf-green)';
    bar.dataset.riskLevel = level;
    bar.dataset.progressWidth = `${width}%`;
    requestAnimationFrame(() => {
      bar.style.width = `${width}%`;
      bar.style.background = color;
    });
    bindForecastHover(bar.closest('.forecast-item'));
  });
}

function initForecastWidget(root = document) {
  syncForecastWidget(root);
}

export default initForecastWidget;
