# Aurora Background for Login & Landing Pages — Design Spec

Date: 2026-07-20

## Goal

Upgrade the visual polish of the login screen and the two landing pages
(`landing.html`, `landing-en.html`) by adding a subtle, animated aurora-glow
background, without changing the existing dark navy/gold/teal theme, layout,
or any dashboard functionality.

## Source

Ported from the React Bits `SoftAurora` component (React + `ogl` WebGL
renderer). This project has no React, no bundler, and no npm dependency
chain in `frontend/`, so the component is reimplemented as a small vanilla-JS
module using the raw WebGL2 API directly — no `ogl` package dependency is
introduced. The shader logic (Perlin noise, aurora glow band, cosine-gradient
color cycling) is preserved as-is from the source; only the component
wrapper changes.

## Scope

**In scope:**
- New file `frontend/aurora-bg.js` — a self-contained vanilla-JS aurora
  renderer, exposing one function: `initAuroraBackground(containerEl, options)`.
- New file `frontend/aurora-bg.css` — sizing/positioning rules for the
  aurora canvas container (`.aurora-bg`).
- Mount points added to three existing pages:
  - `frontend/index.html` — inside `#loginScreen`, behind `.login-box`.
  - `frontend/landing.html` and `frontend/landing-en.html` — behind the
    existing hero content.
- `CLAUDE.md` updated to document the new files under "Core Architecture"
  and note the aurora background as an additive UI enhancement.

**Out of scope / untouched:**
- `#appBgCanvas` (existing dashboard background element) — not modified.
- Any policy simulation logic, API routes, schema, or backend code.
- Any existing color variables, fonts, or layout in `styles.css`.
- No new npm/pip dependencies; no build step introduced.

## Visual Design

- **Placement:** one aurora instance per page — login screen, `landing.html`,
  `landing-en.html`. Each gets its own `<div class="aurora-bg">` container
  with its own WebGL canvas, sized to fill its parent via CSS
  (`position: absolute; inset: 0;`), positioned behind existing content via
  `z-index` (below `.login-box` / hero content, above the plain background
  color).
- **Colors:** `color1 = "#E8A04A"` (gold-light), `color2 = "#0CC8A8"` (teal)
  — both existing CSS custom properties, passed as plain hex constants into
  the aurora module's options (the module itself has no dependency on
  `styles.css` variables; values are duplicated as JS constants to keep the
  module standalone).
- **Intensity preset (subtle ambient glow):**
  - `speed: 0.35`
  - `brightness: 0.55`
  - `scale: 1.5` (default)
  - `bandHeight: 0.5`, `bandSpread: 1.0` (defaults)
  - `enableMouseInteraction: false`
- No fallback path for WebGL-unavailable browsers — this is an internal
  ministry tool on standard office machines; if WebGL2 context creation
  fails, `initAuroraBackground` logs a console warning and leaves the
  container empty (plain background color still shows through, since the
  aurora div has no opaque fill of its own).

## Component API

```js
// aurora-bg.js
export function initAuroraBackground(containerEl, options = {}) {
  // options: { speed, scale, brightness, color1, color2, noiseFrequency,
  //            noiseAmplitude, bandHeight, bandSpread, octaveDecay,
  //            layerOffset, colorSpeed, enableMouseInteraction, mouseInfluence }
  // Returns a teardown function: () => void, to remove the canvas and
  // cancel the animation frame (mirrors the React version's cleanup).
}
```

Called once per page, on `DOMContentLoaded`, e.g.:

```js
initAuroraBackground(document.getElementById('auroraLogin'), {
  color1: '#E8A04A',
  color2: '#0CC8A8',
  speed: 0.35,
  brightness: 0.55,
  enableMouseInteraction: false,
});
```

Since the login screen is always present in the DOM (just toggled via the
`.visible` class, not re-created), the aurora only needs to be initialized
once on page load — no re-init logic needed when the login screen is shown
again after logout.

## File Changes Summary

| File | Change |
|---|---|
| `frontend/aurora-bg.js` | New. WebGL2 aurora renderer + `initAuroraBackground()`. |
| `frontend/aurora-bg.css` | New. `.aurora-bg` container positioning rules. |
| `frontend/index.html` | Add `<div class="aurora-bg" id="auroraLogin">` inside `#loginScreen`; add `<link>`/`<script>` includes; call `initAuroraBackground` on load. |
| `frontend/landing.html` | Same pattern, hero section. |
| `frontend/landing-en.html` | Same pattern, hero section. |
| `CLAUDE.md` | Document new files in the file table; note aurora background as an additive frontend enhancement (no policy-logic impact). |

## Testing

Manual only (this is a pure frontend visual change):
- Load `index.html` → confirm aurora glow visible and subtle behind the
  login box, text/inputs remain fully legible, no console errors.
- Load `landing.html` and `landing-en.html` → confirm same behind hero.
- Resize browser window → aurora canvas resizes correctly, no distortion.
- Confirm dashboard (post-login) is visually unchanged — `#appBgCanvas`
  and all existing styling untouched.
