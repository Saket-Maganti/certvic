# CERTVIC — 10/10 PRE-RUN READINESS: FINAL REAL-KAGGLE HANDOFF, MULTI-SESSION AUTHORIZATION, AND ATOMIC EXECUTION PATCH

## Role

You are operating as the lead research engineer, Kaggle runtime engineer, VLM deployment engineer, benchmark architect, permission/provenance systems engineer, statistician, reproducibility engineer, release engineer, and critical CVPR co-author for **CertVIC**.

This is the **final patch before real execution**.

Do not perform another broad audit.

Do not create another architecture layer.

Do not add another optimistic status report without proving the actual runtime path.

Do not stop at synthetic-local success.

Your job is to close the final real-Kaggle handoff defects and leave CertVIC at genuine:

```text
10/10 PRE-RUN READINESS
```

For this project, `10/10 PRE-RUN READINESS` means:

- every local implementation path is complete;
- all 00A/00B/00C2 notebooks can be run exactly as documented;
- returned smoke artifacts can be consumed without manual renaming or editing;
- three separate Kaggle provider sessions can be reconciled offline;
- scientific notebooks bind their active inputs before GPU/model loading;
- permissions cannot be replayed;
- detectability is bound to exact frozen task bytes;
- import plus permission consumption is transactionally recoverable;
- Main has enough candidate oversampling to survive realistic rejection;
- all synthetic and local integration tests pass;
- and the only remaining blockers are real external assets and real execution.

If any local defect remains, the final verdict must be:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

Do not claim 10/10 readiness from unit tests alone.

---

# 1. Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Treat the live checkout as authoritative.

Preserve:

- historical provider outputs;
- original image pairs;
- canonical manifests;
- human-review originals;
- evidence ledgers;
- gate ledgers;
- raw return archives;
- user-owned files;
- and all frozen scientific boundaries.

Do not initialize Git when absent.

Do not commit or push unless explicitly requested.

---

# 2. Frozen scientific boundaries

The following must not change unless direct repository evidence proves otherwise:

- Qwen2.5-VL-7B has `12/94 = 0.1277` V1 irrelevant-edit flips.
- InternVL2-8B has `1/94 = 0.0106`.
- LLaVA-OneVision-7B has `3/94 = 0.0319`.
- The frozen V1 rule remains:

```text
observed_spurious_flip_rate <= 0.10
```

- Qwen fails the frozen V1 rule.
- V2-30 remains retrospective sensitivity evidence only.
- The independent confirmatory study remains prospective and zero-overlap with V1.
- Main remains blocked until confirmatory and human-review gates pass.
- No real COCO evidence exists.
- `paper_evidence=false`.
- `human_reviewed=true` count remains zero until genuine reviewers complete the protocol.
- No thresholds, prompts, items, expected answers, or revisions may be tuned after observing real outcomes.

---

# 3. Final confirmed defects to close

Verify each in the live checkout and repair every confirmed issue.

## 3.1 00C2 drops portable task-bundle information

The notebook verifies the portable bundle but may omit:

```text
task_bundle_root
task_bundle_manifest
```

from the runtime configuration passed to the worker.

The worker must receive and verify the same bundle root and manifest used during preflight.

## 3.2 00C2 T4×2 shard-count mismatch

The real-model smoke currently may run:

```text
--shard 0
--num-shards 1
```

while packaging expects two shards when two GPUs are visible.

Global smoke semantics must be exact.

A two-item smoke may use either:

- one logical shard intentionally; or
- two one-item shards concurrently.

The runtime and packager must agree exactly.

## 3.3 00A/00B/00C2 artifact names do not match the smoke gate

The real notebooks and the strict smoke gate must use one canonical artifact contract.

No manual renaming, copying, or editing may be required.

## 3.4 Permission verification is not derived from active notebook variables

`PERMISSION_INPUT_PATHS` or equivalent must not be a separately hand-maintained dictionary that can diverge from the files actually used by the notebook.

The permission input map must be constructed directly from active runtime variables.

## 3.5 The permission ledger does not support separate Kaggle sessions

Qwen, InternVL, and LLaVA will likely run in separate Kaggle sessions with separate writable `/kaggle/working` directories.

