# CERTVIC — TRANSACTIONAL REPLACEMENT AND MAXIMUM-CEILING UPGRADE MASTER PROMPT

## Mission

You are the lead repository migration engineer, research-systems architect, Kaggle runtime engineer, VLM deployment engineer, benchmark architect, provenance engineer, statistician, security engineer, release engineer, and critical CVPR co-author for **CertVIC**.

This task has two mandatory parts:

1. Replace the current checkout with the repaired complete repository ZIP already placed inside the CertVIC folder.
2. Upgrade that repaired baseline to the strongest honest pre-run ceiling possible.

Do not perform another audit-only pass. Do not stop after recommendations. Do not create duplicate frameworks. Carry the work through migration, implementation, integration, validation, release sealing, and final handoff.

The target local status is:

```text
CVPR_PRE_EXECUTION_READY
MAXIMUM_CEILING_PRE_RUN_BUILD_COMPLETE
LOCAL_PRE_RUN_READINESS_10_OF_10
```

Use that status only if all local paths pass and only real external assets, compute, reviewers, and evidence remain. Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and identify the exact local defect.

---

# 1. Repository and repaired archive

Expected repository:

```text
/Users/saketmaganti/Projects/certVIC
```

Expected repaired archive inside it:

```text
certVIC_9_SMOKE_AUTHORIZATION_FIXED_FULL.zip
```

When that exact filename is absent, locate the newest unambiguous full-project archive matching:

```text
*certVIC*
*SMOKE_AUTHORIZATION*
*FIXED*
*FULL*.zip
```

Do not select patch-only, release-only, historical evidence, Kaggle-output, or provider-return ZIPs.

The selected archive must contain:

