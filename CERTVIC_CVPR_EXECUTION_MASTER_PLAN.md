# CertVIC CVPR execution master plan

This is the sole continuation point. The active tree passes its repaired baseline tests and contains
the maximum-ceiling operator/recovery layer, but the full replacement archive required by the
migration specification was not present. Therefore the honest migration status is
`PARTIALLY_READY_WITH_BLOCKERS`; the active runtime is locally ready to begin external provisioning
and 00A. `paper_evidence=false`; Main and COCO remain `execution_allowed=false`.

The repaired-baseline capability label `CVPR_PRE_EXECUTION_READY` is retained for backward-compatible
runbooks; it describes the active runtime's pre-execution route, not completion of the requested
repository replacement or the overall migration verdict.

Frozen facts remain Qwen V1 `12/94 = 0.1277`, InternVL V1 `1/94 = 0.0106`, and LLaVA V1
`3/94 = 0.0319`. The frozen V1 rule is observed flip rate at most `0.10`, so Qwen fails. V2-30 is
retrospective sensitivity only. Confirmatory is prospective with zero V1 overlap. Genuine
`human_reviewed=true` count is zero and no real COCO evidence exists.

Start with:

```bash
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
```

## Canonical 28-step route

| # | Action | Inputs | Command or notebook | Hardware / estimate | Output and validation | Retry, recovery, downstream gate |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Verify checkout | active tree | `python3 -m compileall -q certvic scripts tests` | local CPU / <5 min | imports and tree pass | repair exact local error; then doctor |
| 2 | Run doctor | configs, notebooks, code | `python3 -m certvic.cvpr.doctor --json` | local CPU / <1 min | one readiness state and stable blockers | read-only retry; then wheelhouse |
| 3 | Provision wheelhouse | environment lock | `execution_pack/01_EXTERNAL_ASSETS_CHECKLIST.md` | networked provisioner / 30–90 min | all-wheel hash manifest | resume and rehash; then snapshots |
| 4 | Provision snapshots | model registry | external checklist | networked provisioner / 2–6 h | three unified all-file manifests | resume per provider and rehash; then smoke bundle |
| 5 | Create portable smoke bundle | code, wheelhouse, configs | package-run tooling | local CPU / 5–15 min | deterministic private bundle | atomic rebuild; then 00A |
| 6 | Run 00A | bundle, wheelhouse, env lock | `00A_certvic_code_and_environment_smoke.ipynb` | Kaggle CPU, accelerator off / 10–20 min | exact environment artifacts, offline pass; no model load | new session, same bytes; then 00B |
| 7 | Run 00B per provider | accepted 00A, one snapshot | `00B_certvic_model_snapshot_smoke.ipynb` | Kaggle CPU, accelerator off / 15–30 min each | exact snapshot, configuration, processor, and tokenizer integrity; no model load | isolate failed provider; then pre-smoke authorization |
| 8 | Issue pre-smoke matrix | 00A + three 00B artifacts | `reconcile_provider_permissions issue-matrix ...` using smoke-only inputs | local CPU / <5 min | parent binds only 00C2 bytes | regenerate only on input-byte change; then children |
| 9 | Derive three pre-smoke permissions | parent, provider config, smoke gate | `reconcile_provider_permissions derive-provider ...` | local CPU / <5 min | three expiring one-run nonces | never reset nonce; then 00C2 |
| 10 | Run 00C2 separately | parent/child, fixtures, snapshot | `00C2_certvic_real_model_two_item_smoke.ipynb` | Kaggle T4x2 / 20–60 min each | first genuine model load and inference; one ten-member canonical ZIP per provider | audited failure + new permission; then handoff |
| 11 | Run smoke handoff | exact 00A/00B/00C2 returns | `python3 -m certvic.cvpr.smoke_handoff ...` | local CPU / <5 min | all-three real-model importer-grade pass | preserve bytes, follow stable error; then candidates |
| 12 | Build confirmatory candidates | licensed ADE20K, exclusion inventory | `01_specificity_confirmatory_generation_T4x2.ipynb` | Kaggle T4x2 / 2–8 h | outcome-unseen candidates, zero overlap | frozen queue resume; then controls/QA |
| 13 | Generate controls and QA | candidates, frozen study policy | confirmatory QA/generation tools | local CPU or Kaggle / 30–90 min | protected geometry, quality, license, reserve checks | retry exact candidate only; then review |
| 14 | Complete review/adjudication | immutable blind packet | `python3 -m certvic.cvpr.review ...` | two humans + adjudicator / 8–20 h | qualified, complete, independent, signed final ledger | resolve missing rows; packet changes need version; then selection |
| 15 | Exact selection | final inclusion + locked strata | candidate-selection tooling | local CPU / 5–20 min | primary/reserve universe exactly balanced | same-stratum frozen replacements only; then detectability |
| 16 | Run detectability | exact selected task/image bytes | `python3 -m certvic.cvpr.detectability_gate ...` | local CPU / 15–60 min | set-level gate bound to task bytes | no threshold tuning; then freeze |
| 17 | Freeze tasks | final tasks, bundle, review, detectability | freeze-manifest tooling | local CPU / <5 min | immutable task/bundle hashes | rebuild only before outcome execution; then scientific matrix |
| 18 | Issue scientific matrix | freeze, review, detectability, env, registry, prompt, code | `reconcile_provider_permissions issue-matrix ...` | local CPU / <5 min | separate scientific authorization | expires/reissue without byte changes; then provider children |
| 19 | Derive scientific provider permissions | scientific matrix, snapshot, real smoke | `derive-provider ...` | local CPU / <5 min | three provider/run/nonces | never copy/reset; then scientific notebooks |
| 20 | Run three confirmatory notebooks | exact task bundle + child permission | notebooks 02, 03, 04 | Kaggle T4x2 / 1–4 h each | three canonical provider ZIPs | fixed OOM-halving/transient retry only; then reconcile |
| 21 | Reconcile provider proofs | parent and three unchanged ZIPs | `reconcile_provider_permissions reconcile ...` | local CPU / <5 min each | provider, nonce, event, environment, snapshot, row proof | replace no bytes; then transaction |
| 22 | Transactionally import | reconciled matrix, strict import config | `python3 -m certvic.cvpr.import_transaction run ...` | local CPU / 5–20 min | journaled atomic promotion and nonce commit | `recover --journal ...`; then analysis |
| 23 | Analyze | canonical import, preregistered plan | `python3 -m certvic.cvpr.after_runs ... --strict` | local CPU / 15–60 min | raw/filtered denominators, CS, McNemar/Holm, audits, trace | idempotent rebuild from immutable inputs; then Main decision |
| 24 | Issue Main decision | confirmatory decision + review proof | planning/go-no-go tooling | local CPU / <5 min | signed machine-readable `GO` or `NO_GO` | fail closed on missing/inconclusive data; then conditional Main |
| 25 | Execute conditional Main | separate Main freeze/review/permission | notebooks 10–13 only if `GO` | Kaggle + humans / conditional | genuine Main import/analysis or explicit blocked record | same frozen transactional protocol; then paper |
| 26 | Execute COCO feasibility | real licensed COCO assets + separate permission | notebooks 20–23 only if authorized | Kaggle + humans / conditional | real feasibility output or explicit blocked record | no asset fabrication; then paper |
| 27 | Compile paper evidence | verified artifact registry and eligible classes only | `python3 -m certvic.cvpr.paper_evidence_compiler ...` | local CPU + TeX / 10–30 min | guarded manifest, tables, twice-built PDF hash | refuse planned/synthetic/retrospective promotion; then release |
| 28 | Build final release | canonical source, configs, guards, reports | `python3 scripts/build_maximum_ceiling_release.py --deterministic-rebuild --clean-extraction` | local CPU / 10–30 min | byte-identical ZIP, hashes, clean CLI proof | repair exact audit failure and rebuild |

