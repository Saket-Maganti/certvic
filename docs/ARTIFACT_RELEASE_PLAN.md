# Artifact Release Plan — main_200 pilot

**Status: release readiness assessment, NOT a release** (`evidence_status =
RELEASE_READINESS_NON_EVIDENCE`). Build/refresh the machine-readable manifest with:

```bash
python3 scripts/audit_release_candidate.py        # -> data/results/release_candidate_manifest.json
python3 -m certvic.security.release_privacy_audit --root .
```

The privacy/path/secrets audit currently **passes** (0 findings). The candidate is **not yet
release-ready**: the path-relativization blocker below must be cleared first.

## What can be released (release-safe)

Derived, numeric, pixel-free, path-free artifacts (~29 files), each with a sha256 in the
manifest (cross-checked against the result ledger):

- per-model `pilot_report*/pilot_result.{json,md}`, `presence_certification.json`,
  `presence_scores_summary.json`, `presence_by_edit_type.json`, `absent_object_control.json`
- `multimodel_pilot_summary.{json,md,csv}`, `tables/*`, `score_summary_v2.json`
- `registry/results/main200_pilot_result_ledger.{json,md}`, `registry/datasets/*.json`
- code (`certvic/`, `scripts/`), docs (`docs/`), and Kaggle runbooks (`notebooks/kaggle/*.md`)

## What cannot be released

- **ADE20K image pixels** — `data/edits/**/*.jpg`, `ade20k_root/**`, `ade20kdataset/**`, and
  `ade20k_sources.jsonl` / `ade20k_masks.jsonl` (~49k files). Redistribution is **not**
  permitted. Ship **recipes + sha256 hashes**, never pixels. Requires explicit license
  clearance **and** a user request to package anything pixel-derived.
- **Model weights** — never packaged. Reproduction downloads open weights from public hubs.
- **Credentials / Kaggle tokens** — never included (secrets scan enforces).
- **Unreviewed / rejected private files** — e.g. `*_rejected.jsonl` stay out of any release.

## Blocker before release (needs action)

- **Absolute path relativization (high).** The task manifests and review sheets
  (`pilot_eval_tasks_reviewed_v2.jsonl`, `*/tasks.jsonl`, review CSVs) embed absolute local
  home-directory image paths. These must be rewritten to repo-relative or basename form
  before release. The manifest lists every such file.

## Model-weight policy

Weights are never redistributed. The three open VLMs (Qwen2.5-VL-7B, InternVL2-8B,
LLaVA-OneVision-7B) are pulled from their public hubs on free Kaggle at reproduction time.

## Hash verification

Every release-safe entry carries a sha256 in `release_candidate_manifest.json`; the canonical
scored artifacts reuse the hashes in the result ledger. Verify with
`python3 -m certvic.v7.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json`.

## Expected runtimes

- Local scoring (`pilot_report_from_raw.py`): seconds to ~1 min/model on CPU (no model load).
- Kaggle VLM eval: ~minutes/model (observed ~1.5 s/inference × ~300 inferences).
- Kaggle diffusion edits: ~25 s/edit on a free T4 (planning assumption; see the scale plan).

## License / provenance blockers

- ADE20K pixels (redistribution not permitted) — the single hard license blocker for a full
  data release. The numbers, recipes, hashes, and code are unaffected.
