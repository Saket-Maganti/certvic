# Free-Compute Job Bundles (V3)

Portable, copy-safe job bundles for free Kaggle/Colab GPU sessions. A bundle is a
directory of text files describing exactly how to run one stage and how to resume
it after the session dies. **No credentials, no private pixels, no paid endpoints,
no execution.** Paths are anonymized to `<LOCAL_PATH>` / `<PLACEHOLDER>` by default.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.compute.job_bundle` | Shared job specs, path anonymization, forbidden-marker safety scan, bundle writer. |
| `certvic.compute.kaggle_packager` | Kaggle-flavored bundle (T4/P100, ~12 h, `/kaggle/input`, `/kaggle/working`). |
| `certvic.compute.colab_packager` | Colab-flavored bundle (T4, idle timeouts, `/content`, optional Drive). |

## Job types

`diffusion_tiny`, `diffusion_200`, `vlm_tiny`, `vlm_200`, `ablations`,
`reports_only`. Each carries: description, stage, GPU-required flag, scale,
preflight commands, run commands, expected inputs, expected outputs.

## Bundle contents

`README.md` (description + zero-cost policy + platform notes + preflight/run/resume),
`commands.sh`, `preflight.sh`, `expected_inputs.md`, `expected_outputs.md`,
`ZERO_COST_POLICY.txt`, and `manifest.json` (job metadata, file hashes,
`evidence_status: JOB_PLANNED_ONLY`, safety-scan result).

## Safety

The builder scans all emitted text for forbidden markers (API keys, bearer
tokens, `sk-` secrets, paid endpoints) and raises rather than writing an unsafe
bundle. Bundles are never executed and never include pixels or weights — those
are mounted as read-only inputs at run time.

## Commands

```bash
python3 -m certvic.compute.kaggle_packager --job diffusion_tiny --config configs/real_pilot_ade20k.yaml --out-dir compute_bundles/kaggle_diffusion_tiny
python3 -m certvic.compute.kaggle_packager --job vlm_tiny       --config configs/tiny_reviewed_eval.yaml --out-dir compute_bundles/kaggle_vlm_tiny
python3 -m certvic.compute.colab_packager  --job reports_only   --config configs/smoke.yaml              --out-dir compute_bundles/colab_reports_only
```

`--scale N` overrides the default scale; `--no-anonymize` keeps absolute paths
(not recommended). Resume: re-running the commands continues from existing
outputs (generation skips done items, `run_eval` resumes from its JSONL + run
manifest, sharded runs pick up the next incomplete shard), and each session's
outputs should be recorded with `certvic.provenance.run_ledger add`.
