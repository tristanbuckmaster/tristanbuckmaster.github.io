(function () {
  const triggers = document.querySelectorAll('[data-recording] [data-play]');
  let activePlayer = null;

  function closePlayer(restoreFocus) {
    if (!activePlayer) return;
    const { trigger, panel } = activePlayer;
    panel.remove();
    trigger.hidden = false;
    trigger.setAttribute('aria-expanded', 'false');
    if (restoreFocus) trigger.focus();
    activePlayer = null;
  }

  for (const trigger of triggers) {
    const videoId = trigger.dataset.play;
    if (!/^[A-Za-z0-9_-]{11}$/.test(videoId)) continue;
    trigger.setAttribute('aria-expanded', 'false');
    trigger.addEventListener('click', function (event) {
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      event.preventDefault();
      closePlayer(false);

      const article = trigger.closest('[data-recording]');
      const panel = document.createElement('div');
      panel.className = 'recording-player';
      const frame = document.createElement('iframe');
      frame.title = article.querySelector('h2').textContent.trim();
      frame.src = 'https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1';
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.allow = 'autoplay; fullscreen; picture-in-picture; encrypted-media';
      frame.allowFullscreen = true;
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = 'Close player';
      close.addEventListener('click', function () { closePlayer(true); });
      panel.append(frame, close);
      article.appendChild(panel);
      trigger.hidden = true;
      trigger.setAttribute('aria-expanded', 'true');
      activePlayer = { trigger, panel };
      frame.focus();
    });
  }
})();