A shared mutable local ledger cannot be assumed.

## 3.6 Returned provider ZIPs do not carry enough authorization state

The local importer must be able to verify each provider’s permission claim and output-packaged transition using only:

- the immutable base authorization;
- the returned provider ZIP;
- and trusted local inputs.

## 3.7 Smoke and scientific environment/snapshot contracts are not semantically joined

A real smoke using snapshot/environment A must not authorize scientific execution using snapshot/environment B.

## 3.8 Synthetic smoke can satisfy real scientific authorization

Synthetic smoke must never authorize a non-synthetic run.

## 3.9 Detectability PASS is not bound to exact frozen task bytes

The detectability gate must bind:

- final task manifest hash;
- bundle hash;
- task hashes;
- source image hashes;
- edited image hashes;
- control family;
- placements;
- and config hash.

Task IDs alone are insufficient.

## 3.10 Import promotion and permission consumption are not one recoverable transaction

A failure after canonical promotion but before permission consumption can leave inconsistent state.

## 3.11 Main has no rejection buffer

Current candidate targets may equal final primary plus reserve totals exactly, leaving no room for:

- generation failure;
- QA rejection;
- licensing failure;
- reviewer exclusion;
- stratum shortage;
- or source-cap constraints.

## 3.12 Real smoke and scientific-run return workflow is not one-click

The user should not need to infer filenames, edit JSON, merge ledgers manually, or reconstruct missing hashes.

---

# 4. Primary mission

By the end of this task:

1. 00A, 00B, and 00C2 must emit canonical artifacts consumed directly by the smoke gate.
2. 00C2 must pass portable bundle information into the worker.
3. 00C2 shard execution and packaging must agree under T4×2 and single-GPU fallback.
4. Scientific notebooks must derive permission bindings from active runtime variables.
5. Multi-session provider authorization must work offline.
6. Each returned provider ZIP must include a verifiable authorization proof.
7. Smoke and scientific snapshot/environment identities must match exactly.
8. Synthetic smoke must be cryptographically and semantically barred from real authorization.
9. Detectability PASS must bind exact frozen task bytes.
10. Import and permission consumption must use a recoverable two-phase transaction.
11. Main candidate construction must oversample by family and stratum.
12. The entire real handoff must be validated with a Kaggle-session simulator.
13. The release must include all new tooling and pass clean extraction.
14. The next real action must be running 00A/00B/00C2, not another repair pass.

---

# 5. Restrictions

## 5.1 No real model or scientific execution

Do not run:

- real VLM inference;
- real confirmatory inference;
- real Main inference;
- real COCO inference;
- real human review;
- large model downloads;
- large dataset downloads;
- paid APIs.

Synthetic non-evidence fixtures are allowed.

## 5.2 No fabricated evidence

Do not fabricate:

- predictions;
- human labels;
- measured runtimes;
- model commits;
- scientific metrics;
- or paper results.

## 5.3 No manual hidden fixes

The real workflow must not depend on undocumented:

- file renaming;
- JSON editing;
- hash copying;
- path patching;
- or ledger merging.

---

# PHASE 0 — Baseline reproduction

Run and record:

- full test suite;
- latest run-readiness tests;
- notebook tests;
- smoke tests;
- permission tests;
- importer tests;
- release tests;
- claim guard;
- privacy guard;
- paper compile;
- clean extraction;
- deterministic rebuild.

Create:

```text
reports/cvpr_10of10_readiness/CERTVIC_10OF10_SESSION.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_DEFECTS.csv
reports/cvpr_10of10_readiness/CERTVIC_10OF10_CHANGELOG.csv
reports/cvpr_10of10_readiness/CERTVIC_10OF10_COMMANDS.csv
```

---

# PHASE 1 — Canonical real-smoke artifact contract

Create:

```text
certvic/cvpr/smoke_artifacts.py
```

## 1.1 Canonical outputs

00A must emit exactly:

```text
00A_environment.json
00A_environment_validation.json
00A_environment_bundle.zip
```

00B must emit exactly:

```text
00B_<provider>_snapshot.json
00B_<provider>_snapshot_validation.json
00B_<provider>_snapshot_bundle.zip
```

00C2 must emit exactly:

