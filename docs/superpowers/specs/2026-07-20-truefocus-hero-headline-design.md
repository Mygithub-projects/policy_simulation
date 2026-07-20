# TrueFocus Hero Headline — Design Spec

Date: 2026-07-20

## Goal

Upgrade the landing pages' hero headline ("Analyse. / Simulate. / Decide." on
`landing-en.html`, "Analisis. / Simulasi. / Keputusan." on `landing.html`)
from a static 3-line heading into an auto-cycling focus animation, using the
React Bits `TrueFocus` component as reference — ported to vanilla JS to match
this project's dependency-free frontend, following the same pattern already
established for the aurora background (`frontend/aurora-bg.js`).

## Source

Ported from React Bits `TrueFocus` (React + `motion`/framer-motion). This
project has no React/npm build step, so the component is reimplemented as a
small vanilla-JS module: a glowing corner-bracket frame that measures the
active word's `getBoundingClientRect()` and animates to it via CSS
transitions, cycling through words on a timer. No `motion` package is
introduced.

## Scope

**In scope:**
- New file `frontend/true-focus.js` — `initTrueFocus(containerEl, options)`,
  vanilla-JS port of the focus/blur/glow-frame behavior.
- New file `frontend/true-focus.css` — `.focus-word`, `.focus-frame`, corner
  bracket styles (adapted from the component's original CSS).
- Hero headline markup in `frontend/landing.html` and
  `frontend/landing-en.html` changed from static spans to a
  script-hydrated container (see Markup below).
- `CLAUDE.md` updated to document the two new files.

**Out of scope / untouched:**
- Login screen headline/branding — not affected.
- `#appBgCanvas` / dashboard — not affected.
- The aurora background integration — untouched, coexists behind this.
- No new dependencies; no build step.

## Markup

Replace the current static headline:
```html
<h1 class="hero-headline">
  <span>Analyse.</span><br>
  <span class="word-highlight">Simulate.</span><br>
  <span class="word-teal">Decide.</span>
</h1>
```
with a data-driven container the script hydrates on load:
```html
<h1 class="hero-headline" id="heroFocus"
    data-words="Analyse.|Simulate.|Decide."
    data-word-classes="|word-highlight|word-teal"
    data-word-glows="rgba(240,244,255,0.5)|#C4781C|#0CC8A8">
</h1>
```
(BM version: `data-words="Analisis.|Simulasi.|Keputusan."`, same
`data-word-classes` and `data-word-glows`.)

`initTrueFocus` splits each `data-*` attribute on `|`, builds one `<span>`
per word (applying the existing per-word class so the gold-box highlight and
teal color are preserved exactly as today), inserts each on its own line
(matching current stacked layout via `<br>` between spans), and appends the
glow-frame `<div>` used to draw the animated corner brackets.

## Behavior

- **Auto-cycle**, no manual/hover mode: words take turns being "in focus"
  automatically — matches the ambient, non-interactive feel already
  established by the aurora background.
- **Timing:** `animationDuration: 0.6s`, `pauseBetweenAnimations: 1.4s` per
  word (roughly matching the original demo's pacing, tuned slightly slower
  for a 3-word headline instead of a full sentence).
- **Blur amount:** `2.5px` on inactive words (lighter than the component's
  5px default) — softens without hurting headline readability.
- **Glow/border color:** per-word, read from `data-word-glows`, so the
  glowing frame matches each word's existing brand color (soft white for
  "Analyse.", gold for "Simulate.", teal for "Decide.") instead of one fixed
  color for the whole sentence.

## Component API

```js
// true-focus.js
export function initTrueFocus(containerEl, options = {}) {
  // options: { words: string[], wordClasses: string[], wordGlows: string[],
  //            blurAmount, animationDuration, pauseBetweenAnimations }
  // Reads containerEl's data-words/data-word-classes/data-word-glows if
  // options are omitted. Returns a teardown function: () => void.
}
```

Called once per landing page on `DOMContentLoaded`:
```js
initTrueFocus(document.getElementById('heroFocus'));
```

## File Changes Summary

| File | Change |
|---|---|
| `frontend/true-focus.js` | New. Vanilla-JS port of TrueFocus (word cycling + glow frame). |
| `frontend/true-focus.css` | New. `.focus-word`, `.focus-frame`, corner bracket styles. |
| `frontend/landing.html` | Hero headline markup → data-driven container; script include + init call. |
| `frontend/landing-en.html` | Same. |
| `CLAUDE.md` | Document the two new files under Core Architecture. |

## Testing

Manual only (pure frontend visual change):
- Load both landing pages → confirm headline cycles focus across all three
  words automatically, each word's original color/highlight preserved.
- Confirm inactive words are legible (subtle blur, not distracting).
- Resize browser window → glow frame re-measures and repositions correctly.
- Confirm login screen and dashboard are visually unchanged.
