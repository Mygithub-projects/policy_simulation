/*
 * Vanilla-JS port of the React Bits "SplitText" component.
 * Splits a heading's text into per-character spans and fades/slides them in
 * with a staggered delay once the element scrolls into view. Plain CSS
 * transitions + IntersectionObserver — no gsap/@gsap/react dependency,
 * matching the existing precedent set by aurora-bg.js and true-focus.js.
 *
 * Progressive enhancement: operates on markup that already contains the
 * final text (including inline tags like <em>/<br>). If this script fails
 * to load or run, the heading still renders correctly as static text.
 */
(function () {
  function splitIntoChars(el) {
    const nodes = Array.prototype.slice.call(el.childNodes);
    nodes.forEach(function (node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const frag = document.createDocumentFragment();
        const tokens = node.textContent.split(/(\s+)/);
        tokens.forEach(function (token) {
          if (token === '') return;
          if (/^\s+$/.test(token)) {
            frag.appendChild(document.createTextNode(token));
            return;
          }
          Array.prototype.forEach.call(token, function (ch) {
            const span = document.createElement('span');
            span.className = 'split-char';
            span.textContent = ch;
            frag.appendChild(span);
          });
        });
        el.replaceChild(frag, node);
      } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName !== 'BR') {
        splitIntoChars(node);
      }
    });
  }

  function initSplitText(el, options) {
    options = options || {};
    if (!el) return function () {};

    const delay = options.delay !== undefined ? options.delay : 30;
    const duration = options.duration !== undefined ? options.duration : 0.6;
    const threshold = options.threshold !== undefined ? options.threshold : 0.2;
    const rootMargin = options.rootMargin || '0px';

    splitIntoChars(el);
    const chars = Array.prototype.slice.call(el.querySelectorAll('.split-char'));
    if (!chars.length) return function () {};

    chars.forEach(function (span) {
      span.style.transitionDuration = duration + 's';
    });

    function play() {
      chars.forEach(function (span, i) {
        span.style.transitionDelay = (i * delay) + 'ms';
        span.classList.add('split-in');
      });
    }

    if (!('IntersectionObserver' in window)) {
      play();
      return function () {};
    }

    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          play();
          observer.unobserve(el);
        }
      });
    }, { threshold: threshold, rootMargin: rootMargin });

    observer.observe(el);

    return function teardown() {
      observer.disconnect();
    };
  }

  window.initSplitText = initSplitText;
})();
