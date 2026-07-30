/*
 * Vanilla-JS port of the React Bits "LogoLoop" component.
 * Infinite horizontal marquee of logo images — plain requestAnimationFrame +
 * CSS transform, no React/dependency, matching the precedent set by
 * aurora-bg.js and true-focus.js. Mounted on the login screen only, as a
 * "supported by" strip beneath the login card.
 */
(function () {
  function initLogoLoop(containerEl, options) {
    options = options || {};
    if (!containerEl) return function () {};

    const logos = options.logos || [];
    if (!logos.length) return function () {};

    const speed = options.speed !== undefined ? options.speed : 60; // px/sec
    const gap = options.gap !== undefined ? options.gap : 40;
    const logoHeight = options.logoHeight !== undefined ? options.logoHeight : 32;
    const fadeOut = options.fadeOut !== undefined ? options.fadeOut : true;
    const pauseOnHover = options.pauseOnHover !== undefined ? options.pauseOnHover : true;

    containerEl.classList.add('logo-loop');
    if (fadeOut) containerEl.classList.add('logo-loop--fade');
    containerEl.style.setProperty('--logo-loop-gap', `${gap}px`);
    containerEl.style.setProperty('--logo-loop-height', `${logoHeight}px`);
    containerEl.setAttribute('role', 'region');
    containerEl.setAttribute('aria-label', options.ariaLabel || 'Partner logos');

    const track = document.createElement('div');
    track.className = 'logo-loop__track';
    containerEl.appendChild(track);

    function buildList() {
      const list = document.createElement('ul');
      list.className = 'logo-loop__list';
      list.setAttribute('role', 'list');
      logos.forEach(logo => {
        const li = document.createElement('li');
        li.className = 'logo-loop__item';
        li.setAttribute('role', 'listitem');
        const img = document.createElement('img');
        img.src = logo.src;
        img.alt = logo.alt || '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.draggable = false;
        li.appendChild(img);
        list.appendChild(li);
      });
      return list;
    }

    // The first copy is the one we measure against; more copies are appended
    // once we know its width, so the strip covers the container with enough
    // spare width for a seamless loop.
    const firstList = buildList();
    track.appendChild(firstList);

    let sequenceWidth = 0;
    let offset = 0;
    let rafId = null;
    let lastTimestamp = null;
    let hovered = false;

    function layout() {
      sequenceWidth = firstList.getBoundingClientRect().width;
      if (!sequenceWidth) return;
      const containerWidth = containerEl.clientWidth;
      const copiesNeeded = Math.ceil(containerWidth / sequenceWidth) + 2;
      while (track.children.length < copiesNeeded) {
        track.appendChild(buildList());
      }
      while (track.children.length > copiesNeeded && track.children.length > 2) {
        track.removeChild(track.lastElementChild);
      }
    }

    function animate(timestamp) {
      if (lastTimestamp === null) lastTimestamp = timestamp;
      const deltaSeconds = Math.max(0, timestamp - lastTimestamp) / 1000;
      lastTimestamp = timestamp;

      if (!hovered && sequenceWidth > 0) {
        offset = (offset + speed * deltaSeconds) % sequenceWidth;
        track.style.transform = `translate3d(${-offset}px, 0, 0)`;
      }
      rafId = requestAnimationFrame(animate);
    }

    function handleResize() { layout(); }
    window.addEventListener('resize', handleResize);

    function handleEnter() { hovered = true; }
    function handleLeave() { hovered = false; }
    if (pauseOnHover) {
      containerEl.addEventListener('mouseenter', handleEnter);
      containerEl.addEventListener('mouseleave', handleLeave);
    }

    // Wait for the logo images to load before measuring, otherwise the
    // sequence width is measured against zero-size broken images.
    const images = firstList.querySelectorAll('img');
    let pending = images.length;
    function onImageSettled() {
      pending -= 1;
      if (pending <= 0) {
        layout();
        if (rafId === null && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
          rafId = requestAnimationFrame(animate);
        }
      }
    }
    if (!images.length) {
      onImageSettled();
    } else {
      images.forEach(img => {
        if (img.complete) onImageSettled();
        else {
          img.addEventListener('load', onImageSettled, { once: true });
          img.addEventListener('error', onImageSettled, { once: true });
        }
      });
    }

    return function teardown() {
      if (rafId !== null) cancelAnimationFrame(rafId);
      window.removeEventListener('resize', handleResize);
      if (pauseOnHover) {
        containerEl.removeEventListener('mouseenter', handleEnter);
        containerEl.removeEventListener('mouseleave', handleLeave);
      }
      containerEl.innerHTML = '';
    };
  }

  window.initLogoLoop = initLogoLoop;
})();
