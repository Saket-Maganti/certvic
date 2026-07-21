# V3 Prompt 17 — Failure Mode Playbooks Report

## Goal

Create operational playbooks for what to do when real runs fail, plus an
automatic symptom→playbook diagnosis.

## What was built

- `docs/playbooks/` — README index + 11 playbooks: edit realism, no certified gap, high parse failure, high control flip, low human agreement, Kaggle/Colab session failure, label-policy failure, claim-gate failure, low original accuracy, too few candidates, GPU/preflight failure. Each is an actionable checklist that refuses to fabricate results.
- `certvic/playbooks/diagnose_failure.py` — reads whatever report artifacts exist in a report dir and maps observed symptoms (low quality pass, high detectability, high parse failure, high control flip, no certified gap, low original accuracy, low human agreement, too few candidates, GPU preflight failure) to the matching playbook; markdown report.

## Tests

`tests/test_v3_failure_playbooks.py` — 11 tests: all playbook docs exist; no-report state; healthy report → no symptoms; detection of low quality pass, high detectability, high parse failure, control flip + low accuracy, GPU preflight failure, no-certified-gap (with summary present); report lists all playbooks; no heavy imports.

## Verification

- `python3 -m pytest -q` — full suite green (418 passed; was 407).
- CLI smoke: on `data/results/smoke_report` and a summary fixture, correctly diagnosed `no_certified_gap` (the expected state pre-evidence) and pointed to `docs/playbooks/NO_CERTIFIED_GAP.md`.

## Evidence / cost discipline

Read-only diagnosis: no inference, no downloads, no paid services, no evidence
claims (`evidence_claims_made=false`). Every playbook explicitly says: when the
honest outcome is a null result or ineligible claim, report it — do not fabricate.
No heavy imports.

## Status

**PASSED.**

## Remaining blockers

None. Diagnosis fills in as real run artifacts appear; this prevents panic during
real runs.
