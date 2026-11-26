const subjects = document.querySelector('.subjects');
const topics = Array.from(subjects.querySelectorAll('a'));
subjects.setAttribute('role', 'tablist');

function setupFlowStudy(study) {
  const movies = Array.from(study.querySelectorAll('video'));
  const choices = study.querySelector('.flow-options');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let movie = movies[0];
  let requestedFrame = null;
  let visible = false;
  let firstVisit = true;

  function play() {
    // A browser can require an explicit gesture. Native controls stay available.
    movie.play().catch(() => {});
  }

  function pause() {
    if (requestedFrame) requestedFrame.resume = false;
    movie.pause();
  }

  function alignFrames() {
    if (!requestedFrame || movie.readyState < 1) return;
    const {time, resume} = requestedFrame;
    requestedFrame = null;
    movie.currentTime = Math.min(time, movie.duration);
    if (resume && visible && !document.hidden) play();
  }

  for (const clip of movies) {
    clip.addEventListener('loadedmetadata', () => {
      if (clip === movie) alignFrames();
    });
  }
  choices.hidden = false;
  choices.addEventListener('change', event => {
    const next = movies[Number(event.target.value)];
    if (!next || next === movie) return;
    requestedFrame = requestedFrame || {time: movie.currentTime, resume: !movie.paused && !movie.ended};
    movie.pause();
    movie.hidden = true;
    movie = next;
    movie.hidden = false;
    if (movie.readyState >= 1) alignFrames();
    else {
      movie.preload = 'metadata';
      movie.load();
    }
  });

  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) pause(); });
  return activeId => {
    visible = study.closest('.feature').id === activeId;
    if (!visible) pause();
    else if (firstVisit) {
      firstVisit = false;
      if (!reducedMotion.matches && !document.hidden) play();
    }
  };
}

const flowStudies = Array.from(document.querySelectorAll('[data-flow-study]'), setupFlowStudy);

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
  }
  for (const showStudy of flowStudies) showStudy(active.hash.slice(1));
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