```text
00C2_<provider>_real_model_smoke.zip
```

The smoke ZIP must contain canonical internal filenames:

```text
predictions.jsonl
runtime_manifest.json
environment_manifest.json
snapshot_manifest.json
task_bundle_manifest.json
validation_report.json
hash_manifest.json
authorization_proof.json
```

## 1.2 No manual transformations

The strict smoke gate must consume the notebook outputs directly.

## 1.3 Artifact schema

Version the artifact contract:

```text
certvic.cvpr.smoke_artifact.v1
```

## 1.4 Tests

Prove a notebook-produced synthetic artifact passes the gate without renaming.

---

# PHASE 2 — Fix 00C2 portable bundle propagation

## 2.1 Runtime config

Pass:

```text
task_bundle_root
task_bundle_manifest
task_bundle_hash
```

into the worker runtime config.

## 2.2 Worker verification

Before reading any image:

- verify bundle manifest;
- verify bundle hash;
- resolve logical relative paths;
- verify file bytes;
- verify task hashes.

## 2.3 Same bundle in preflight and worker

Record the exact same bundle hash in:

- preflight;
- runtime config;
- worker manifest;
- output rows;
- smoke ZIP;
- smoke gate.

## 2.4 Tests

Create a portable bundle under one root, copy it to another root, and prove 00C2 mock runtime succeeds unchanged.

---

# PHASE 3 — Fix smoke sharding semantics

Choose one explicit design.

## Option A — One logical smoke shard

For exactly two smoke items:

```text
num_shards=1
expected_shards=1
```

even when two GPUs are present.

This is acceptable because the smoke tests model compatibility, not throughput.

## Option B — Two concurrent one-item shards

Use:

```text
num_shards=2
expected_shards=2
```

and launch both GPUs concurrently.

Whichever design is selected:

- runtime;
- assignment manifest;
- packager;
- validation report;
- and documentation

must agree exactly.

Add T4×2 and single-GPU tests.

---

# PHASE 4 — Derive permission binding from active runtime variables

Create one canonical helper:

```text
certvic/cvpr/notebook_permission_binding.py
```

## 4.1 Build the map automatically

The notebook must derive permission inputs from:

```text
TASK_BUNDLE_MANIFEST
FINAL_TASK_FREEZE
FINAL_REVIEW_LEDGER
SMOKE_GATE_JSON
ENVIRONMENT_LOCK
MODEL_REGISTRY
SNAPSHOT_MANIFEST
CODE_BUNDLE
STUDY_CONFIG
SCHEMA_VERSION
PROVIDER
RUN_TAG
```

## 4.2 No user-supplied duplicate map

Remove or deprecate manually populated `PERMISSION_INPUT_PATHS`.

## 4.3 Exact equality

Verify that the paths used for permission verification are the same values later passed to the worker.

## 4.4 Pre-model fail-fast

Any mismatch must fail before:

- adapter creation;
- model loading;
- CUDA initialization;
- or output directory creation.

---

# PHASE 5 — Replace the shared mutable ledger with provider-specific offline authorization

Use a provider-specific permission design.

## 5.1 Base matrix authorization

Create one immutable matrix authorization artifact containing:

- study;
- task bundle hash;
- review hash;
- detectability hash;
- environment hash;
- model registry hash;
- provider list;
- code hash;
- schema;
- expiry;
- matrix authorization ID.

## 5.2 Provider-specific child permissions

Derive one child permission per provider:

```text
qwen_permission.json
internvl_permission.json
llava_permission.json
```

Each child permission binds:

- parent matrix authorization ID;
- provider;
- model ID;
- revision;
- snapshot hash;
- environment hash;
- task bundle hash;
- run tag;
- one-run nonce;
- expiry;
- code hash.

## 5.3 Local provider ledger

Each Kaggle notebook receives only its provider permission.

It maintains its own provider-local state:

```text
ISSUED
CLAIMED
RUN_STARTED
OUTPUT_PACKAGED
CONSUMED
```

## 5.4 Returned authorization proof

Each provider ZIP must include:

```text
authorization_proof.json
permission_events.jsonl
provider_permission.json
```

## 5.5 Local reconciliation

Create:

