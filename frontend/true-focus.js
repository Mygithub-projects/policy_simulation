/*
 * Vanilla-JS port of the React Bits "TrueFocus" component.
 * Auto-cycles a glowing corner-bracket frame across a sequence of words,
 * blurring inactive ones. No React/motion dependency — plain CSS
 * transitions + getBoundingClientRect for frame positioning.
 *
 * Progressive enhancement: this script ENHANCES existing <span> word
 * elements already in the markup (each word's original styling/text stays
 * as plain static HTML). If this script fails to load or run, the
 * headline still renders correctly as static text — it just won't animate.
 */
(function () {
  function initTrueFocus(containerEl, options) {
    options = options || {};
    if (!containerEl) return function () {};

    const wordEls = Array.prototype.slice.call(containerEl.querySelectorAll(':scope > span'));
    if (!wordEls.length) return function () {};

    const blurAmount = options.blurAmount !== undefined ? options.blurAmount : 2.5;
    const animationDuration = options.animationDuration !== undefined ? options.animationDuration : 0.6;
    const pauseBetweenAnimations = options.pauseBetweenAnimations !== undefined ? options.pauseBetweenAnimations : 1.4;

    containerEl.classList.add('true-focus-container');
    wordEls.forEach(function (el) {
      el.classList.add('focus-word');
      el.style.transition = `filter ${animationDuration}s ease`;
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

      const glow = wordEls[index].dataset.glow || 'rgba(240,244,255,0.5)';
      frame.style.setProperty('--glow-color', glow);
      frame.style.setProperty('--border-color', glow);

      const parentRect = containerEl.getBoundingClientRect();
      const activeRect = wordEls[index].getBoundingClientRect();
      frame.style.transform = `translate(${activeRect.left - parentRect.left}px, ${activeRect.top - parentRect.top}px)`;
      frame.style.width = `${activeRect.width}px`;
      frame.style.height = `${activeRect.height}px`;
      frame.style.opacity = '1';
    }

    // Wait for fonts/layout to settle before the first measurement, otherwise
    // the frame can end up measured against pre-webfont-swap positions.
    function start() {
      applyFocus(currentIndex);
    }
    if (document.fonts && document.fonts.status !== 'loaded') {
      document.fonts.ready.then(start);
    } else {
      start();
    }

    const intervalId = setInterval(() => {
      currentIndex = (currentIndex + 1) % wordEls.length;
      applyFocus(currentIndex);
    }, (animationDuration + pauseBetweenAnimations) * 1000);

    function handleResize() {
      applyFocus(currentIndex);
    }
    window.addEventListener('resize', handleResize);

    return function teardown() {
      clearInterval(intervalId);
      window.removeEventListener('resize', handleResize);
      if (frame.parentElement) containerEl.removeChild(frame);
    };
  }

  window.initTrueFocus = initTrueFocus;
})();