```text
certvic/
tests/
configs/
notebooks/
scripts/
pyproject.toml
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

Record its path, SHA-256, size, member count, and detected repository root.

---

# 2. Frozen scientific boundaries

Preserve exactly:

- Qwen2.5-VL-7B V1 flips: `12/94 = 0.1277`.
- InternVL2-8B V1 flips: `1/94 = 0.0106`.
- LLaVA-OneVision-7B V1 flips: `3/94 = 0.0319`.
- Frozen V1 rule: `observed_spurious_flip_rate <= 0.10`.
- Qwen fails the frozen V1 rule.
- V2-30 remains retrospective sensitivity evidence.
- Confirmatory remains prospective and zero-overlap with V1.
- Main remains blocked until confirmatory and genuine human-review gates pass.
- No real COCO evidence exists.
- `paper_evidence=false`.
- Genuine `human_reviewed=true` count remains zero until real review occurs.
- No outputs, labels, commits, runtimes, metrics, or paper results may be fabricated.
- No prompt, threshold, item, expected answer, model revision, filter, or analysis rule may be tuned after observing real outcomes.

Do not delete or rewrite historical raw evidence.

---

# 3. Transactional repository replacement

The user has already backed up the project and explicitly wants Codex to replace the checkout. Do not create another full backup archive.

## 3.1 Stage outside the repository

Extract into a sibling staging directory:

```text
/Users/saketmaganti/Projects/.certvic_replacement_stage_<timestamp>
```

Do not extract over the live checkout.

Reject:

- path traversal;
- duplicate archive members;
- unsafe symlinks;
- malicious nested paths;
- implausible archive expansion ratios.

Normalize one accidental outer directory level when necessary.

## 3.2 Validate the staged repository

Before replacing anything:

- verify required files and directories;
- run `compileall`;
- import critical runtime modules;
- run focused smoke-authorization and final-runtime tests;
- verify all 16 CVPR notebooks;
- verify pre-smoke and scientific authorization are separate;
- verify repaired 00C2;
- verify the execution plan and handoff.

Critical imports:

```text
certvic.cvpr.smoke_gate
certvic.cvpr.smoke_artifacts
certvic.cvpr.package_run
certvic.cvpr.execution_gate
certvic.cvpr.reconcile_provider_permissions
certvic.cvpr.notebook_builder
certvic.cvpr.notebook_00c2_proof
certvic.cvpr.task_bundle
certvic.cvpr.import_transaction
certvic.cvpr.after_runs
```

## 3.3 Preserve the incoming archive

Temporarily move the ZIP outside the live repository before clearing old files.

After successful replacement, place it under:

```text
local_inputs/incoming_archives/
```

Exclude that directory from releases and version-control surfaces.

## 3.4 Replace contents

After staged validation succeeds:

- remove stale old repository contents;
- synchronize the repaired staged repository into the existing CertVIC root;
- prevent nested `certVIC/certVIC`;
- retain only clearly external user-owned dataset mounts or symlinks;
- do not preserve stale source files absent from the repaired archive merely to avoid deletion.

The repaired archive becomes the active baseline.

## 3.5 Replacement records

Create:

```text
reports/repository_replacement/CERTVIC_REPLACEMENT_SESSION.md
reports/repository_replacement/CERTVIC_REPLACEMENT_ARCHIVE.json
reports/repository_replacement/CERTVIC_REPLACEMENT_FILE_DIFF.csv
reports/repository_replacement/CERTVIC_REPLACEMENT_VALIDATION.md
```

Record archive SHA-256, staged-tree hash, replaced files, stale files removed, preserved external paths, commands, and final active-tree hash.

---

# 4. Validate repaired baseline

Run:

```bash
python3 -m pytest -q
python3 -m compileall -q certvic scripts tests
python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr
python3 scripts/validate_t4x2_notebooks.py
```

Also run claim guard, privacy guard, paper compilation twice, repaired smoke-authorization tests, final-runtime tests, clean release extraction, and deterministic release rebuild.

Repair any failure before adding upgrades.

---

# 5. Maximum-ceiling upgrades

Implement only upgrades that materially improve execution reliability, operator usability, provenance, recovery, reproducibility, statistical defensibility, reviewer trust, runtime planning, paper evidence safety, or release quality.

Avoid decorative dashboards and speculative feature sprawl.

## Upgrade A — Project doctor

Create:

```text
certvic/cvpr/doctor.py
```

Commands:

```bash
python3 -m certvic.cvpr.doctor
python3 -m certvic.cvpr.doctor --study specificity_confirmatory_cvpr
python3 -m certvic.cvpr.doctor --json
```

Inspect repository integrity, environment, wheelhouse, data, licenses, snapshots, task bundles, 00A/00B/00C2, smoke gate, review, detectability, task freeze, permissions, provider returns, import transactions, analysis, paper branch, and release.

Return one state:

```text
READY_FOR_00A
READY_FOR_00B
READY_FOR_00C2
READY_FOR_CONFIRMATORY_BUILD
READY_FOR_HUMAN_REVIEW
READY_FOR_AUTHORIZATION
READY_FOR_MODEL_RUNS
READY_FOR_IMPORT
READY_FOR_ANALYSIS
BLOCKED
```

Every blocker must include an error code, missing artifact, next command, remediation, and whether it is local or external.

## Upgrade B — Next-action tool

Create:

```text
certvic/cvpr/next_action.py
```

Commands:

```bash
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.next_action --execute-local-safe
```

Default is read-only. Local-safe execution may only hash, validate, package, run synthetic tests, compile the paper, or audit releases. Never launch real inference, GPU jobs, human review, or alter frozen configs.

## Upgrade C — Execution DAG

Create:

```text
configs/execution/certvic_run_graph.yaml
certvic/cvpr/run_graph.py
```

Each node records ID, study, prerequisites, inputs, outputs, command/notebook, hardware, permission class, retry/recovery, evidence class, and downstream nodes.

Commands:

```bash
python3 -m certvic.cvpr.run_graph status
python3 -m certvic.cvpr.run_graph explain <NODE>
python3 -m certvic.cvpr.run_graph next
python3 -m certvic.cvpr.run_graph export-dot
```

## Upgrade D — Artifact registry

Create:

```text
certvic/cvpr/artifact_registry.py
```

Track task bundles, environments, snapshots, smoke artifacts, review artifacts, detectability reports, permissions, provider ZIPs, imports, analyses, figures, paper PDFs, and releases.

Record artifact ID, role, SHA-256, size, schema, study, parent artifacts, evidence class, immutable location, aliases, and creation time.

Provide add, verify, and lineage commands. Avoid unnecessary duplication.

## Upgrade E — Reproducibility capsule

Create:

```text
certvic/cvpr/reproducibility_capsule.py
```

Bind code, task bundle, freeze, review, detectability, environment, snapshots, model registry, prompt hash, parser, run contract, permission, provider nonce, returned ZIP, import transaction, and analysis plan.

Provide one verification command for the entire chain.

## Upgrade F — Kaggle configuration generator

Create:

```text
certvic/cvpr/kaggle_config.py
```

Example:

```bash
python3 -m certvic.cvpr.kaggle_config \
  --notebook 00C2 \
  --provider qwen2_5_vl_7b \
  --out generated_configs/
