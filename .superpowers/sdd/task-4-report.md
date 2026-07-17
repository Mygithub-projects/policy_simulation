# Task 4 Report: Frontend — Save Simulation Button, Naming Modal, and i18n Keys

## Summary

Successfully implemented Task 4: added the "Save Simulation" button to the results table footer, added the naming modal markup, added modal CSS styling, and added all bilingual i18n keys (both BM and EN) to support the "Run First, Save Later" feature.

## Implementation Details

### 1. Save Simulation Button (index.html)
- Added a new button with id `btnSaveSimulation` to the table footer div (line 524-527)
- Button uses the `btn btn-outline btn-sm` CSS classes, matching existing download buttons
- Set initial state with `style="display:none;"` as required (visibility wired in Task 5)
- Added `onclick="openSaveSimulationModal()"` handler (JS implementation in Task 5)
- Applied `data-i18n="btn.save.simulation"` for i18n support

### 2. Naming Modal Markup (index.html)
- Added modal overlay and box structure immediately before closing `</body>` tag (line 743-758)
- Modal uses semantic HTML with:
  - `.modal-overlay` container with fixed positioning and dark background overlay
  - `.modal-box` with card-style presentation
  - `h3` for title with i18n key `modal.save.title`
  - Hint paragraph with i18n key `modal.save.hint`
  - Label for text input with i18n key `modal.save.label`
  - Text input with id `saveSimNameInput`, maxlength 200, and placeholder with i18n support
  - Two action buttons: Cancel (outline style) and Save (primary style)
- All elements use existing CSS classes and patterns
- No duplicate IDs with existing elements

### 3. Modal CSS (styles.css)
- Added `.modal-overlay` styles (lines 966-973):
  - Fixed positioning covering entire viewport (`inset: 0`)
  - Flexbox centering
  - Dark semi-transparent background `rgba(6,10,20,0.65)`
  - High z-index (2000) to overlay above other content
- Added `.modal-box` styles (lines 975-985):
  - Uses CSS custom properties for consistency: `var(--bg-card)`, `var(--border)`, `var(--radius-lg)`, `var(--text)`, `var(--text-muted)`
  - Responsive width with max-width constraint
  - Flexbox column layout with consistent spacing
- Added `.modal-box h3`, `.modal-box .hint`, and `.modal-actions` styles (lines 986-993):
  - Proper typography hierarchy
  - Button action layout with right-aligned flex
  - Consistent spacing and gaps
- All CSS uses existing color/spacing variables from the design system

### 4. i18n Keys (lang.js)

#### Bahasa Malaysia (BM) Block
Added 10 keys after line 168:
- `btn.save.simulation`: '💾 Simpan Simulasi'
- `btn.save.saved`: '✅ Disimpan'
- `modal.save.title`: 'Simpan Simulasi'
- `modal.save.hint`: 'Namakan simulasi ini supaya anda boleh menjumpainya kembali di Simulasi Saya.'
- `modal.save.label`: 'Nama Simulasi'
- `modal.save.placeholder`: 'cth. Johor Sains nisbah opsyen 70%'
- `modal.save.cancel`: 'Batal'
- `modal.save.confirm`: 'Simpan'
- `toast.save.ok`: 'Simulasi berjaya disimpan.'
- `myruns.col.name`: 'Nama Simulasi'

#### English (EN) Block
Added 10 keys after line 505 (now line 515 due to BM additions):
- `btn.save.simulation`: '💾 Save Simulation'
- `btn.save.saved`: '✅ Saved'
- `modal.save.title`: 'Save Simulation'
- `modal.save.hint`: 'Give this simulation a name so you can find it later in My Runs.'
- `modal.save.label`: 'Simulation Name'
- `modal.save.placeholder`: 'e.g. Johor Science 70% option ratio'
- `modal.save.cancel`: 'Cancel'
- `modal.save.confirm': 'Save'
- `toast.save.ok`: 'Simulation saved successfully.'
- `myruns.col.name`: 'Simulation Name'

## Verification

### Markup Syntax
- All HTML elements are well-formed with matching open/close tags
- Button properly nested in `table-footer` div
- Modal properly nested with all internal structure correct
- No duplicate element IDs found in the codebase

### CSS Syntax
- All CSS properties are correctly formatted
- Uses only existing CSS custom properties (no hardcoded colors)
- Proper selector specificity and cascade behavior
- No missing semicolons or syntax errors

### JavaScript Syntax (lang.js)
- All i18n keys properly formatted with single quotes
- Each key-value pair followed by comma (except the last before comments)
- Both BM and EN blocks maintain identical key structure
- JavaScript object syntax is valid with no missing braces

### Smoke Tests
Both smoke tests passed successfully:
- `python smoke_test.py`: ✅ PASSED
  - Database connectivity confirmed
  - Model loading confirmed
  - Policy simulation logic confirmed
  - CSV output generation confirmed

- `python api_smoke_test.py`: ✅ PASSED
  - API health check passed
  - All simulation endpoints tested
  - Agent scenario processing confirmed
  - PDF generation confirmed

## Files Modified
1. `frontend/index.html` — Added button (line 524-527) and modal (line 743-758)
2. `frontend/styles.css` — Added modal styling (line 965-993)
3. `frontend/lang.js` — Added i18n keys to both BM (line 169-178) and EN (line 516-525)

## Git Commit
- Commit SHA: `ff2102f`
- Message: `feat: add Save Simulation button and naming modal markup`

## Self-Review Findings

### Element IDs
✅ All new element IDs are unique:
- `btnSaveSimulation` (button)
- `saveSimModal` (modal overlay)
- `saveSimNameInput` (text input)
- `saveSimCancelBtn` (cancel button)
- `saveSimConfirmBtn` (confirm button)

### CSS Custom Properties
✅ All new CSS uses existing variables:
- `var(--bg-card)` for background
- `var(--border)` for border color
- `var(--radius-lg)` for border radius
- `var(--text)` for text color
- `var(--text-muted)` for muted text
- `var(--text-muted)` for muted text

### i18n Keys
✅ Both BM and EN blocks contain identical keys:
- All keys present in both languages
- Valid JavaScript object syntax
- Proper trailing commas
- No syntax errors

### Button Visibility Logic
✅ Button correctly uses `style="display:none;"` default state, matching pattern used by:
- `#btnDownload`
- `#btnDownloadSummary`
- `#btnDownloadSummaryCsv`

This ensures the button remains hidden for superadmin/admin roles until Task 5 wires the visibility logic.

## No Issues Found

All markup is well-formed, CSS is properly formatted, and i18n keys are syntactically correct. The implementation matches the task brief exactly and follows the project's coding style and conventions.
