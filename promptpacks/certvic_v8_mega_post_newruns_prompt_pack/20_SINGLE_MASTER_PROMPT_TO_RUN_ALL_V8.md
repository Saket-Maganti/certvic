# Single Master Prompt to Run All V8

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
Run the complete V8 Mega Post-NewRuns integration sequence end to end. Use this only if you want one large agent run; individual prompts are safer.

Sequence:
1. Create V8 work area and non-fabrication contract.
2. Inventory `kaggleoutputs/newruns`.
3. Validate all prediction JSONLs and archives.
4. Normalize the 12 expected prediction files into canonical result folders.
5. Run spurious ingestion for all three providers.
6. Run spurious edit detectability/quality gate.
7. Run `certvic.v7.spurious_control_integration`.
8. Ingest scaled perception predictions for all three providers.
9. Analyze prompt polarity predictions for all three providers.
10. Analyze mechanism probe predictions for all three providers.
11. Refresh multimodel summary and create V8 result ledger.
12. Audit evidence status and certification policy.
13. Upgrade failure taxonomy and qualitative gallery.
14. Export residual-cue human audit sheet.
15. Export or compute second-rater IAA depending on whether labels exist.
16. Refresh statistical sensitivity.
17. Generate paper tables, figures, and claim-safe section scaffolds.
18. Run V8 reviewer attack harness.
19. Run release/privacy/reproducibility audit.
20. Decide Main-500 GO/NO-GO.
21. Refresh Main-500 runbooks if appropriate.
22. Produce CVPR readiness scorecard.
23. Run final validation and handoff.

Mandatory behavior:
- At every step, if inputs are missing, mark BLOCKED and continue to later independent diagnostics where possible.
- Do not fabricate missing predictions/human labels/results.
- Do not overwrite V7 canonical results without provenance.
- Do not promote paper_evidence unless repo policy explicitly allows it.
- Keep all metrics traceable to raw JSONL hashes.

Expected canonical prediction files:

```text
# Spurious
data/results/main_real_200/kaggle_spurious/pred_qwen2_5_vl_7b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_internvl_8b_spurious_merged.jsonl
data/results/main_real_200/kaggle_spurious/pred_llava_onevision_7b_spurious_merged.jsonl

# Scaled perception
data/results/main_real_200/kaggle_perception_scaled/pred_qwen2_5_vl_7b_perception_scaled_merged.jsonl
data/results/main_real_200/kaggle_perception_scaled/pred_internvl_8b_perception_scaled_merged.jsonl
data/results/main_real_200/kaggle_perception_scaled/pred_llava_onevision_7b_perception_scaled_merged.jsonl

# Polarity
data/results/main_real_200/kaggle_polarity/pred_qwen2_5_vl_7b_polarity.jsonl
data/results/main_real_200/kaggle_polarity/pred_internvl_8b_polarity.jsonl
data/results/main_real_200/kaggle_polarity/pred_llava_onevision_7b_polarity.jsonl

# Mechanism
data/results/main_real_200/kaggle_mechanism/pred_qwen2_5_vl_7b_mechanism.jsonl
data/results/main_real_200/kaggle_mechanism/pred_internvl_8b_mechanism.jsonl
data/results/main_real_200/kaggle_mechanism/pred_llava_onevision_7b_mechanism.jsonl
```

Final outputs:

```text
data/results/main_real_200/v8_upgrade/V8_FINAL_HANDOFF.md
data/results/main_real_200/v8_upgrade/v8_final_handoff.json
data/results/main_real_200/v8_upgrade/CVPR_READINESS_SCORECARD_V8.md
data/results/main_real_200/v8_upgrade/cvpr_readiness_scorecard_v8.json
data/results/main_real_200/v8_upgrade/V8_TASK_LEDGER.md
data/results/main_real_200/v8_upgrade/v8_task_ledger.json
```

Final response required:
- Real V8 results integrated.
- Blockers remaining.
- CVPR readiness level.
- Exact next action.
- Tests and guard status.
