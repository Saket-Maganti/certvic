# Kaggle main-200 bundle — build report

Deliverable for the **next GPU step**: diffusion edit generation for the CertVIC
main-200 pilot on a free Kaggle **T4×2** notebook. Result-free, pixel-free,
weight-free. Nothing here is an evidence claim.

## Artifacts

| Artifact | Path |
| --- | --- |
| Bundle | `dist/certvic_kaggle_main200_bundle.zip` |
| Manifest | `dist/certvic_kaggle_main200_bundle_manifest.json` |
| Security audit (md) | `docs/KAGGLE_BUNDLE_SECURITY_AUDIT.md` |
| Security audit (json) | `data/results/kaggle_bundle_security_audit.json` |
| In-bundle README | `README_KAGGLE_BUNDLE.md` (also at bundle root) |
| Builder | `scripts/build_kaggle_main200_bundle.py` |
| Checker | `certvic/security/audit_kaggle_bundle.py` |

## Bundle facts

- Entries: **356** · uncompressed **2.66 MB** · zipped **~530 KB**
- Deterministic content digest: `e047ed8523da3ed668fdd8a8c52417f75fbcd8f55845b2418ac039b7214d2f17`
- Security audit: **PASS — 0 findings** (no pixels, no weights, no private paths, no secrets)
- Reproducible: fixed zip timestamps + sorted entries; `build_manifest` digest is stable.

## Which dataset (and why)

`ade20kdataset/ade20k.zip → ADEChallengeData2016/` — the MIT Scene Parsing release
with semantic-PNG annotations; the adapter inspection passes (`supported_layout`,
22,210 matched pairs). `ADE20K-main.zip` (toolkit/per-instance) and
`ade20k-DatasetNinja.tar` (Supervisely polygon JSON) are **not** used. The bundle
contains **no ADE20K pixels** — attach ADE20K as a separate Kaggle dataset and set
`ADE20K_ROOT`. See `docs/runbooks/DATASET_DECISION.md`.

## Contents (high level)

| Group | Count | Purpose |
| --- | --- | --- |
| `certvic/` | 288 | package: mask loader, quality gates, engines, schema, runners, security |
| `commands/` | 23 | staged command manifests (incl. `main_200/`) |
| `configs/` | 17 | run configs (incl. `real_pilot_ade20k.yaml`, `kaggle_open_vlm.yaml`) |
| `scripts/` | 7 | helpers (incl. `split_edit_plan_by_shard.py`, bundle + notebook builders) |
| `notebooks/kaggle/` | 3 | **ready-to-run** `.ipynb`: precache weights + diffusion (next step) + VLM (after-gates) |
| `docs/` | 6 | runbooks (diffusion + VLM), dataset decision, V6 run-after checklist, V6 handoff |
| `data/results/main_real_200/` | 10 | **planning artifacts only** (sanitized) |
| `pyproject.toml`, `README_KAGGLE_BUNDLE.md` | 2 | deps reference + bundle README |

Planning artifacts: `pilot_selection.jsonl` (200), `pilot_edit_plan.jsonl` (168),
`gpu_shards/pilot_edit_plan_shard{0,1}_of_2.jsonl` (81 / 87), `diffusion_job_queue.jsonl`,
`diffusion_resume.jsonl`, plus the `*_summary.json` and `pilot_task_preview.jsonl`.

## Explicitly excluded

ADE20K images/annotations · generated edited images · model weights · `.git/` ·
virtualenvs · `__pycache__`/`.pytest_cache`/`.ruff_cache` · large raw datasets ·
local private absolute paths · API keys/secrets/credentials · mock/smoke outputs ·
the large pointer manifests (`ade20k_sources.jsonl`, `ade20k_masks.jsonl` — not
needed for diffusion; the edit plan already carries `mask_path` + `label_id` + bbox).

## Path remapping (no private paths in the bundle)

Planning manifests are sanitized at build time: the local ADE20K root is replaced
with the token `__ADE20K_ROOT__`. On Kaggle the diffusion runbook detects that
token (the prefix before `/images/`) and swaps it for `$ADE20K_ROOT` (the real
mount). For an un-sanitized manifest, set `CERTVIC_LOCAL_ADE20K_ROOT`. No local
home-directory absolute path is ever written into docs, scripts, or the bundle.

## T4×2 execution (diffusion only)

- **GPU 0 → session 1 → shard 0** (81 edits), `CUDA_VISIBLE_DEVICES=0`
- **GPU 1 → session 2 → shard 1** (87 edits), `CUDA_VISIBLE_DEVICES=1`
- Both launched in parallel, then `wait`; separate out-dirs / manifests / logs;
  resume-safe (re-run skips finished `edit_id`s); final merge concatenates the two
  per-shard manifests. **No VLM eval in the diffusion notebook.** Full cells:
  `docs/runbooks/KAGGLE_T4x2_DIFFUSION_EDITS.md`.

## Download back to the local repo

`pilot_generated_edits.jsonl` (merged), `diffusion_out.zip` (edited PNGs),
`gen_summary_shard{0,1}.json`, `log_shard{0,1}.txt` → into
`data/results/main_real_200/` and `data/edits/main_real_200/`.

## Gate that decides whether VLM may start

After the edits return, run **quality + detectability** on the Mac. VLM eval stays
blocked until **all** pass: quality gates, **detectability AUC < 0.80**, human
visual review (`pilot_eval_tasks_reviewed.jsonl`), and item certificates.
`run_eval --evidence-run` refuses non-open-local providers and unreviewed tasks.
Crude CPU edits (detectability AUC ≈ 0.92) are non-evidence and correctly blocked.

## Rebuild + re-audit

```bash
python3 -m scripts.build_kaggle_main200_bundle
python3 -m certvic.security.audit_kaggle_bundle \
  --bundle dist/certvic_kaggle_main200_bundle.zip --strict \
  --out docs/KAGGLE_BUNDLE_SECURITY_AUDIT.md \
  --json-out data/results/kaggle_bundle_security_audit.json
```
