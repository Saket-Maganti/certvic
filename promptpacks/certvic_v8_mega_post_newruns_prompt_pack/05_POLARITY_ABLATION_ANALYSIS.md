# V8 Prompt Polarity Ablation Analysis

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
Analyze V8 prompt-polarity predictions from data/results/main_real_200/kaggle_polarity for all three providers. Inspect schema and existing certvic.reporting.ablations / certvic.eval.run_ablations CLIs. If they do not fit the flat V8 probe schema, create certvic/v8/polarity_ablation_report.py. Verify 728 rows/provider, group by positive/negative/short/pixel_only, compute parse rates, answer distributions, correctness/consistency if gold is recoverable, and create POLARITY_ABLATION_REPORT.md/json plus v8_polarity_ablation_summary.csv. Do not invent gold labels. Update V8_06.

Never fabricate missing outputs; mark BLOCKED with exact missing files. Update the V8 task ledger. Final answer must list inputs used, outputs created, commands run, tests/guards, and remaining blockers.
