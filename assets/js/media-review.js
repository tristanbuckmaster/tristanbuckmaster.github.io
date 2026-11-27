(() => {
  const form = document.getElementById('review');
  const count = document.getElementById('count');
  const note = document.getElementById('save-note');
  const storagePrefix = 'plates-media-review:v1:';
  const byStorageKey = new Map();
  const items = Array.from(form.querySelectorAll('[data-item]'), item => {
    const primaryUrl = item.querySelector('[data-link] a').getAttribute('href');
    const links = Array.from(item.querySelectorAll('[data-link]'), row => {
      const anchor = row.querySelector('a');
      const link = {
        url: anchor.getAttribute('href'),
        label: anchor.textContent.trim(),
        checkbox: row.querySelector('input')
      };
      const key = storagePrefix + JSON.stringify([primaryUrl, link.url]);
      byStorageKey.set(key, link.checkbox);
      return link;
    });
    return { title: item.dataset.title, primary: links[0], companions: links.slice(1) };
  });
  const checkboxes = Array.from(byStorageKey.values());
  const unsaved = new Set();

  function showCount() {
    const kept = checkboxes.filter(box => box.checked).length;
    count.textContent = kept + ' of ' + checkboxes.length + ' links kept';
  }

  function showSaveNote() {
    note.textContent = unsaved.size ? 'Some selections may only last this session. Export before closing.' : 'Selections are saved in this browser.';
  }

  for (const [key, checkbox] of byStorageKey) {
    try {
      checkbox.checked = localStorage.getItem(key) === 'keep';
    } catch {
      unsaved.add(key);
    }
    checkbox.addEventListener('change', () => {
      try {
        if (checkbox.checked) localStorage.setItem(key, 'keep');
        else localStorage.removeItem(key);
        unsaved.delete(key);
      } catch {
        unsaved.add(key);
      }
      showCount();
      showSaveNote();
    });
  }

  window.addEventListener('storage', event => {
    if (event.key === null) {
      for (const checkbox of checkboxes) checkbox.checked = false;
      unsaved.clear();
    } else if (event.key.startsWith(storagePrefix)) {
      const checkbox = byStorageKey.get(event.key);
      if (checkbox) checkbox.checked = event.newValue === 'keep';
      unsaved.delete(event.key);
    } else return;
    showCount();
    showSaveNote();
  });

  function decision(link) {
    return link.checkbox.checked ? 'keep' : 'remove';
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const review = {
      format: 'plates-media-review',
      version: 1,
      items: items.map(({ title, primary, companions }) => ({
        title,
        url: primary.url,
        decision: decision(primary),
        links: companions.map(link => ({ label: link.label, url: link.url, decision: decision(link) }))
      }))
    };
    const file = new Blob([JSON.stringify(review, null, 2) + '\n'], { type: 'application/json' });
    const download = document.createElement('a');
    download.href = URL.createObjectURL(file);
    download.download = 'media-review.json';
    document.body.append(download);
    download.click();
    download.remove();
    setTimeout(() => URL.revokeObjectURL(download.href), 60000);
    note.textContent = 'Exported media-review.json';
  });

  showCount();
  showSaveNote();
  document.getElementById('export').disabled = false;
})();
