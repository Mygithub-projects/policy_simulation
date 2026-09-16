/**
 * Cursor-origin expanding-fill interaction for CTA/action buttons.
 *
 * Targets every element matching SELECTOR (the app's .btn family, plus the
 * marketing landing pages' .btn-nav / .btn-primary-lg / .btn-ghost-lg CTAs).
 * The actual fill circle and color fade live in CSS (styles.css / the
 * landing pages' own <style> blocks) driven by the --fill-x / --fill-y /
 * --fill-d custom properties and the .is-filling class this file sets.
 *
 * Listeners are delegated on `document` rather than attached per-button, so
 * there is nothing to wire up or tear down for buttons that get created
 * after load (e.g. the error-retry button in app.js's renderError()) and
 * nothing to leak.
 */
(function () {
  var SELECTOR = '.btn, .btn-nav, .btn-primary-lg, .btn-ghost-lg';

  function setOrigin(btn, x, y, rect) {
    var d = Math.ceil(Math.hypot(rect.width, rect.height) * 2);
    btn.style.setProperty('--fill-x', x + 'px');
    btn.style.setProperty('--fill-y', y + 'px');
    btn.style.setProperty('--fill-d', d + 'px');
  }

  function centerOrigin(btn) {
    var rect = btn.getBoundingClientRect();
    setOrigin(btn, rect.width / 2, rect.height / 2, rect);
  }

  function pointerOrigin(btn, evt) {
    var rect = btn.getBoundingClientRect();
    setOrigin(btn, evt.clientX - rect.left, evt.clientY - rect.top, rect);
  }

  function isDisabled(btn) {
    return btn.disabled || btn.getAttribute('aria-disabled') === 'true';
  }

  // Non-touch pointer entering a button: fill grows from the cursor's entry
  // point. Touch: always use the center (a finger covers the exact contact
  // point anyway, and this doubles as the touch "preview" on tap).
  document.addEventListener('pointerover', function (e) {
    var btn = e.target.closest(SELECTOR);
    if (!btn || isDisabled(btn)) return;
    if (e.relatedTarget && btn.contains(e.relatedTarget)) return;
    if (e.pointerType === 'touch') centerOrigin(btn);
    else pointerOrigin(btn, e);
    btn.classList.add('is-filling');
  });

  // Track the cursor while hovering so a leave-without-crossing-elsewhere
  // still shrinks back toward the last real position, not a stale one.
  document.addEventListener('pointermove', function (e) {
    if (e.pointerType === 'touch') return;
    var btn = e.target.closest(SELECTOR);
    if (!btn || !btn.classList.contains('is-filling')) return;
    pointerOrigin(btn, e);
  });

  function handleLeave(e) {
    var btn = e.target.closest(SELECTOR);
    if (!btn) return;
    if (e.relatedTarget && btn.contains(e.relatedTarget)) return;
    btn.classList.remove('is-filling');
  }
  document.addEventListener('pointerout', handleLeave);
  document.addEventListener('pointercancel', handleLeave);

  // Keyboard focus previews the fill from the button's center, same as
  // touch. :focus-visible keeps this from firing on a mouse click that
  // happens to leave the button focused (that case is already covered by
  // pointerover above, with the real cursor position as origin).
  document.addEventListener('focusin', function (e) {
    var btn = e.target.closest(SELECTOR);
    if (!btn || isDisabled(btn)) return;
    if (!btn.matches(':focus-visible')) return;
    centerOrigin(btn);
    btn.classList.add('is-filling');
  });

  document.addEventListener('focusout', function (e) {
    var btn = e.target.closest(SELECTOR);
    if (btn) btn.classList.remove('is-filling');
  });
})();
