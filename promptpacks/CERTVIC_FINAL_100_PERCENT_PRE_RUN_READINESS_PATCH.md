# CERTVIC — FINAL 100% PRE-RUN READINESS PATCH

## Purpose

This is the final implementation contract before real Kaggle execution.

Do not perform another broad audit. Do not create another parallel infrastructure layer. Do not declare readiness from isolated tests. Repair the remaining 00C2, strict-smoke, authorization, prompt-binding, and packaging defects, prove the notebook-derived path end to end, and leave CertVIC ready for real 00A, 00B, and 00C2 execution.

The only acceptable success status is:

```text
CVPR_PRE_EXECUTION_READY
LOCAL_PRE_RUN_READINESS_10_OF_10
```

Use it only when every local criterion in this prompt passes. Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and name the exact blocker.

---

## Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Treat the live checkout as authoritative. Preserve historical provider outputs, image pairs, evidence ledgers, gate ledgers, review originals, canonical manifests, and user-owned files. Do not initialize Git when absent. Do not commit or push unless explicitly requested.

---

## Frozen scientific boundaries

Do not change:

- Qwen2.5-VL-7B V1: `12/94 = 0.1277`.
- InternVL2-8B V1: `1/94 = 0.0106`.
- LLaVA-OneVision-7B V1: `3/94 = 0.0319`.
- Frozen V1 threshold: `observed_spurious_flip_rate <= 0.10`.
- Qwen fails V1.
- V2-30 remains retrospective sensitivity evidence.
- Confirmatory remains prospective and zero-overlap with V1.
- Main remains blocked until confirmatory and human-review gates pass.
- No real COCO evidence exists.
- `paper_evidence=false`.
- Genuine `human_reviewed=true` count remains zero until real review exists.
- No prompts, thresholds, items, expected answers, or model revisions may be tuned after real outcomes are observed.

---

# Confirmed final defects

## 1. 00C2 canonical ZIP creation is broken

`runtime_class` is now:

```text
REAL_MODEL_SMOKE
```

but `package_run.py` may include `snapshot_manifest.json` only for an older runtime label or strict synthetic fixtures. The actual failure chain is:

```text
worker succeeds
package_run succeeds
snapshot_manifest.json is omitted
canonical smoke ZIP creation fails
```

## 2. Canonical smoke validation ignores runtime failures

The strict canonical branch must reject:

- `cleanup_status != PASS`;
- any OOM event;
- unresolved warnings;
- failed model release;
- failed CUDA cleanup;
- incomplete teardown.

## 3. Trusted run-contract identity is not enforced

One exact `run_contract_hash` must match across:

- trusted smoke contract;
- runtime manifest;
- every prediction row;
- authorization proof;
- validation report;
- package metadata.

## 4. Scientific notebooks do not verify the parent matrix authorization before model loading

The provider child permission must be checked against its parent matrix authorization before any hardware inspection, CUDA call, adapter import, model loading, or output-directory creation.

## 5. Prompt hash is not permission-bound

The active prompt template hash must be frozen into the matrix authorization, provider permission, runtime config, run contract, rows, package metadata, importer, and analysis provenance.

## 6. Packaging lifecycle is not retry-safe

The provider permission may transition to `OUTPUT_PACKAGED` before the final ZIP is fully written and atomically promoted. A ZIP failure can strand the permission.

---

# Primary mission

By the end of this task:

1. 00C2 produces a complete canonical ZIP.
2. `snapshot_manifest.json` is included for `REAL_MODEL_SMOKE`.
3. Canonical smoke validation rejects cleanup failure, OOM, and unresolved warnings.
4. Trusted `run_contract_hash` matches everywhere.
5. Parent matrix authorization is verified before model loading.
6. Prompt hash is bound through the full chain.
7. Packaging state transitions only after successful final ZIP creation.
8. Packaging failure is safely retryable.
9. A notebook-derived synthetic 00C2 route passes for all three providers.
10. Tampered variants fail.
11. All 16 notebooks remain valid.
12. The release works from clean extraction.
13. The next real action is running 00A, 00B, and 00C2.

---

# Restrictions

Do not run real VLM inference, real confirmatory/Main/COCO inference, real human review, large downloads, or paid APIs. Synthetic non-evidence fixtures are allowed.

Do not fabricate predictions, labels, metrics, model commits, runtimes, or paper results.

