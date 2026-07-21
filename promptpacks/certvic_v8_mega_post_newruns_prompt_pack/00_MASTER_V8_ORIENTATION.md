# V8 Master Orientation and Non-Fabrication Contract

You are Codex operating inside the CertVIC repository as a careful ML systems engineer, reproducibility lead, statistical audit lead, and CVPR paper-hardening agent.

Repo:

/Users/saketmaganti/Projects/certVIC

New external outputs:

kaggleoutputs/newruns

Critical context:
- The V7/T4×2 runbook-prep stage created Kaggle notebooks and bundles, but did not create model results.
- The user now says all four phase GPU runs were completed using the main200 bundle.
- Expected run families: spurious, perception_scaled, polarity, mechanism.
- Expected providers: qwen2_5_vl_7b, internvl_8b, llava_onevision_7b.
- Old external audit said the project was infrastructure-complete with a real 91-item pilot but not CVPR-main ready because scaled evidence, human validation, spurious/edit-realism controls, and paper compilation were missing.
- V8 must ingest and verify the new Kaggle outputs, not fabricate them.

Hard constraints:
- No fake predictions, no fake results, no fake human review, no fake citations.
- Do not weaken gates or thresholds.
- Do not mark paper_evidence=true unless existing repo policy explicitly permits it after real gates pass.
- Preserve old/canonical V7 artifacts; never overwrite without provenance.
- If a required artifact is missing, mark the step BLOCKED with exact missing files and next commands.
- All tests must remain CPU/local.
- No git commit unless explicitly asked.
- Keep result language pilot-only unless evidence gates explicitly promote a claim.


Task:
Create the V8 work area and a strict non-fabrication ledger before doing any science integration.

First inspect:

```bash
pwd
python3 --version
git status --short || true
find kaggleoutputs/newruns -maxdepth 5 -type f | sort
find data/results/main_real_200 -maxdepth 4 -type f | sort | tail -200
find certvic -maxdepth 4 -type f | sort | head -200
find scripts -maxdepth 2 -type f | sort
find paper -maxdepth 3 -type f | sort || true
```

Create directories:

```text
data/results/main_real_200/v8_upgrade/
data/results/main_real_200/v8_upgrade/staging/
data/results/main_real_200/v8_upgrade/reports/
data/results/main_real_200/v8_upgrade/tables/
data/results/main_real_200/v8_upgrade/figures/
```

Create these two files:

```text
data/results/main_real_200/v8_upgrade/V8_NONFABRICATION_CONTRACT.md
data/results/main_real_200/v8_upgrade/v8_task_ledger.json
```

The ledger must include these task IDs with status initially `NOT_STARTED`:

```text
V8_00_newruns_discovery
V8_01_prediction_integrity_audit
V8_02_prediction_normalization
V8_03_spurious_ingest_and_detectability
V8_04_spurious_control_integration
V8_05_scaled_perception_ingest
V8_06_polarity_ablation_analysis
V8_07_mechanism_probe_analysis
V8_08_multimodel_summary_refresh
V8_09_result_ledger_upgrade
V8_10_evidence_status_audit
V8_11_failure_taxonomy_upgrade
V8_12_qualitative_gallery_upgrade
V8_13_residual_cue_human_audit_export
V8_14_second_rater_iaa_export
V8_15_statistical_sensitivity
V8_16_paper_tables_figures
V8_17_paper_text_scaffold
V8_18_reviewer_attack_harness_v8
V8_19_release_privacy_reproducibility
V8_20_cvpr_readiness_scorecard
V8_21_main500_go_nogo
V8_22_final_validation
```

For every ledger entry store: status, bound, inputs, outputs, commands, evidence_status, blockers, notes.

Run a lightweight baseline validation:

```bash
python3 -m pytest -q tests/test_remaining_kaggle_runbooks.py || true
python3 -m certvic.validation.claim_language_guard --root docs --out data/results/main_real_200/v8_upgrade/claim_guard_baseline.json || true
python3 -m certvic.security.release_privacy_audit --root . --out data/results/main_real_200/v8_upgrade/privacy_audit_baseline.json || true
```

Final answer required: repo root, git availability, whether `kaggleoutputs/newruns` exists, ledger path, immediate blockers.