```

Generate ready-to-paste config cells, required datasets, expected filenames, environment variables, output filenames, handoff command, and validation checklist. Never embed private absolute paths.

Support 00A, 00B, 00C2, confirmatory, Main, and COCO.

## Upgrade G — Actual notebook runner

Create:

```text
certvic/cvpr/notebook_runner.py
```

Use `nbclient` or a primary Jupyter execution mechanism.

Support config injection, timeouts, cell logs, failure-cell extraction, artifact collection, output clearing, and deterministic reports.

Execute actual synthetic versions of 00A, 00B, all three 00C2 notebooks, one generation notebook, one scientific-provider notebook, and one post-run workflow.

Repository notebooks must retain empty outputs.

## Upgrade H — Chaos suite

Create:

```text
certvic/cvpr/chaos.py
tests/test_cvpr_chaos.py
```

Inject corrupt ZIPs, missing/duplicate members, wrong provider/snapshot/environment/prompt/parser/run contract, stale permissions, replay, packaging interruption, transaction interruption, disk failure, incomplete review, detectability failure, solver timeout, missing images, hash mismatch, and missing provider returns.

Verify fail-closed behavior, stable codes, no canonical corruption, recovery instructions, and idempotent retry.

## Upgrade I — Runtime planner

Create:

```text
certvic/cvpr/runtime_planner.py
```

Estimate latency, VRAM, batch size, notebook duration, GPU-hours, ZIP size, disk requirements, and review hours.

Before smoke, label values as estimates. After smoke, recalibrate from non-evidence runtime manifests. Warn about Kaggle session, VRAM, storage, and checkpoint risks.

## Upgrade J — Data and license registry

Create:

```text
certvic/data/license_registry.py
configs/data/source_license_registry.yaml
```

Track dataset, split, origin, local root, redistribution, paper use, image-level license, insertion-asset license, reviewer visibility, and release inclusion.

Task builders fail closed on unresolved licenses. Release packaging excludes non-redistributable files.

## Upgrade K — Human-review hardening

Extend the review CLI with packet inventory, reviewer progress, missing-row detection, qualification expiry, adjudicator assignment, immutable timeline, exclusion-reason HTML, blind-ID verification, and packet-version diff.

Do not create fake identities or auto-complete sheets.

## Upgrade L — Statistical hardening

Add raw and filtered denominators, confidence-sequence outputs, Bonferroni declaration, McNemar/Holm matrix, exclusion sensitivity, family/category/stratum breakdowns, missingness audit, provider completion audit, decision trace, and machine-readable claim eligibility.

Test against hand-calculated tiny fixtures.

## Upgrade M — Paper evidence compiler

Create:

```text
certvic/cvpr/paper_evidence_compiler.py
```

Read only canonical evidence-registry artifacts, verify hashes, generate tables and figures, create a paper-injection manifest, activate permitted branches, preserve synthetic/historical labels, refuse planned/synthetic data as real evidence, run guards, compile paper, and record PDF hash.

## Upgrade N — Maximum hardened release

Build:

```text
release/certvic_cvpr_pre_run_maximum.zip
```

Include canonical source, configs, notebooks, synthetic fixtures, guides, doctor, next-action tool, run graph, registry, capsule verifier, notebook runner, chaos suite, planner, license registry, paper source, release manifest, and reports.

Exclude weights, datasets, private review sheets, incoming project archives, caches, secrets, temp files, and host paths.

Require deterministic timestamps/order, byte-identical builds, member hashes, dependency closure, clean extraction, critical CLI execution, and synthetic end-to-end proof.

## Upgrade O — Security and privacy

Check archive traversal, ZIP bombs, duplicate members, unsafe symlinks, shell injection, unsafe subprocesses, secrets, home paths, emails, notebook outputs, unsafe pickle/YAML, and unpinned remote-code assumptions.

Do not weaken privacy guards.

## Upgrade P — User execution pack

Create:

```text
execution_pack/
  00_READ_ME_FIRST.md
  01_EXTERNAL_ASSETS_CHECKLIST.md
  02_00A_INSTRUCTIONS.md
  03_00B_INSTRUCTIONS.md
  04_00C2_INSTRUCTIONS.md
  05_SMOKE_HANDOFF.md
  06_CONFIRMATORY_BUILD.md
  07_HUMAN_REVIEW.md
  08_SCIENTIFIC_RUNS.md
  09_IMPORT_AND_ANALYSIS.md
  10_FAILURE_RECOVERY.md