```text
certvic/cvpr/reconcile_provider_permissions.py
```

It must verify three independent provider proofs against the parent matrix authorization.

No shared mutable Kaggle state is required.

## 5.6 Replay prevention

The local canonical import ledger records each provider nonce as consumed.

A repeated ZIP or repeated nonce fails.

---

# PHASE 6 — Bind smoke identity to scientific authorization

## 6.1 Smoke artifact fields

For each provider, the real smoke gate must record:

- provider;
- model ID;
- model revision;
- snapshot manifest hash;
- snapshot root hash;
- environment manifest hash;
- code hash;
- processor/model contract;
- parser version;
- prompt hash;
- task bundle hash;
- smoke fixture hash.

## 6.2 Authorization equality checks

Before issuing provider permission, require exact equality between:

```text
smoke.model_revision
current.model_revision

smoke.snapshot_hash
current.snapshot_hash

smoke.environment_hash
current.environment_hash

smoke.code_hash
current.code_hash

smoke.parser_version
current.parser_version
```

## 6.3 No mere co-hashing

Hashing two unrelated files is not enough.

Validate their semantic equality.

---

# PHASE 7 — Forbid synthetic smoke from real execution

## 7.1 Runtime class

Use:

```text
SYNTHETIC_SMOKE
REAL_MODEL_SMOKE
SCIENTIFIC_RUN
```

## 7.2 Authorization rule

For `SCIENTIFIC_RUN`, require:

```text
REAL_MODEL_SMOKE_PASSED
synthetic_fixture=false
```

Reject:

```text
SYNTHETIC_SMOKE_PASSED
```

under all real authorization paths.

## 7.3 Negative tests

Prove synthetic smoke cannot authorize:

- confirmatory;
- Main;
- or COCO runs.

---

# PHASE 8 — Bind detectability to exact task bytes

Update:

```text
certvic/cvpr/detectability_gate.py
```

## 8.1 Required hashes

The gate must bind:

- final task manifest SHA-256;
- task bundle manifest SHA-256;
- bundle content hash;
- every task hash;
- source image hashes;
- edited image hashes;
- placement geometry;
- control family;
- study config hash;
- QA manifest hash.

## 8.2 Gate hash

Create and verify a canonical `gate_hash`.

## 8.3 Authorization check

Execution authorization must verify:

- detectability gate hash;
- exact task bundle hash;
- exact final task manifest hash;
- exact task universe;
- exact edited image hashes.

## 8.4 No missing universe fields

A missing task/bundle hash must fail closed.

---

# PHASE 9 — Transactional import and permission consumption

Implement a two-phase commit.

Create or update:

```text
certvic/cvpr/import_transaction.py
```

## 9.1 States

Use:

```text
STAGED
VALIDATED
PREPARED
PROMOTED
LEDGER_COMMITTED
COMMITTED
ROLLED_BACK
RECOVERY_REQUIRED
```

## 9.2 Transaction journal

Record:

- transaction ID;
- study;
- provider ZIP hashes;
- provider nonces;
- staged paths;
- destination path;
- permission states;
- intended transitions;
- timestamps;
- checksums.

## 9.3 Prepare phase

Before canonical promotion:

- validate all ZIPs;
- verify all provider proofs;
- reserve all provider nonces;
- verify destination state;
- write recovery journal.

## 9.4 Commit phase

Perform:

1. atomic destination promotion;
2. atomic consumed-nonce ledger update;
3. evidence-ledger update;
4. gate-ledger update;
5. journal commit.

## 9.5 Recovery

If failure occurs after promotion:

- detect journal on retry;
- complete or rollback deterministically;
- never strand one provider consumed while others remain output-packaged.

## 9.6 Idempotency

Re-running the same successful import must return a safe no-op.

---

# PHASE 10 — Main candidate oversampling

Update:

```text
configs/studies/main_study_cvpr.yaml
```

## 10.1 Oversampling policy

Generate at least:

```text
1.5× final requirement
```

and preferably:

```text
2×
```

for difficult families or strata.

Example planning target:

```text
final primary: 500
final reserve: 125
minimum candidates before QA/review: 950–1,250
```

## 10.2 Per-family buffer

Freeze separate oversampling ratios for:

