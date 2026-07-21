# 00A: code and environment smoke

Inputs are the portable code bundle, offline wheelhouse, environment lock, and generated 00A config.
Use a fresh Kaggle session with internet off; GPU is optional for this phase. Expected duration is
10–20 minutes.

Open `notebooks/kaggle/cvpr/00A_certvic_code_and_environment_smoke.ipynb`, paste the generated config,
attach only the declared datasets, and run all cells once. Download these exact outputs without
renaming or editing:

- `00A_environment.json`
- `00A_environment_validation.json`
- `00A_environment_bundle.zip`

Validation requires exact package versions, import probes, environment hash agreement, offline mode,
and `passed=true`. Put unchanged files in `data/runtime/` and run
`python3 -m certvic.cvpr.doctor --json`; the expected state is `READY_FOR_00B`.

On failure, preserve all logs, start a new session with the same code and wheel bytes, and fix only the
provisioning defect. Do not change model prompts, parser rules, study thresholds, or evidence flags.

