const subjects = document.querySelector('.subjects');
const topics = Array.from(subjects.querySelectorAll('a'));
subjects.setAttribute('role', 'tablist');

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