Do not rely on manual file renaming, JSON editing, hash copying, permission resets, or ZIP surgery.

---

# Phase 0 — Baseline

Run and record:

- full pytest;
- latest readiness tests;
- notebook validation;
- package-run tests;
- smoke artifact tests;
- smoke-gate tests;
- execution-gate tests;
- provider-permission tests;
- importer tests;
- claim guard;
- privacy guard;
- paper compile;
- clean release extraction;
- deterministic release rebuild.

Create:

```text
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_SESSION.md
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_DEFECTS.csv
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_CHANGELOG.csv
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_COMMANDS.csv
```

---

# Phase 1 — Fix REAL_MODEL_SMOKE packaging

Update:

```text
certvic/cvpr/package_run.py
```

Whenever:

```text
runtime_class == REAL_MODEL_SMOKE
```

require and copy:

```text
snapshot_manifest.json
```

into the staged package.

Fail closed when the snapshot manifest is missing, unreadable, inconsistent, or hash-mismatched.

The final 00C2 ZIP must contain the canonical contract members required by the current smoke artifact schema, including at minimum:

```text
predictions.jsonl
runtime_manifest.json
environment_manifest.json
snapshot_manifest.json
task_bundle_manifest.json
validation_report.json
hash_manifest.json
authorization_proof.json
provider_permission.json
permission_events.jsonl
```

If the canonical contract intentionally defines a different exact member count, update the artifact builder, gate, documentation, and tests together.

Add an integration regression proving:

```text
worker
→ package_run
→ canonical smoke packaging
→ final ZIP exists
```

---

# Phase 2 — Harden strict smoke runtime validation

Update:

```text
certvic/cvpr/smoke_gate.py
```

Reject unless:

```text
cleanup_status == PASS
oom_events == 0
unresolved_warnings == []
model_release_status == PASS
cuda_cleanup_status in {PASS, NOT_APPLICABLE}
```

Use documented aliases only.

Create an allowlist for genuinely non-blocking warnings. All other warnings fail.

Retain existing peak-VRAM checks.

Add negative tests for:

- cleanup failure;
- one OOM event;
- unresolved warning;
- missing cleanup status;
- failed model release;
- failed CUDA cleanup.

Each must fail the strict gate.

---

# Phase 3 — Enforce trusted run-contract identity

The trusted smoke contract must define one provider-specific:

```text
run_contract_hash
```

Require exact equality in:

- trusted smoke contract;
- runtime manifest;
- every prediction row;
- authorization proof;
- validation report;
- provider permission where applicable.

Missing values fail closed.

Tamper tests must independently alter:

- runtime hash;
- one row hash;
- proof hash;
- validation hash;
- trusted contract hash.

Every mismatch must fail.

Derive the hash once from the frozen run contract. Do not let notebooks independently construct a semantically different version.

---

# Phase 4 — Verify parent matrix authorization in notebook preflight

Update:

```text
certvic/cvpr/notebook_builder.py
certvic/cvpr/notebook_permission_binding.py
certvic/cvpr/reconcile_provider_permissions.py
```

Add required notebook input:

```text
MATRIX_AUTHORIZATION
```

Before any model or hardware action:

1. verify matrix authorization;
2. verify provider child permission;
3. verify child-parent linkage;
4. verify current runtime inputs;
5. claim provider permission;
6. continue.

Verify:

- matrix authorization ID;
- study;
- provider membership;
- code hash;
- environment hash;
- task bundle hash;
- final task hash;
- review hash;
- detectability hash;
- model registry hash;
- schema;
- prompt hash;
- expiry.

A mismatch must fail before:

- `torch.cuda`;
- hardware inspection;
- adapter import;
- model loading;
- output-directory creation.

Add a negative test where a valid child permission is paired with a different parent matrix.

---

# Phase 5 — Bind prompt template hash

Use one canonical field:

```text
prompt_template_hash
```

Bind it into:

- matrix authorization;
- provider child permission;
- notebook active binding;
- runtime config;
- run contract;
- prediction rows;
- package validation;
- authorization proof;
- importer;
- analysis provenance.

The notebook must derive the hash from the exact prompt template it passes to the worker. Do not accept an unrelated manually typed value.

Scientific authorization must prove smoke prompt identity equals the authorized scientific prompt identity unless the prospective protocol explicitly freezes separate prompts and records both.

