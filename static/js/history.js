function setupHistoryFilters(options = {}) {
  const container  = document.querySelector('[data-history-list]');
  const emptyEl    = options.emptyId ? document.getElementById(options.emptyId) : null;
  if (!container) return;

  const dateFilter = document.querySelector('[data-history-date]');
  const cropFilter = document.querySelector('[data-history-crop]');
  const searchInput = document.querySelector('[data-history-search]');

  function parseDate(value) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function matchesCard(card) {
    const selectedCrop  = cropFilter?.value || '';
    const filterValue   = dateFilter?.value || 'all';
    const query         = (searchInput?.value || '').trim().toLowerCase();
    const cardCrop      = card.dataset.reportCrop || '';
    const cardDate      = parseDate(card.dataset.reportDate);
    const cardDisease   = card.dataset.reportDisease || '';

    if (selectedCrop && cardCrop !== selectedCrop) return false;
    if (query) {
      const haystack = `${cardCrop} ${cardDisease}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }

    if (filterValue !== 'all' && cardDate) {
      const diffDays = (Date.now() - cardDate.getTime()) / 86400000;
      if (filterValue === '7'  && diffDays > 7)  return false;
      if (filterValue === '30' && diffDays > 30) return false;
    }
    return true;
  }

  function applyFilters() {
    const cards = Array.from(container.querySelectorAll('.history-card'));
    let visible = 0;
    cards.forEach(card => {
      const show = matchesCard(card);
      card.hidden = !show;   // works with flex/grid layout correctly
      if (show) visible++;
    });
    if (emptyEl) emptyEl.style.display = visible === 0 ? 'block' : 'none';
  }

  dateFilter?.addEventListener('change', applyFilters);
  cropFilter?.addEventListener('change', applyFilters);
  searchInput?.addEventListener('input', applyFilters);
  applyFilters();
}

export { setupHistoryFilters };