- removal;
- insertion;
- attribute;
- difficult size/position strata;
- licensed insertion assets;
- low-frequency categories.

## 10.3 Shortage reporting

Produce projected post-QA and post-review availability.

## 10.4 No weakened final design

Oversampling must not change the frozen final quotas.

---

# PHASE 11 — One-click real smoke return workflow

Create:

```text
certvic/cvpr/smoke_handoff.py
```

## 11.1 User inputs

Accept:

- 00A artifact;
- three 00B artifacts;
- three 00C2 ZIPs;
- trusted smoke contract;
- model registry;
- environment lock.

## 11.2 Output

Produce:

```text
REAL_MODEL_SMOKE_GATE.json
REAL_MODEL_SMOKE_GATE.csv
SMOKE_HANDOFF_REPORT.md
```

## 11.3 No manual editing

The command must discover and validate canonical filenames.

## 11.4 Exact next command

Print the authorization command only when all three providers PASS.

---

# PHASE 12 — Kaggle-session simulator

Create a local simulator that models separate Kaggle sessions.

## 12.1 Simulate three isolated work directories

Each provider receives:

- read-only input bundle;
- writable isolated working directory;
- provider-specific permission;
- no shared mutable state.

## 12.2 Return three ZIPs

Each ZIP must include its provider authorization proof.

## 12.3 Local reconciliation

Run:

- provider-proof reconciliation;
- atomic import;
- permission nonce consumption;
- replay rejection.

## 12.4 Failure cases

Test:

- one provider missing;
- duplicated provider ZIP;
- reused nonce;
- wrong parent matrix permission;
- stale snapshot;
- wrong environment;
- post-promotion ledger failure;
- retry recovery.

---

# PHASE 13 — Notebook updates

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

Every notebook must:

- use canonical artifact names;
- include portable bundle configuration;
- derive permission binding from active variables;
- claim provider-specific permission;
- record authorization proof;
- update provider-local state;
- package permission proof in returned ZIP;
- fail before model loading on mismatch;
- print exact local handoff command.

00C2 must have correct shard semantics.

---

# PHASE 14 — Update master execution plan

Update:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
docs/execution/CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

The real route must be:

1. provision wheelhouse;
2. provision three snapshots;
3. build portable two-item smoke bundle;
4. run 00A;
5. run 00B for each provider;
6. run 00C2 for each provider;
7. run one-click smoke handoff;
8. build confirmatory task bundle;
9. complete review, selection, detectability;
10. issue matrix authorization;
11. derive three provider permissions;
12. run three provider notebooks in separate Kaggle sessions;
13. return three provider ZIPs;
14. reconcile provider proofs;
15. run transactional atomic import;
16. analyze and sign Main decision.

No hidden ledger-copy step may remain.

---

# PHASE 15 — Potential final upgrades

Implement only when they directly improve run safety.

## 15.1 Provider proof viewer

Create a concise human-readable report for each returned provider proof.

## 15.2 Transaction recovery CLI

Provide:

```bash
python3 -m certvic.cvpr.import_transaction recover ...
```

## 15.3 Runtime calibration

Use real 00C2 outputs later to update runtime/VRAM estimates.

## 15.4 Ready-to-run command generator

Given all external paths, generate the exact notebook configuration blocks and local commands.

## 15.5 Main candidate sufficiency planner

Estimate expected retained counts using configurable QA/review rejection assumptions.

---

# PHASE 16 — Required deliverables

Create or update:

