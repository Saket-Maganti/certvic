# STOP Building Infrastructure — Start the Real Run

The V3 final pre-real-run audit is **green (13/13)**. Per the V3 stop rule, do not
build more infrastructure unless a real run exposes a concrete missing gate. The
remaining work is **empirical, not code**.

## Gate

```bash
python3 -m certvic.v3.final_pre_real_run_audit --out docs/V3_FINAL_PRE_REAL_RUN_AUDIT_REPORT.md --json-out data/results/v3_final_pre_real_run_audit.json
```

## The two real unblockers (only the user can provide these)

1. **A local ADE20K root** — `export ADE20K_ROOT=/path/to/ADEChallengeData2016`
   (pixels are read locally and never rehosted).
2. **Free GPU access** — a Kaggle (or Colab) account for diffusion edits and
   open-VLM inference.

## Exact next steps

```bash
# 0. Confirm the gate is green.
python3 -m certvic.v3.final_pre_real_run_audit

# 1. Plan the full study (no execution).
python3 -m certvic.pipeline.main_study_dry_run --scale 200 --out-dir data/results/main_study_dry_run_200

# 2. Dry-run the tiny pilot against your local ADE20K root.
python3 -m certvic.pipeline.run_tiny_pilot \
  --config configs/real_pilot_ade20k.yaml \
  --ade20k-root "$ADE20K_ROOT" \
  --out-dir data/results/tiny_real_pilot --dry-run

# 3. When the dry-run is clean, run for real (drop --dry-run), generating
#    photorealistic diffusion edits on free GPU, then human-review, then run open
#    VLMs via the model run matrix, score, certify, and report.
```

## Discipline during the real run

- Record every stage with `certvic.provenance.run_ledger add` so paper numbers
  trace back to runs.
- Run `certvic.validation.edit_detectability` and `certvic.eval.output_triage`
  before trusting any gap.
- Inject paper numbers only via `certvic.paper.inject_results` (eligible + hashed).
- If anything fails, `certvic.playbooks.diagnose_failure` maps the symptom to a
  playbook. Report null results honestly; never fabricate.

The critical CVPR risk remains **edit realism / construct validity** — prefer
photorealistic diffusion edits and let the detectability probe confirm low
artifact-confound before reporting.
