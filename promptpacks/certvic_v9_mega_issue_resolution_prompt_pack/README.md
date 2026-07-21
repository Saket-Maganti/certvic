# README

# CertVIC V9 Mega Issue-Resolution Prompt Pack

This pack is for the post-V8/V8.1 state where the pipeline is real and audited, but the project is blocked by Qwen failing the spurious specificity gate. V9 is designed to fix the actual scientific blockers instead of adding generic infrastructure.

Primary objective: resolve or honestly reframe the Qwen specificity failure, run stronger controls, prepare/execute Main-500 only after gates permit it, upgrade human validation, compile a claim-safe paper, and produce a CVPR-readiness ledger.

Run order:

1. `00_MASTER_V9_ORIENTATION.md`
2. `01_PRELIM_LABEL_HYGIENE_AND_AUDIT_REPAIR.md`
3. `02_QWEN_FAILURE_HUMAN_REVIEW_PACKET.md`
4. `03_SPURIOUS_V2_STRICT_CONTROL_BUILDER.md`
5. `04_SPURIOUS_V2_T4X2_RUNBOOKS_AND_BUNDLES.md`
6. `05_SPURIOUS_V2_INGEST_GATE_AND_DECISION.md`
7. `06_MODEL_DEPENDENT_SPECIFICITY_REFRAME.md`
8. `07_MAIN500_GO_NOGO_AFTER_SPECIFICITY.md`
9. `08_MAIN500_CPU_PLANNING_AND_ITEM_CERTIFICATES.md`
10. `09_MAIN500_DIFFUSION_T4X2_EXECUTION_PACK.md`
11. `10_MAIN500_QUALITY_DETECTABILITY_AND_REVIEW_EXPORT.md`
12. `11_MAIN500_HUMAN_VALIDATION_AND_IAA.md`
13. `12_MAIN500_VLM_T4X2_EVAL_PACK.md`
14. `13_MAIN500_INGEST_CERTIFICATION_AND_TABLES.md`
15. `14_SECOND_DOMAIN_FEASIBILITY_AND_MINI_RUN.md`
16. `15_MECHANISM_POLARITY_DEEP_ANALYSIS.md`
17. `16_STATISTICAL_INFERENCE_AND_POWER_LOCK.md`
18. `17_FAILURE_TAXONOMY_AND_QUAL_GALLERY_FINAL.md`
19. `18_PAPER_COMPILE_CVPR_SCAFFOLD.md`
20. `19_RELEASE_PRIVACY_REPRODUCIBILITY_PACKAGE.md`
21. `20_REVIEWER_ATTACK_AND_REBUTTAL_SIM.md`
22. `21_CVPR_READINESS_SCORECARD_AND_STOP_CONDITIONS.md`
23. `22_FINAL_VALIDATION_HANDOFF.md`
24. `23_SINGLE_MASTER_PROMPT_RUN_ALL_V9.md`

## Global hard constraints for every V9 prompt

- Repo: `/Users/saketmaganti/Projects/certVIC`.
- Do not fabricate predictions, human labels, results, citations, or paper claims.
- Do not weaken `control_spurious_flip_max <= 0.10`.
- Do not manually delete Qwen failures to force a pass.
- Do not mark `paper_evidence=true` unless an existing, explicit repository policy allows it after real gates pass.
- Do not claim CVPR-ready unless the V9 final audit supports it.
- Do not commit unless explicitly asked.
- Keep all tests CPU/local.
- Heavy model/GPU work must be packaged for Kaggle/free GPU and never simulated locally.
- Any machine/AI triage label must be named `CODEX_PRELIM_*`, never `HUMAN_*`.
- Real human labels must be absent unless a person actually fills a review sheet.
- If a task is blocked, write a BLOCKED artifact with the exact missing file/action.
- Preserve V7/V8 canonical outputs; never destructively overwrite prior results.
- Every prompt must update a V9 task ledger.

## Current state to assume

- V8 ingested all 12 provider/run outputs from `kaggleoutputs/newruns`.
- Main pilot: Qwen2.5-VL-7B, InternVL2-8B, LLaVA-OneVision-7B on 91 reviewed items.
- Spurious specificity gate: Qwen failed with `12/94 = 0.1277`; InternVL passed `1/94`; LLaVA passed `3/94`.
- Detectability: `n_items=94`, AUC about `0.6682`, `artifact_risk=false`.
- Scaled perception: Qwen about `0.897`, InternVL about `0.935`, LLaVA about `0.9322`.
- Polarity and mechanism diagnostics are complete and diagnostic-only.
- V8.1 forensic audit says Qwen failures are Qwen-only; claim-valid recompute scenarios still fail; preliminary labels were machine/AI triage and must not be represented as human review.
- Recommendation before V9: do not start Main-500 until Qwen specificity is resolved or the paper is honestly reframed.
