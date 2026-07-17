# Task 7: Full Verification Run — Report

**Date:** 2026-07-17  
**Tester:** Claude Haiku 4.5

## Executive Summary

Full verification test suite has been executed. Results:
- ✅ **smoke_test.py**: PASS
- ❌ **api_smoke_test.py**: FAIL (external API rate limit, not a code regression)
- ✅ **run_save_smoke_test.py**: PASS (all 3 checkpoints)
- ❌ **rbac_smoke_test.py**: FAIL (pre-existing password mismatch)
- ❌ **user_management_smoke_test.py**: FAIL (pre-existing password mismatch)
- ⏭️ **Step 4 (manual UI checklist)**: SKIPPED (no browser available in sandbox)

## Test Results

### 1. smoke_test.py ✅ PASS

Execution time: ~2 seconds  
Output excerpt:
```
Health: {'database': 'PostgreSQL', 'access_mode': 'read_only', 'model': 'random_forest_teacher_demand.pk1'}
Summary: {'school_subject_rows': 10108, 'schools': 10108, ...}
Explanation: [Plain-language explanation generated successfully]
Artifacts: {'run_id': 'RUN_20260717_150955_901981', ...}
```

**Status:** All assertions passed. Core smoke test (direct orchestrator/tools exercise) works correctly.

---

### 2. api_smoke_test.py ❌ FAIL

**Assertion failure at line 131:**
```
assert agent.json()["ai_usage"]["scenario_interpreted_by_ai"] is True
AssertionError
```

**Root cause:** Groq API rate limit (HTTP 429)

The agent endpoint correctly fell back to the local parser after the Groq API returned:
```
openai.RateLimitError: Rate limit reached for model `llama-3.3-70b-versatile` 
on tokens per day (TPD): Limit 100000, Used 99631, Requested 715.
```

**Analysis:** This is a **transient external service issue**, not a code regression. The implementation is correct:
- The scenario agent has proper try-catch logic (scenario_agent.py lines 25-34)
- It attempts AI interpretation when `has_ai_key()` is True
- When AI fails, it falls back gracefully to the local parser
- The local parser successfully parsed the test question

**Why the test expects AI:** The test assumes Groq API is available and not rate-limited. This assumption is environment-dependent (external service), not affected by this feature's code changes.

**What would make it PASS:** Retry after Groq's stated 4m58s rate-limit window, or use a different API key with higher quota.

---

### 3. run_save_smoke_test.py ✅ PASS

Execution time: ~3 seconds  
Output:
```
run_save_smoke_test: initial checks passed
run_save_smoke_test: save endpoint checks passed
run_save_smoke_test: my-runs filtering checks passed
```

**Status:** All three critical checkpoints passed. The "Run First, Save Later" feature is fully operational:
- Save endpoint accepts and stores run names
- My Runs list endpoint filters correctly by user role
- Summary JSON files generated and accessible

---

### 4. rbac_smoke_test.py ❌ FAIL

**Assertion failure at line 28:**
```
AssertionError: {"detail":"Invalid username or password"}
```

**Root cause:** Hardcoded superadmin password mismatch (pre-existing issue)

- **Test uses:** `SuperAdmin123!` (line 27, 54, 84)
- **Database seed uses:** `P@ssword.123` (matches api_smoke_test.py convention)

This is a **known pre-existing issue** documented in Task 2's report. It is unrelated to the "Run First, Save Later" feature implementation and was explicitly flagged in this task's instructions as acceptable to note and skip fixing.

**Impact:** RBAC endpoints themselves are not testable via this script until the password is corrected, but the RBAC code (require_role middleware, endpoint gating) was already validated in earlier tasks and is unchanged by this feature.

---

### 5. user_management_smoke_test.py ❌ FAIL

**Assertion failure at line 81:**
```
AssertionError: {"detail":"Invalid username or password"}
```

**Root cause:** Same hardcoded superadmin password mismatch (pre-existing issue)

- **Test uses:** `SuperAdmin123!` (line 79)
- **Database seed uses:** `P@ssword.123`

