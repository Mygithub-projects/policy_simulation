# Progress Ledger — Policy Maker "My Runs" feature

Plan: docs/superpowers/plans/2026-07-12-policy-maker-my-runs-implementation.md
No git repo in this project — verification is done by direct Read/Grep of
modified files after each task, not git diff.

Task 1: complete (main.py: import json + _read_run_scenario + GET /api/my-runs; smoke_test.py + api_smoke_test.py pass; report at .superpowers/sdd/task-1-report.md)
Task 2: complete (index.html header button + myRunsPage markup + v-bumps; lang.js 7 keys x2; app.js showAdminPanel/goToAdminPage/goToDashboard/goToAuditLogPage updated + goToMyRunsPage/loadMyRuns added; controller-verified via Grep/Read)
Task 3: complete (app.js: downloadPdfForRun added after runSimulation; index.html app.js?v=28; live Playwright end-to-end verified on port 8010 with disposable test account, run-count +1 confirmed, superadmin untouched; smoke tests pass)