## Authorization and evidence boundaries

Pre-smoke and scientific authorizations are distinct. Parent and child verification occurs before
hardware inspection, CUDA access, model loading, or output creation. Static study configs remain
`execution_allowed=false`; only a verified, expiring, hash-bound permission confers authority.

Only genuine permission-bound imports plus genuine adjudicated review may activate a paper branch.
Smoke, simulators, synthetic notebook proof, historical V1, retrospective V2-30, packaging, and
software tests remain non-paper evidence.

## Execution classifications

The frozen operational classes are `MANUAL_DATA_PROVISION`, `CPU_LOCAL`, `CPU_KAGGLE`,
`GPU_KAGGLE_T4X2`, `GPU_KAGGLE_SINGLE_FALLBACK`, `HUMAN_REVIEW`, and
`POST_RUN_CPU_ANALYSIS`.

## Final paper trigger

The paper branch may activate only from hash-verified eligible registry artifacts after genuine
human review, transactional import, preregistered analysis, and claim/privacy guards pass. Until
then, the guarded results branch and `paper_evidence=false` remain active.

## Canonical smoke and recovery contract

00A returns environment JSON, validation JSON, and bundle ZIP. 00B returns equivalent provider
snapshot artifacts. Each 00C2 ZIP has predictions, runtime, environment, snapshot, task-bundle,
validation, hash manifest, authorization proof, provider permission, and permission events. No
renaming, JSON edit, hash copy, permission reset, or ZIP surgery is allowed.

Packaging follows `PACKAGING_STARTED -> PACKAGE_WRITTEN -> OUTPUT_PACKAGED`. Import uses a durable
journal and atomic promotion. Recover post-promotion failures with `import_transaction recover`.
Never delete a journal or reset a consumed nonce. A repeated matching import is idempotent; a changed
ZIP or destination under the same nonce is replay and fails closed.

## Exact continuation

Follow `execution_pack/00_READ_ME_FIRST.md`, provision the offline wheelhouse and three snapshots,
then run 00A, 00B for each provider, pre-smoke authorization, and 00C2 for each provider. Do not run
another repair prompt and do not begin confirmatory scientific inference before all intervening gates.