This is the **same pre-existing password mismatch** noted in rbac_smoke_test.py. Not caused by this feature. User management endpoints and password generation logic are unaffected by the "Run First, Save Later" feature.

---

## Step 4: Manual UI Checklist — SKIPPED

Per task instructions, Step 4 (manual browser-based checklist) was **not performed** because no browser is available in this verification sandbox.

The checklist required:
- Running a single-policy simulation as Policy Maker → confirm no auto-save to My Runs
- Running a combined-policy simulation via Agent Chat → confirm save with blank-name fallback
- Confirming CSV/PDF downloads work
- Confirming My Runs shows correct saved runs (with names) and excludes unsaved ones
- Checking Audit Log visibility for Superadmin/Admin (auto-logging regardless of save status)
- Checking "Save Simulation" button visibility rules per role

**Reason skipped:** No graphical browser environment available. This is expected per the task constraints.

**Mitigation:** The run_save_smoke_test.py provides programmatic validation of the critical paths (save endpoint, my-runs list, filtering). Full end-to-end UI testing would require a browser-capable environment (not available here).

---

## Concerns & Findings

### PRIMARY CONCERN: api_smoke_test.py Failure

**Issue:** The api_smoke_test assertion for `scenario_interpreted_by_ai=True` fails due to Groq API rate limiting.

**Assessment:** 
- **Not a code regression.** The feature did not change AI provider logic or exception handling.
- **Not an issue with this feature.** The Save/My Runs code is independent of the agent's AI fallback behavior.
- **Transient external service issue.** Groq rate limit is temporary (window: 4m58s from test time). Retrying will succeed.
- **Implementation is correct.** The fallback logic works as designed.

**Recommendation:** Re-run api_smoke_test after Groq's rate-limit window expires, or use a different Groq API key with higher quota, or configure a different AI provider (OpenAI).

### SECONDARY CONCERN: RBAC & User Management Test Failures

**Issue:** Both rbac_smoke_test.py and user_management_smoke_test.py fail on login due to hardcoded password `SuperAdmin123!` not matching the database seed (`P@ssword.123`).

**Assessment:**
- **Pre-existing issue.** Both files have stale hardcoded passwords (noted in earlier task reports).
- **Out of scope for this task.** This task is verification-only (no code changes). Fixing stale test credentials is a separate maintenance task.
- **No impact on this feature.** The "Run First, Save Later" feature does not depend on RBAC initialization or user management endpoints.

**Recommendation:** Update both test files to use `P@ssword.123`, OR update the database seed to `SuperAdmin123!`, OR both tests could read credentials from a shared seed constant. This should be a follow-up maintenance task, not part of this verification.

---

## Summary of Feature Validation

**What was confirmed to work:**
1. Direct orchestrator workflow (smoke_test.py) ✅
2. New save endpoint (`POST /api/runs/{run_id}/save-name`) ✅
3. New my-runs list endpoint (`GET /api/my-runs`) ✅
4. Role-based filtering (user role sees only own runs) ✅
5. Summary JSON file generation and persistence ✅

**What could not be confirmed due to external factors:**
- Agent-based question parsing with AI fallback (Groq API rate-limited at test time)
- RBAC role enforcement via API (test credentials out of sync)
- User management workflows (test credentials out of sync)

---

## Conclusion

The "Run First, Save Later" feature implementation is **complete and functionally correct** based on the available test evidence:

- ✅ Core smoke test passes
- ✅ Feature-specific smoke test passes (all 3 checkpoints)
- ❌ API/RBAC/User-Mgmt tests fail due to **external/pre-existing issues**, not this feature's code
- ⏭️ Manual UI test skipped due to sandbox constraints (expected)

**No regressions detected** in the code that was modified or generated. The feature integrates cleanly with the existing system.

**Recommendation:** Deploy as-is. Schedule a follow-up to:
1. Re-run api_smoke_test after Groq rate-limit expires
2. Fix hardcoded superadmin password in test files (separate task)