```text
reports/cvpr_10of10_readiness/CERTVIC_10OF10_SESSION.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_DEFECTS.csv
reports/cvpr_10of10_readiness/CERTVIC_10OF10_CHANGELOG.csv
reports/cvpr_10of10_readiness/CERTVIC_10OF10_COMMANDS.csv
reports/cvpr_10of10_readiness/CERTVIC_10OF10_VALIDATION.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_SCORECARD.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_READY_TO_RUN_HANDOFF.md

certvic/cvpr/smoke_artifacts.py
certvic/cvpr/notebook_permission_binding.py
certvic/cvpr/reconcile_provider_permissions.py
certvic/cvpr/import_transaction.py
certvic/cvpr/smoke_handoff.py

docs/execution/CERTVIC_REAL_SMOKE_ARTIFACT_CONTRACT.md
docs/execution/CERTVIC_MULTI_SESSION_PERMISSION_GUIDE.md
docs/execution/CERTVIC_TRANSACTIONAL_IMPORT_RECOVERY_GUIDE.md
docs/execution/CERTVIC_MAIN_OVERSAMPLING_GUIDE.md
docs/execution/CERTVIC_10OF10_READY_TO_RUN_GUIDE.md

CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

---

# PHASE 17 — Final validation

Run:

- focused 10/10 tests;
- full test suite;
- Ruff;
- compileall;
- type checks when configured;
- 00A artifact tests;
- 00B artifact tests;
- 00C2 bundle-propagation tests;
- T4×2 shard tests;
- single-GPU fallback tests;
- active-variable permission binding tests;
- provider-specific authorization tests;
- multi-session simulator tests;
- synthetic-vs-real smoke tests;
- smoke/snapshot equality tests;
- detectability exact-byte binding tests;
- two-phase import recovery tests;
- replay rejection tests;
- Main oversampling tests;
- one-click smoke handoff tests;
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

00C2 worker receives task_bundle_root and task_bundle_manifest
00C2 packaging expects exactly the shards actually produced
00A/00B/00C2 outputs are consumed directly by smoke_gate
permission bindings are derived from active notebook variables
separate Kaggle sessions require no shared mutable ledger
each provider ZIP carries a verifiable authorization proof
synthetic smoke cannot authorize a real scientific run
smoke snapshot/environment equals scientific snapshot/environment
detectability gate binds exact task and image bytes
import plus permission consumption is recoverable and idempotent
Main candidate pool has realistic oversampling buffers
release works from clean extraction
```

---

# 6. Final status rule

Report:

```text
CVPR_PRE_EXECUTION_READY
```

only if all local criteria pass and the next action is genuinely real 00A/00B/00C2 execution.

Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and list the exact remaining local defect.

Do not report percentages such as 98/100 when a real notebook is still guaranteed to fail.

For the final scorecard:

- `10/10 pre-run readiness` means zero known local blockers.
- Real evidence readiness may remain low because real runs and human review have not happened.

---

# 7. Required final response

Use this structure:

## 1. Executive verdict

## 2. Final Kaggle handoff defects repaired

For each include:

- path;
- original failure;
- repair;
- regression test;
- result.

## 3. 00A/00B/00C2 canonical artifacts

## 4. Portable bundle propagation

## 5. T4×2 smoke behavior

## 6. Multi-session provider permissions

## 7. Smoke-to-scientific identity binding

## 8. Detectability exact-byte binding

## 9. Transactional import and recovery

## 10. Main oversampling

## 11. Kaggle-session simulator

## 12. Notebook readiness

## 13. Release self-containment

## 14. Validation results

Give exact commands, exits, and test totals.

## 15. Remaining external blockers

Only list:

- wheelhouse bytes;
- snapshots;
- source datasets;
- real Kaggle runs;
- real human review;
- real model evidence.

## 16. Exact next sequence

The next action must be:

1. attach wheelhouse;
2. attach snapshots;
3. run 00A;
4. run 00B;
5. run 00C2;
6. return artifacts.

## 17. Readiness verdict

Report separately:

```text
Local pre-run readiness: 10/10 or not
Real evidence readiness: current honest level
```

## 18. Files created or modified

## 19. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/cvpr_10of10_readiness/CERTVIC_10OF10_READY_TO_RUN_HANDOFF.md
```

---

# 8. Success standard

This is the final implementation prompt.

After this pass, there must be no local repair between the repository and real Kaggle smoke.

The project succeeds only when a user can:

1. attach the external assets;
2. run the notebooks exactly as documented;
3. download the canonical artifacts;
4. run one local handoff command;
5. receive a strict smoke decision;
6. issue provider-specific permissions;
7. run three separate Kaggle sessions;
8. return three ZIPs;
9. atomically import them;
10. continue to analysis without manual ledger surgery.

**Finish the real Kaggle handoff completely, eliminate all hidden manual steps, prove multi-session authorization and recovery, and leave CertVIC at genuine 10/10 pre-run readiness.**