Change one character in the prompt after permission issuance; preflight must fail.

---

# Phase 6 — Retry-safe packaging lifecycle

Update:

```text
certvic/cvpr/package_run.py
certvic/cvpr/permission_ledger.py
certvic/cvpr/reconcile_provider_permissions.py
```

Use a lifecycle such as:

```text
RUN_STARTED
PACKAGING_STARTED
PACKAGE_WRITTEN
OUTPUT_PACKAGED
```

Write the archive to a temporary path. Then:

1. validate the archive;
2. fsync where practical;
3. atomically rename it to the final path;
4. only then transition to `OUTPUT_PACKAGED`.

On failure, use `PACKAGING_FAILED` or retain another explicitly retryable state.

A retry is allowed only when:

- the final ZIP does not exist;
- the prior package attempt failed;
- runtime outputs remain valid;
- the provider nonce has not been consumed.

If an already-valid final ZIP exists and hashes match, rerunning packaging returns a safe no-op.

Add tests for:

- ZIP write failure;
- archive validation failure;
- atomic rename failure;
- interruption after temporary ZIP creation;
- successful retry;
- idempotent rerun.

---

# Phase 7 — Notebook-derived synthetic 00C2 proof

Create one authoritative integration route that executes the generated 00C2 notebook logic rather than calling modules in a different order.

For each provider:

- Qwen;
- InternVL;
- LLaVA;

generate the real 00C2 notebook and execute it with a mock adapter while preserving the real:

- configuration cells;
- portable bundle propagation;
- parent authorization verification;
- child permission verification;
- prompt binding;
- worker invocation;
- package-run invocation;
- canonical smoke-artifact packaging;
- strict smoke gate.

Produce:

```text
00C2_<provider>_synthetic_notebook_proof.zip
```

and a strict synthetic PASS.

Then tamper with:

- snapshot manifest;
- run-contract hash;
- prompt hash;
- cleanup status;
- OOM count;
- warning list;
- parent authorization;
- provider permission.

Every tampered artifact must fail.

---

# Phase 8 — Upgrade smoke-gate diagnostics

For each failure report:

- provider;
- file;
- field;
- expected value;
- observed value;
- stable error code;
- remediation.

Use stable error codes such as:

```text
SMOKE_SNAPSHOT_MISMATCH
SMOKE_RUN_CONTRACT_MISMATCH
SMOKE_PROMPT_MISMATCH
SMOKE_CLEANUP_FAILED
SMOKE_OOM_DETECTED
SMOKE_WARNING_UNRESOLVED
SMOKE_PARENT_AUTHORIZATION_MISMATCH
```

Do not expose private paths or secrets.

---

# Phase 9 — Update notebooks

Repair:

```text
00A
00B
00C2
02
03
04
11
12
13
21
22
23
```

Every scientific notebook must:

- attach `MATRIX_AUTHORIZATION`;
- derive prompt hash from the active prompt;
- verify parent and child permissions;
- verify current runtime bindings;
- fail before model loading;
- use retry-safe packaging;
- emit canonical artifacts;
- print the exact local handoff command.

00C2 must:

- include `snapshot_manifest.json`;
- use correct shard semantics;
- emit the canonical ZIP;
- pass the strict gate without manual edits.

---

# Phase 10 — Update release and execution plan

Update:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_READY_TO_RUN_HANDOFF.md
```

The real route must be exactly:

1. attach wheelhouse;
2. attach snapshots;
3. run 00A;
4. run 00B per provider;
5. run 00C2 per provider;
6. download canonical artifacts;
7. run one local smoke-handoff command;
8. receive a strict gate decision;
9. proceed only when all providers pass.

No renaming or JSON editing.

---

# Potential final upgrades

Implement only when they directly improve safety:

## Notebook preflight report

Write one report binding:

- matrix authorization;
- child permission;
- prompt hash;
- task bundle;
- environment;
- snapshot;
- code;
- run contract;
- provider;
- expiry.

## Packaging recovery report

On retry, explain exactly why retry is allowed.

## Smoke provenance capsule

Create one compact artifact binding:

- 00A;
- 00B;
- 00C2;
- matrix authorization;
- child permission;
- run contract;
- prompt hash.

## Real-run configuration generator

Generate ready-to-paste notebook configuration blocks from trusted local inputs.

## No-hidden-step audit

Add one test that follows only the documented commands in the execution master plan.

---

# Required deliverables

Create or update:

```text
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_SESSION.md
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_DEFECTS.csv
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_CHANGELOG.csv
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_COMMANDS.csv
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_VALIDATION.md
reports/cvpr_final_runtime_patch/CERTVIC_FINAL_RUNTIME_PATCH_SCORECARD.md
reports/cvpr_final_runtime_patch/CERTVIC_100_PERCENT_READY_HANDOFF.md

