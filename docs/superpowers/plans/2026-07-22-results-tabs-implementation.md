# Results Area Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the simulation results area into 5 tabs (Overview, Charts, Explanation, Strategic Recommendations, Priority Schools) so users reach any section without scrolling through all of them.

**Architecture:** Pure frontend change. Wrap the existing result sections in `.tab-panel` divs inside `#resultsWrapper` (no change to what renders inside them), add a sticky `.result-tabs` button row above them, and add one JS function (`setActiveResultTab`) that toggles visibility and resizes the three Chart.js instances when the Charts tab becomes visible for the first time after a hidden draw.

**Tech Stack:** Vanilla HTML/CSS/JS (no build step, no JS test framework — this project's frontend has none; verification is manual browser testing via Playwright MCP, matching the existing manual testing checklist in `CLAUDE.md`).

## Global Constraints

- No change to any existing element ID (`kpiGrid`, `decisionInsight`, `policyImpactCard`, `chartComparison`, `chartSubject`, `chartRisk`, `explanationBox`, `rulesList`, `recTable`, `tableInfo`) — `app.js`'s `getElementById` calls must keep working unmodified.
- No change to chart draw call sites, render functions, or the PDF export pipeline (`pdfExplanation`, `pdfKpiGrid`, etc.) — those are separate, untouched containers.
- Pre-render all tab content; only toggle `display` on switch — no lazy rendering.
- Default active tab is always `overview`, reset on every `renderResults()` call.
- Tab bar is `position: sticky; top: 0` within the scrollable `.main-panel`.
- Styling must reuse existing CSS variables (`--gold`, `--gold-lt`, `--border`, `--bg-card`) — no new hex colors.
- Both BM and EN language strings required for every new user-visible label (`frontend/lang.js`).

---

### Task 1: Restructure `index.html` results area into tab bar + panels

**Files:**
- Modify: `frontend/index.html:543-639` (the `#resultsWrapper` block)

**Interfaces:**
- Produces: `#resultTabs` (tab button row), 5 `.tab-panel[data-tab="..."]` divs (`overview`, `charts`, `explanation`, `recs`, `schools`) that Task 2 (CSS) and Task 3 (JS) depend on. All existing inner IDs unchanged.

- [ ] **Step 1: Replace the results-wrapper contents**

Read the current block first to confirm exact current content (it was last read at these lines: scenario banner through the schools table closing at line 639). Replace lines 543-639 with:

```html
        <!-- ---- RESULTS ---- -->
        <div class="results-wrapper" id="resultsWrapper">

          <div class="result-tabs" id="resultTabs">
            <button class="result-tab active" data-tab="overview" onclick="setActiveResultTab('overview')" data-i18n="tab.overview">Ikhtisar</button>
            <button class="result-tab" data-tab="charts" onclick="setActiveResultTab('charts')" data-i18n="tab.charts">Carta</button>
            <button class="result-tab" data-tab="explanation" onclick="setActiveResultTab('explanation')" data-i18n="tab.explanation">Penjelasan</button>
            <button class="result-tab" data-tab="recs" onclick="setActiveResultTab('recs')" data-i18n="tab.recs">Cadangan Strategik</button>
            <button class="result-tab" data-tab="schools" onclick="setActiveResultTab('schools')" data-i18n="tab.schools">Sekolah Keutamaan</button>
          </div>

          <div class="tab-panel active" data-tab="overview">
            <div class="scenario-banner" id="scenarioBanner"></div>
            <div class="kpi-grid" id="kpiGrid"></div>
            <div class="decision-insight" id="decisionInsight"></div>

            <div class="result-card" id="policyImpactCard" style="display:none;">
              <div class="result-card-header teal" data-i18n="card.policy">Kesan Dasar Individu dan Gabungan</div>
              <div class="result-card-body">
                <div class="table-container">
                  <table class="rec-table">
                    <thead>
                      <tr>
                        <th data-i18n="th.condition">Keadaan</th>
                        <th data-i18n="th.required">Guru Diperlukan</th>
                        <th data-i18n="th.change">Perubahan</th>
                        <th data-i18n="th.shortage">Kekurangan Guru</th>
                        <th data-i18n="th.opt.shortage">Kekurangan Guru Opsyen Mata Pelajaran</th>
                      </tr>
                    </thead>
                    <tbody id="policyImpactBody"></tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div class="tab-panel" data-tab="charts">
            <div class="chart-grid">
              <div class="result-card">
                <div class="result-card-header" id="comparisonChartTitle" data-i18n="card.comparison">
                  Perbandingan Permintaan Guru
                </div>
                <div class="result-card-body">
                  <div class="chart-wrap"><canvas id="chartComparison"></canvas></div>
                </div>
              </div>
              <div class="result-card">
                <div class="result-card-header teal" data-i18n="card.subject">Permintaan Mengikut Mata Pelajaran</div>
                <div class="result-card-body">
                  <div class="chart-wrap"><canvas id="chartSubject"></canvas></div>
                  <div class="subject-chips" id="subjectChips" style="margin-top:14px;"></div>
                </div>
              </div>
              <div class="result-card">
                <div class="result-card-header amber" id="riskChartTitle" data-i18n="card.risk">
                  Ranking Risiko Negeri
                </div>
                <div class="result-card-body">
                  <div class="chart-wrap"><canvas id="chartRisk"></canvas></div>
                </div>
              </div>
            </div>
          </div>

          <div class="tab-panel" data-tab="explanation">
            <div class="result-card">
              <div class="result-card-header amber" data-i18n="card.summary">Ringkasan Bahasa Mudah</div>
              <div class="result-card-body">
                <div class="explanation-box" id="explanationBox"></div>
              </div>
            </div>
          </div>

          <div class="tab-panel" data-tab="recs">
            <div class="result-card">
              <div class="result-card-header" data-i18n="card.recs">Cadangan Strategik</div>
              <div class="result-card-body">
                <ul class="rules-list" id="rulesList"></ul>
              </div>
            </div>
          </div>

          <div class="tab-panel" data-tab="schools">
            <div class="result-card">
              <div class="result-card-header">
                <span data-i18n="card.schools">Sekolah Keutamaan — 30 Teratas</span>
                <div class="header-actions">
                  <span id="tableInfo">—</span>
                </div>
              </div>
              <div class="result-card-body">
                <div class="table-container">
                  <table class="rec-table" id="recTable">
                    <thead>
                      <tr>
                        <th data-i18n="th.num">#</th>
                        <th data-i18n="th.school.code">Kod Sekolah</th>
                        <th data-i18n="th.state">Negeri</th>
                        <th data-i18n="th.ppd">PPD</th>
                        <th data-i18n="th.subject">Mata Pelajaran</th>
                        <th data-i18n="th.est.without">Anggaran tanpa perubahan dasar</th>
                        <th data-i18n="th.est.after">Anggaran selepas perubahan dasar</th>
                        <th data-i18n="th.teacher.shortage">Kekurangan Guru</th>
                        <th data-i18n="th.priority">Keutamaan</th>
                        <th data-i18n="th.action">Tindakan Dicadangkan</th>
                      </tr>
                    </thead>
                    <tbody id="recTableBody"></tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

        </div>
        <!-- ---- END RESULTS ---- -->
```

Note `policyImpactCard` moved from a full-width `result-card` between the chart grid and the summary card into the Overview tab panel — same element, same `id`, same `style="display:none;"` default, only its position in the document changed.

- [ ] **Step 2: Visually sanity-check the HTML is well-formed**

Run: `grep -c "tab-panel" frontend/index.html`
Expected: `6` (5 opening `class="tab-panel` matches + this grep also counts the word inside comments/none — verify manually by opening the file if the count looks off). More reliably, run:

```bash
node -e "require('fs').readFileSync('frontend/index.html','utf8')" 
```
Expected: no output, no error (confirms the file is at least readable; full HTML parsing isn't necessary since this is a plain text edit — the real check is Task 5's browser verification).

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: wrap results sections into tab panels"
```

---

### Task 2: Add tab bar and panel CSS

**Files:**
- Modify: `frontend/styles.css` (add new rules near the existing `.results-wrapper` rules around line 1133)

**Interfaces:**
- Consumes: `.result-tabs`, `.result-tab`, `.result-tab.active`, `.tab-panel`, `.tab-panel.active` class names produced by Task 1.

- [ ] **Step 1: Read the current `.results-wrapper` rule for exact insertion point**

Run: `grep -n "results-wrapper" frontend/styles.css`
Expected output includes `1133:.results-wrapper { display: none; flex-direction: column; gap: 16px; }` and `1134:.results-wrapper.visible { display: flex; }`.

- [ ] **Step 2: Insert new rules immediately after line 1134**

Insert this block right after the `.results-wrapper.visible { display: flex; }` line:

```css
.result-tabs {
  display: flex;
  gap: 4px;
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  padding: 0 4px;
}

.result-tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgba(255,255,255,0.55);
  font-size: 13px;
  font-weight: 600;
  padding: 12px 14px;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.result-tab:hover { color: rgba(255,255,255,0.80); }

.result-tab.active {
  color: var(--gold-lt);
  border-bottom-color: var(--gold);
}

.tab-panel { display: none; flex-direction: column; gap: 16px; }
.tab-panel.active { display: flex; }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/styles.css
git commit -m "feat: style results tab bar and panels"
```

---

### Task 3: Add `setActiveResultTab` JS and wire it into `renderResults`

**Files:**
- Modify: `frontend/app.js:1311` (start of `renderResults`) and the sidebar-navigation section near `frontend/app.js:1155` (where `collapseSidebarAfterResult` and related nav helpers already live — add the new function there for consistency with the existing accordion-toggle pattern).

**Interfaces:**
- Consumes: `state.chartComparison`, `state.chartSubject`, `state.chartRisk` (existing Chart.js instances, already defined at `frontend/app.js:617-619`).
- Produces: `setActiveResultTab(tab)` — called from the `onclick` handlers added in Task 1, and from `renderResults()` to reset to `overview` on every fresh render.

- [ ] **Step 1: Add `setActiveResultTab` next to the other sidebar-nav helpers**

Insert this function after `collapseSidebarAfterResult` (which ends at `frontend/app.js:1159` based on the closing brace of that function):

```js
/** Switches the visible results tab. Charts are drawn once when results
 *  first render (while the Charts panel may still be display:none), so
 *  Chart.js needs an explicit resize() the first time that panel becomes
 *  visible — otherwise it keeps the 0x0 size it read at draw time. */
function setActiveResultTab(tab) {
  document.querySelectorAll('.result-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(panel =>
    panel.classList.toggle('active', panel.dataset.tab === tab));

  if (tab === 'charts') {
    [state.chartComparison, state.chartSubject, state.chartRisk].forEach(chart => {
      if (chart) chart.resize();
    });
  }
}
```

- [ ] **Step 2: Reset to the Overview tab on every fresh render**

In `renderResults` (`frontend/app.js:1311`), immediately after the existing line:

```js
  document.getElementById('resultsWrapper').classList.add('visible');
```

add:

```js
  setActiveResultTab('overview');
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app.js
git commit -m "feat: add result tab switching with chart resize on first Charts view"
```

---

### Task 4: Add BM/EN language strings for tab labels

**Files:**
- Modify: `frontend/lang.js` (both the `bm:` object starting at line 10 and the `en:` object starting at line 366 — insert near the existing `card.*` keys, e.g. right before `'card.comparison'` at line 235 for `bm` and line 591 for `en`)

**Interfaces:**
- Consumes: `data-i18n="tab.overview"` etc. attributes added in Task 1 — the generic `[data-i18n]` handler at `frontend/lang.js:751` already applies any key found here via `textContent`, no code change needed beyond adding the key/value pairs.

- [ ] **Step 1: Add BM keys**

In the `bm:` object, immediately before line 235 (`'card.comparison': 'Perbandingan Permintaan Guru',`), insert:

```js
    'tab.overview': 'Ikhtisar',
    'tab.charts': 'Carta',
    'tab.explanation': 'Penjelasan',
    'tab.recs': 'Cadangan Strategik',
    'tab.schools': 'Sekolah Keutamaan',
```

- [ ] **Step 2: Add EN keys**

In the `en:` object, immediately before line 591 (`'card.comparison': 'Teacher Demand Comparison',`), insert:

```js
    'tab.overview': 'Overview',
    'tab.charts': 'Charts',
    'tab.explanation': 'Explanation',
    'tab.recs': 'Recommendations',
    'tab.schools': 'Priority Schools',
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lang.js
git commit -m "feat: add BM/EN language strings for result tab labels"
```

---

### Task 5: Manual browser verification

**Files:** none (verification only — no code changes)

**Interfaces:** none.

This project has no JS test framework (per `CLAUDE.md`'s manual testing checklist convention) — verification is done by driving the running app in a real browser via the Playwright MCP tools, the same way the tab-collapse behavior was verified earlier in this project's development.

- [ ] **Step 1: Start the backend**

Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`
Expected: `Application startup complete.` in the log, no tracebacks.

- [ ] **Step 2: Log in and run a single-policy simulation**

Using the Playwright MCP browser tools: navigate to `http://127.0.0.1:8002/app/`, log in, leave Policy Simulation on "Dasar Tunggal" (single mode), click "Jalankan Simulasi 2027".

Expected: results appear with the Overview tab active by default — scenario banner, KPI cards, and decision insight visible; `policyImpactCard` NOT visible (single mode).

- [ ] **Step 3: Click the Charts tab**

Click the "Carta"/"Charts" tab button.

Expected: all 3 charts (`chartComparison`, `chartSubject`, `chartRisk`) render at full size, not blank or squished — confirming the `chart.resize()` calls in Task 3 worked. Take a screenshot to confirm visually.

- [ ] **Step 4: Click through Explanation, Strategic Recommendations, and Priority Schools tabs**

Expected: each shows only its own content (`explanationBox` text, `rulesList` items, `recTable` with 30 rows respectively) — no other tab's content visible, no layout overlap.

- [ ] **Step 5: Confirm the tab bar stays sticky**

While on the Priority Schools tab (the tallest one), scroll down within the main panel.

Expected: the tab bar (`#resultTabs`) remains pinned at the top of the visible results area while the table content scrolls underneath it.

- [ ] **Step 6: Run a combined-policy simulation**

Switch Policy Simulation to "Gabungan" (combined mode), select 2+ policies, run the simulation.

Expected: back on the Overview tab (reset confirmed), and `policyImpactCard`'s "Kesan Dasar Individu dan Gabungan" table is now visible inside the Overview panel.

- [ ] **Step 7: Confirm language toggle**

Click the "EN" language toggle.

Expected: all 5 tab labels switch to their English strings from Task 4 ("Overview", "Charts", "Explanation", "Recommendations", "Priority Schools") without a page reload.

- [ ] **Step 8: Confirm "Simulasi Saya" re-download still works (if logged in as a Policy Maker / `user` role account is available)**

If a `user`-role test account exists, log in as that role, open "Simulasi Saya", click download on a past run.

Expected: dashboard switches, scenario re-runs, results land on the Overview tab, and the PDF still generates correctly after the existing ~1200ms wait — confirming Task 3's tab reset doesn't interfere with the existing PDF pipeline.

If no such test account is available, skip this step and note it as unverified rather than guessing.
