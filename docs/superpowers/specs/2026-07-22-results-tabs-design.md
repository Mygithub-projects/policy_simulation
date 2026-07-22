# Results Area Tabs — Design Spec

Date: 2026-07-22

## Problem

The simulation results area (`#resultsWrapper` in [frontend/index.html](../../../frontend/index.html)) currently renders as one long vertical stack: scenario banner, KPI grid, decision insight, combined-policy impact table, three charts, plain-language explanation, strategic recommendations, and a 30-row priority schools table. Users must scroll through all of it to reach later sections, even when they only care about one part (e.g. jumping straight to the schools table).

## Goal

Split the results area into 5 tabs so each section is reachable without scrolling past the others:

1. **Overview** — scenario banner, KPI cards, decision insight, combined-policy impact table (Combined mode only)
2. **Charts** — the 3-chart grid (comparison, subject, risk)
3. **Explanation** — plain-language summary ("Ringkasan Bahasa Mudah")
4. **Strategic Recommendations** — the rules-based recommendation list
5. **Priority Schools** — the top-30 schools table

## Non-goals

- No change to how results are computed, fetched, or rendered internally (chart draws, table population, KPI formatting all stay as-is).
- No change to the PDF export pipeline (`pdfExplanation`, `pdfKpiGrid`, etc.) — it already uses its own separate hidden containers, populated independently of the visible tabs.
- No change to the "Simulasi Saya" (My Runs) re-download flow, which also targets the same visible DOM (see below).

## Structure

Inside `#resultsWrapper` ([frontend/index.html](../../../frontend/index.html)):

```html
<div class="results-wrapper" id="resultsWrapper">
  <div class="result-tabs" id="resultTabs">
    <button class="result-tab active" data-tab="overview">Ikhtisar</button>
    <button class="result-tab" data-tab="charts">Carta</button>
    <button class="result-tab" data-tab="explanation">Penjelasan</button>
    <button class="result-tab" data-tab="recs">Cadangan Strategik</button>
    <button class="result-tab" data-tab="schools">Sekolah Keutamaan</button>
  </div>

  <div class="tab-panel active" data-tab="overview">
    <!-- scenarioBanner, kpiGrid, decisionInsight, policyImpactCard -->
  </div>
  <div class="tab-panel" data-tab="charts">
    <!-- chart-grid: chartComparison, chartSubject, chartRisk -->
  </div>
  <div class="tab-panel" data-tab="explanation">
    <!-- explanationBox result-card -->
  </div>
  <div class="tab-panel" data-tab="recs">
    <!-- rulesList result-card -->
  </div>
  <div class="tab-panel" data-tab="schools">
    <!-- recTable result-card -->
  </div>
</div>
```

All existing element IDs (`kpiGrid`, `decisionInsight`, `policyImpactCard`, `chartComparison`, `chartSubject`, `chartRisk`, `explanationBox`, `rulesList`, `recTable`, `tableInfo`) are preserved unchanged — they simply live one level deeper, nested inside their respective `.tab-panel`. No `getElementById` call in `app.js` needs to change.

## Rendering approach

**Pre-render all, toggle visibility.** All 5 tab panels render immediately as part of the existing `renderResults()` flow (same as today — nothing becomes lazy). Only the CSS `display` state changes on tab switch:

```css
.tab-panel { display: none; }
.tab-panel.active { display: block; }
```

Charts render once, at the moment results arrive, exactly as they do today — no change to the chart-draw call sites. However, since **Overview** is the default active tab, the Charts panel is `display:none` at that exact moment, and Chart.js cannot size a canvas correctly inside a hidden container (it reads 0 width/height). To handle this, `setActiveResultTab('charts')` calls `chart.resize()` on the three existing Chart.js instances (`chartComparison`, `chartSubject`, `chartRisk` — whichever the codebase already holds a reference to) immediately after making the Charts panel visible. This is a one-line addition per instance, not a re-render — the underlying data/options are untouched, only the canvas is resized to its now-visible container.

## Tab switching behavior

New function in [frontend/app.js](../../../frontend/app.js), following the existing `setActiveGroup()` pattern used for the sidebar accordion:

```js
let activeResultTab = 'overview';

function setActiveResultTab(tab) {
  activeResultTab = tab;
  document.querySelectorAll('.result-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(panel =>
    panel.classList.toggle('active', panel.dataset.tab === tab));
}
```

- Bound via `onclick="setActiveResultTab('...')"` on each `.result-tab` button, matching the existing inline-onclick convention used by sidebar rail icons and group headers.
- **Resets to `overview` on every fresh render.** `renderResults()` calls `setActiveResultTab('overview')` at the start of its render, so a new simulation (or a "Simulasi Saya" re-download re-run) always lands back on the Overview tab rather than staying on whatever tab was previously open.

## Styling

New rules in [frontend/styles.css](../../../frontend/styles.css), visually consistent with the existing sidebar rail's active-state treatment (gold accent, matching `--gold-lt` / `--gold`):

- `.result-tabs`: horizontal flex row, `position: sticky; top: 0;`, solid background (not transparent) matching the main panel's background color so scrolled content doesn't show through underneath it, `border-bottom: 1px solid var(--border)`, `z-index` above `.tab-panel` content.
- `.result-tab`: transparent button, muted text color by default.
- `.result-tab.active`: `color: var(--gold-lt)`, `border-bottom: 2px solid var(--gold)` (underline indicator), matching the accent style already used for the sidebar's active group.
- `.tab-panel`: no special layout styling needed beyond `display` toggling — internal spacing (`result-card` margins, `chart-grid` gutters, etc.) stays exactly as it is today, since it's the same DOM just re-wrapped.

## Interactions with existing features

- **Combined policy mode**: `policyImpactCard`'s existing `style="display:none"` show/hide logic (driven by single vs. combined policy mode selection) is untouched — it still lives inside the Overview panel and shows/hides independently of the tab system.
- **PDF export**: generates from `pdfExplanation`/`pdfKpiGrid` and other dedicated PDF-only containers already separate from the visible tabs — confirmed no interaction. The existing ~1200ms wait before PDF generation (used by the "Simulasi Saya" re-download flow, see [2026-07-12 My Runs design](2026-07-12-policy-maker-my-runs-design.md)) is unaffected since it doesn't depend on which tab is visually active.
- **"Simulasi Saya" re-download**: re-runs the scenario and calls `renderResults()`, same as any simulation — inherits the reset-to-Overview behavior above.

## Testing checklist

- Run a single-policy simulation → confirm all 5 tabs populate, Overview shown by default.
- Run a combined-policy simulation → confirm `policyImpactCard` appears inside Overview tab.
- Switch to the Charts tab after landing on Overview → confirm all 3 charts render at full size (not blank/squished from being drawn into a hidden container), verifying the `chart.resize()` calls fire correctly.
- Confirm sticky tab bar stays visible while scrolling within the tall Priority Schools tab.
- Run "Simulasi Saya" re-download → confirm tab resets to Overview, PDF still generates correctly.
- Test in both BM and EN language toggle (tab labels need `data-i18n` keys added to [frontend/lang.js](../../../frontend/lang.js)).
