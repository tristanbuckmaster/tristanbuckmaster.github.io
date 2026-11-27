(() => {
  const archive = document.getElementById('publication-list');
  if (!archive) return;

  const search = document.getElementById('paper-search');
  const yearSelect = document.getElementById('paper-year');
  const count = document.querySelector('[data-paper-count]');
  const empty = document.querySelector('.pub-empty');

  function normalize(text) {
    return text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  }

  const groups = Array.from(archive.querySelectorAll('h2'), (heading) => {
    const list = heading.nextElementSibling;
    const year = heading.textContent.trim();
    heading.id = 'pub-year-' + normalize(year).replaceAll(' ', '-');
    heading.tabIndex = -1;
    const option = new Option(year, heading.id);
    yearSelect.add(option);

    const rows = Array.from(list.children, (item) => {
      const metadata = Array.from(item.querySelectorAll('.pub-title, .pub-authors, .pub-venue'),
        (element) => element.textContent);
      return { item, text: normalize([year, ...metadata].join(' ')) };
    });

    return { heading, list, option, rows };
  });

  function filterPapers() {
    const words = normalize(search.value).split(' ').filter(Boolean);
    let visible = 0;

    for (const { heading, list, option, rows } of groups) {
      let groupCount = 0;
      for (const row of rows) {
        const matches = words.every(word => row.text.includes(word));
        row.item.hidden = !matches;
        if (matches) groupCount++;
      }
      heading.hidden = list.hidden = option.disabled = groupCount === 0;
      visible += groupCount;
    }

    count.textContent = visible + (visible === 1 ? ' publication' : ' publications');
    empty.hidden = visible > 0;
    yearSelect.value = '';
  }

  document.querySelector('.pub-search').hidden = false;
  document.querySelector('.pub-jump').hidden = false;
  search.addEventListener('input', filterPapers);
  yearSelect.addEventListener('change', () => {
    const heading = document.getElementById(yearSelect.value);
    if (heading) {
      heading.scrollIntoView();
      heading.focus({ preventScroll: true });
    }
  });
  document.querySelector('[data-clear-search]').addEventListener('click', () => {
    search.value = '';
    filterPapers();
    search.focus();
  });
  filterPapers();
})();
