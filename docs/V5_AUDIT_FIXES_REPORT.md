# V5 Audit Fixes Report

**Date:** 2026-06-22
**Context:** four bugs found in the V5 destructive audit (see `docs/V5_DESTRUCTIVE_AUDIT_REPORT.md`). All four are claim-safety / leak-prevention gates. Every change **strengthens** a gate; none removes a check. Tests: **459 → 471 passed** (+12 regressions). No production behavior weakened.

---

## Fix 1 — Certification policy no longer leaks the required status globally
**File:** `certvic/metrics/certification_policy.py`

Before, `evaluate_certification_policy()` mutated the module-level `_REVIEWED_OR_STRONGER` set:
```python
if required not in _REVIEWED_OR_STRONGER:
    _REVIEWED_OR_STRONGER.add(required)        # leaks across calls
if statuses and not (statuses & _REVIEWED_OR_STRONGER):
    ...
```
After, the accepted set is built locally and the global is never mutated:
```python
accepted = _REVIEWED_OR_STRONGER | {required}  # local; no cross-call leak
if statuses and not (statuses & accepted):
    ...
```
**Why stronger:** a custom/permissive `evidence_status_required` can no longer permanently widen the allowlist for later default-policy calls. The custom status is still accepted *within* its own call (verified by a regression test).

---

## Fix 2 — Paper-number guard is fail-closed against em-dashes and placeholders
**File:** `certvic/validation/paper_numbers_guard.py`

1. The whole-line placeholder skip was replaced with **in-place token neutralization**, so a fabricated number that shares a line with `--` / `TBD` / `N/A` (or an em-dash `---`, or a range `10--20`) is still scanned. Placeholder tokens carry no digits, so bare-placeholder lines stay clean.
2. The number regex now also matches **leading-dot decimals** (`.42`):
   `(?<![\w.])(?:\d+(?:\.\d+)?|\.\d+)(?![\w])`

**Why stronger:** the only acceptable failure mode for a fabrication guard is fail-closed. Verified the real placeholder-only `paper/sections/05_results.tex` still passes with **0 violations**.

---

## Fix 3 — Item validity certificate gates on edit detectability
**File:** `certvic/validity/certificate_schema.py`

`detectability_status` added to `BLOCKING_FIELDS`. Now:
- a failing detectability value → blocking reason → not evidence-eligible;
- an **unassessed** (`unknown`) detectability → `incomplete_review_state` warning → not evidence-eligible (conservative: never-assessed = ineligible).

**Why stronger:** a crude/trivially-detectable edit, or one whose detectability was never measured, can no longer be an `evidence_eligible_candidate`. The existing certificate test fixture was updated so its eligible item now declares `detectability_status: pass` (it previously claimed eligibility without any detectability assessment — exactly the gap).

**Known residual (documented, not fixed here):** the detectability *probe* does not yet write a per-item `detectability_status` into task metadata, and `evidence_eligible_candidate` is consumed nowhere downstream. Both are real-run integration steps, tracked as RISK-3 in the audit report.

---

## Fix 4 — Release privacy audit text-scans the release directory
**File:** `certvic/security/release_privacy_audit.py`

`scan_private_paths`/`scan_secrets` skip the generated `release/` tree, so the combined audit previously inspected only **pixels** in `--release-dir`. Now, when `release_dir` is supplied, the audit additionally runs both scans **rooted at the release dir** (so its text files are not skipped) and folds the findings into the pass decision and the markdown report (new `release_private_paths` / `release_secrets` fields).

**Why stronger:** a home-directory absolute path, a private dataset root, or an API-key-like token inside a release config/script/README is now caught by the gate that runs before publishing. Verified no new false positives on the real repo (`audit(".")` still passes).

---

## Regression coverage
`tests/test_v5_destructive_audit_regressions.py` (12 tests) pins each fix:
- policy: no cross-call leak; custom required status still accepted in-call.
- paper guard: em-dash line, placeholder-sharing line, leading-dot decimal, and end-to-end `verify_paper_numbers` block.
- item cert: detectability is blocking; detectable → ineligible; unassessed → ineligible; passes only when detectability passes.
- release: release-dir text leak caught; clean release dir passes.

## Verification after fixes
```
pytest: 471 passed
cvpr_ready_except_results_audit: passed (5/5)
all_commands_smoke: passed (4 unsafe skipped)
claim_language_guard: 0 findings
paper_numbers_guard (real 05_results.tex): 0 violations
release_privacy_audit (real repo): 0 findings
```
