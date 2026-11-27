const subjects = document.querySelector('.subjects');
const topics = Array.from(subjects.querySelectorAll('a'));
subjects.setAttribute('role', 'tablist');

const movies = document.querySelectorAll('[data-feature-movie]');
const unvisited = new Set(movies);
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

for (const choices of document.querySelectorAll('.clip-choices')) {
  const figure = choices.closest('figure');
  const movie = figure.querySelector('[data-feature-movie]');
  const source = movie.querySelector('source');
  const caption = figure.querySelector('figcaption span');
  let current = choices.querySelector('[aria-current]');
  let pendingTime = null;

  movie.addEventListener('loadedmetadata', () => {
    if (pendingTime === null || movie.currentSrc !== current.href) return;
    movie.currentTime = Math.min(pendingTime, movie.duration);
    pendingTime = null;
  });

  for (const clip of choices.querySelectorAll('[data-clip]')) {
    clip.addEventListener('click', event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (clip === current) return;

      // Until metadata arrives the newly loaded file reports time zero.
      if (pendingTime === null) pendingTime = movie.currentTime;
      const wasPlaying = !movie.paused && !movie.ended;
      current.removeAttribute('aria-current');
      current = clip;
      clip.setAttribute('aria-current', 'true');
      movie.poster = clip.dataset.poster;
      movie.setAttribute('aria-label', clip.dataset.description);
      caption.textContent = clip.dataset.caption;
      source.src = clip.href;
      movie.querySelector('a').href = clip.href;
      movie.preload = 'auto';
      movie.load();
      if (wasPlaying && !document.hidden) movie.play().catch(() => {});
    });
  }
}

function pauseMovies() {
  for (const movie of movies) movie.pause();
}

document.addEventListener('visibilitychange', () => { if (document.hidden) pauseMovies(); });
reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) pauseMovies(); });

function showTopic(active) {
  for (const link of topics) {
    const selected = link === active;
    const panel = document.getElementById(link.hash.slice(1));
    link.setAttribute('role', 'tab');
    link.setAttribute('aria-selected', String(selected));
    link.setAttribute('aria-controls', panel.id);
    link.tabIndex = selected ? 0 : -1;
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', link.id);
    panel.hidden = !selected;

    const movie = panel.querySelector('[data-feature-movie]');
    if (!movie) continue;
    if (!selected) movie.pause();
    else if (unvisited.delete(movie) && !reducedMotion.matches && !document.hidden) {
      // Some browsers require a gesture. Native controls are always available.
      movie.play().catch(() => {});
    }
  }
}

function showHashTopic() {
  const active = topics.find(link => link.hash === location.hash);
  showTopic(active || topics[0]);
}

function activate(link) {
  showTopic(link);
  history.replaceState(null, '', link.hash);
}

for (const [index, link] of topics.entries()) {
  link.addEventListener('click', event => {
    event.preventDefault();
    activate(link);
  });
  link.addEventListener('keydown', event => {
    const nextIndex = {
      ArrowLeft: (index + topics.length - 1) % topics.length,
      ArrowRight: (index + 1) % topics.length,
      Home: 0,
      End: topics.length - 1
    }[event.key];
    if (nextIndex === undefined) return;
    event.preventDefault();
    topics[nextIndex].focus();
    activate(topics[nextIndex]);
  });
}
window.addEventListener('hashchange', showHashTopic);
showHashTopic();