```

Every guide must contain exact commands, inputs, outputs, validation, retry, and recovery. No hidden steps.

---

# 6. Canonical execution order

Update both master plans and README:

1. verify checkout;
2. run doctor;
3. provision wheelhouse;
4. provision snapshots;
5. create portable smoke bundle;
6. run 00A;
7. run 00B per provider;
8. issue pre-smoke matrix authorization;
9. derive three pre-smoke permissions;
10. run 00C2 in separate Kaggle sessions;
11. run smoke handoff;
12. build confirmatory candidates;
13. generate controls and QA;
14. complete review and adjudication;
15. exact selection;
16. detectability;
17. task freeze;
18. issue scientific matrix authorization;
19. derive scientific provider permissions;
20. run three confirmatory notebooks;
21. reconcile provider proofs;
22. transactionally import;
23. analyze;
24. issue Main decision;
25. execute conditional Main;
26. execute COCO feasibility;
27. compile paper evidence;
28. build final release.

For every step list inputs, command/notebook, hardware, estimate, output, validation, retry, recovery, and downstream gate.

---

# 7. Final validation

Run:

- full pytest;
- replacement tests;
- doctor and next-action tests;
- run-graph tests;
- registry and capsule tests;
- Kaggle-config tests;
- actual notebook execution tests;
- chaos tests;
- planner tests;
- license-registry tests;
- review dry-run tests;
- statistical fixture tests;
- paper compiler tests;
- release audit;
- clean extraction;
- deterministic rebuild;
- Ruff;
- compileall;
- configured type checks;
- notebook validators;
- claim guard;
- privacy guard;
- paper compile twice.

Verify:

```text
paper_evidence=false
genuine human_reviewed=true count = 0
Main execution_allowed=false
COCO execution_allowed=false
V2-30 remains retrospective
no real GPU evidence created
no human labels fabricated
no model commit fabricated

repaired ZIP installed successfully
no nested repository exists
stale old runtime files removed
00A/00B/00C2 are directly runnable after external provisioning
pre-smoke and scientific authorizations remain separate
canonical smoke artifacts need no editing
three provider sessions reconcile offline
transaction recovery is idempotent
detectability binds exact task bytes
Main oversampling remains sufficient
release works from clean extraction
```

---

# 8. Required reports

Create:

```text
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_SESSION.md
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_DEFECTS.csv
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_CHANGELOG.csv
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_COMMANDS.csv
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_VALIDATION.md
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_SCORECARD.md
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_READY_TO_RUN_HANDOFF.md
```

---

# 9. Final status rule

Report:

```text
CVPR_PRE_EXECUTION_READY
MAXIMUM_CEILING_PRE_RUN_BUILD_COMPLETE
LOCAL_PRE_RUN_READINESS_10_OF_10
```

only if replacement, all upgrades, actual synthetic notebook execution, release extraction, and guards pass.

Otherwise report:

```text
PARTIALLY_READY_WITH_BLOCKERS
```

and identify the exact local failure.

---

# 10. Required final response

Use:

## 1. Executive verdict

## 2. Repository replacement

Include selected archive, SHA-256, staging validation, replacement result, stale files removed, and preserved external paths.

## 3. Repaired baseline validation

## 4. Maximum-ceiling upgrades

For every upgrade include path, purpose, implementation, tests, and result.

## 5. Doctor and next-action system

## 6. Run graph, artifact registry, and reproducibility capsule

## 7. Kaggle configuration and actual notebook proof

## 8. Chaos and recovery validation

## 9. Review and statistical hardening

## 10. Paper evidence compiler

## 11. Release self-containment

## 12. Exact validation results

## 13. Remaining external blockers

## 14. Exact next sequence

The next action must be external provisioning and 00A/00B/00C2—not another repair prompt.

## 15. Readiness verdict

Report local pre-run readiness separately from real evidence readiness.

## 16. Files created or modified

## 17. Master continuation point

Point to:

```text
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
reports/max_ceiling_upgrade/CERTVIC_MAX_CEILING_READY_TO_RUN_HANDOFF.md
execution_pack/00_READ_ME_FIRST.md
```

---

# Success standard

The user has already backed up the project and wants Codex to perform the replacement.

Success means:

1. the repaired ZIP replaces the checkout safely;
2. the repaired runtime remains intact;
3. the project has one-command diagnosis and next-action guidance;
4. dependencies and artifacts are machine-tracked;
5. generated notebooks execute synthetically;
6. recovery is proven;
7. paper and release promotion remain evidence-safe;
8. the maximum release is deterministic and self-contained;
9. the next action is real external provisioning and Kaggle smoke;
10. no further repair prompt is required.

**Replace the checkout transactionally, preserve the evidence boundary, integrate the highest-value upgrades, validate every canonical path, and leave CertVIC at the strongest honest pre-run ceiling possible.**