docs/execution/CERTVIC_00C2_CANONICAL_PACKAGE_GUIDE.md
docs/execution/CERTVIC_STRICT_SMOKE_INTEGRITY_GUIDE.md
docs/execution/CERTVIC_PARENT_CHILD_AUTHORIZATION_GUIDE.md
docs/execution/CERTVIC_RETRY_SAFE_PACKAGING_GUIDE.md

CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# Final validation

Run:

- focused final-runtime tests;
- full test suite;
- Ruff;
- compileall;
- type checks where configured;
- REAL_MODEL_SMOKE snapshot-copy test;
- cleanup-failure tests;
- OOM and warning rejection tests;
- run-contract tamper tests;
- parent-authorization mismatch tests;
- prompt-hash tamper tests;
- retry-safe packaging tests;
- notebook-derived synthetic 00C2 tests for all three providers;
- notebook static tests;
- notebook synthetic-runtime tests;
- claim guard;
- privacy guard;
- paper compile;
- clean release extraction;
- deterministic release rebuild;
- `git diff --check` when applicable.

Verify explicitly:

```text
paper_evidence=false
human_reviewed=true count = 0 unless genuine review exists
Main execution_allowed=false
COCO execution_allowed=false
V2-30 remains retrospective
no real GPU evidence created
no human labels fabricated

REAL_MODEL_SMOKE package includes snapshot_manifest.json
canonical smoke rejects cleanup failure
canonical smoke rejects OOM events
canonical smoke rejects unresolved warnings
trusted run_contract_hash matches runtime, rows, proof, and validation
scientific notebook verifies parent matrix authorization before model loading
prompt_template_hash is bound through the complete chain
OUTPUT_PACKAGED occurs only after final ZIP success
failed packaging is safely retryable
notebook-derived synthetic 00C2 succeeds for all providers
release works from clean extraction
```

---

# Final status rule

Report:

```text
CVPR_PRE_EXECUTION_READY
LOCAL_PRE_RUN_READINESS_10_OF_10
```

only when every validation above passes.

Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and list the exact remaining defect.

Do not report 99% or 9.8/10 when 00C2 still fails.

---

# Required final response

Use this structure:

## 1. Executive verdict

## 2. Final defects repaired

For each include:

- path;
- original defect;
- repair;
- test;
- result.

## 3. 00C2 canonical package

## 4. Strict smoke runtime integrity

## 5. Run-contract binding

## 6. Parent-child authorization

## 7. Prompt-hash binding

## 8. Retry-safe packaging

## 9. Notebook-derived 00C2 proof

## 10. Notebook readiness

## 11. Release self-containment

## 12. Validation results

Give exact commands, exit codes, and test totals.

## 13. Remaining external blockers

Only list:

- wheelhouse bytes;
- model snapshots;
- source datasets;
- real Kaggle runs;
- real human review;
- real model evidence.

## 14. Exact next sequence

The next action must be:

1. attach wheelhouse;
2. attach snapshots;
3. run 00A;
4. run 00B;
5. run 00C2;
6. return canonical artifacts.

## 15. Readiness verdict

Report separately:

```text
Local pre-run readiness: 10/10 or not
Real evidence readiness: honest current level
```

## 16. Files created or modified

## 17. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_final_runtime_patch/CERTVIC_100_PERCENT_READY_HANDOFF.md
```

---

# Success standard

This is the final patch.

After this pass, the repository must be directly ready for real 00A, 00B, and 00C2 execution.

A successful handoff means the user can:

1. attach the required external assets;
2. run the notebooks unchanged except for documented paths;
3. download canonical artifacts;
4. run the strict smoke handoff;
5. receive a trustworthy PASS or FAIL;
6. proceed to scientific authorization without another code patch.

**Fix the final 00C2, smoke-integrity, authorization, prompt-binding, and packaging defects completely, prove the exact notebook-derived route, and leave CertVIC at genuine 100% local pre-run readiness.**
