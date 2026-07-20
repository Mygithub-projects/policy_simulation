/*
 * Vanilla-JS port of the React Bits "TrueFocus" component.
 * Auto-cycles a glowing corner-bracket frame across a sequence of words,
 * blurring inactive ones. No React/motion dependency — plain CSS
 * transitions + getBoundingClientRect for frame positioning.
 */
(function () {
  function initTrueFocus(containerEl, options) {
    options = options || {};
    if (!containerEl) return function () {};

    const words = options.words || (containerEl.dataset.words || '').split('|').filter(Boolean);
    const wordClasses = options.wordClasses ||
      (containerEl.dataset.wordClasses !== undefined ? containerEl.dataset.wordClasses.split('|') : []);
    const wordGlows = options.wordGlows ||
      (containerEl.dataset.wordGlows !== undefined ? containerEl.dataset.wordGlows.split('|') : []);

    if (!words.length) return function () {};

    const blurAmount = options.blurAmount !== undefined ? options.blurAmount : 2.5;
    const animationDuration = options.animationDuration !== undefined ? options.animationDuration : 0.6;
    const pauseBetweenAnimations = options.pauseBetweenAnimations !== undefined ? options.pauseBetweenAnimations : 1.4;

    containerEl.innerHTML = '';
    containerEl.classList.add('true-focus-container');

    const wordEls = words.map((word, i) => {
      const span = document.createElement('span');
      span.className = 'focus-word' + (wordClasses[i] ? ' ' + wordClasses[i] : '');
      span.textContent = word;
      span.style.transition = `filter ${animationDuration}s ease`;
      containerEl.appendChild(span);
      if (i < words.length - 1) containerEl.appendChild(document.createElement('br'));
      return span;
    });

    const frame = document.createElement('div');
    frame.className = 'focus-frame';
    frame.style.transitionDuration = `${animationDuration}s`;
    frame.innerHTML =
      '<span class="corner top-left"></span>' +
      '<span class="corner top-right"></span>' +
      '<span class="corner bottom-left"></span>' +
      '<span class="corner bottom-right"></span>';
    containerEl.appendChild(frame);

    let currentIndex = 0;

    function applyFocus(index) {
      wordEls.forEach((el, i) => {
        el.style.filter = i === index ? 'blur(0px)' : `blur(${blurAmount}px)`;
      });

      const glow = wordGlows[index] || 'rgba(240,244,255,0.5)';
      frame.style.setProperty('--glow-color', glow);
      frame.style.setProperty('--border-color', glow);

      const parentRect = containerEl.getBoundingClientRect();
      const activeRect = wordEls[index].getBoundingClientRect();
      frame.style.transform = `translate(${activeRect.left - parentRect.left}px, ${activeRect.top - parentRect.top}px)`;
      frame.style.width = `${activeRect.width}px`;
      frame.style.height = `${activeRect.height}px`;
      frame.style.opacity = '1';
    }

    applyFocus(currentIndex);

    const intervalId = setInterval(() => {
      currentIndex = (currentIndex + 1) % words.length;
      applyFocus(currentIndex);
    }, (animationDuration + pauseBetweenAnimations) * 1000);

    function handleResize() {
      applyFocus(currentIndex);
    }
    window.addEventListener('resize', handleResize);

    return function teardown() {
      clearInterval(intervalId);
      window.removeEventListener('resize', handleResize);
    };
  }

  window.initTrueFocus = initTrueFocus;
})();
