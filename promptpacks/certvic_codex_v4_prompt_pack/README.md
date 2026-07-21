# CertVIC Codex V4 Prompt Pack

Generated for a final infrastructure sprint before assistant/coding limits expire.

V4 assumes V1–V3 are complete, including:
- V2.7 pre-run hardening
- native anytime-valid CS fallback
- reviewer harness
- paper number guard
- V3 run ledger, storage planner, Kaggle/Colab bundles, diffusion queue, detectability probe, cluster diagnostics, human review ops, model matrix, output triage, scale planner, dashboard, paper injection, related work audit, reviewer simulation, dockerless reproduction, security audit, playbooks, main study dry-run, and final V3 audit.

V4 purpose:
Build **execution-after-credits-expire infrastructure**. After this pack, the user should mostly execute runs, not request more code.

Hard constraints:
- No git init/commit/tag unless user explicitly asks.
- No paid APIs, paid cloud, paid datasets, paid annotation, paid credits.
- No downloads of real datasets or model weights.
- No GPU jobs in tests.
- No VLM inference in tests.
- No fabricated results or paper claims.
- Heavy imports optional/lazy.
- Tests local CPU only.
- Simulated/planned artifacts must be non-evidence.

Recommended order:
1. `00_V4_MASTER_CONTEXT.md`
2. `01_V4_REAL_RUN_COMMAND_GENERATOR.md`
3. `02_V4_KAGGLE_NOTEBOOK_AUTOGENERATOR.md`
4. `03_V4_COLAB_NOTEBOOK_AUTOGENERATOR.md`
5. `04_V4_OFFLINE_MODEL_CACHE_MANIFESTS.md`
6. `05_V4_DATASET_FALLBACK_ADAPTERS.md`
7. `06_V4_CC0_SHOWCASE_SPLIT.md`
8. `07_V4_EDIT_ENGINE_PARAMETER_SWEEP_PLANNER.md`
9. `08_V4_VISUAL_QA_REVIEW_APP_STATIC.md`
10. `09_V4_REAL_RUN_RECOVERY_AND_REPAIR.md`
11. `10_V4_PREDICTION_MERGE_AND_DEDUP.md`
12. `11_V4_MULTI_MODEL_COMPARISON_SUITE.md`
13. `12_V4_STATISTICAL_SENSITIVITY_SUITE.md`
14. `13_V4_QUALITATIVE_FIGURE_BUILDER.md`
15. `14_V4_LATEX_CAMERA_READY_INFRASTRUCTURE.md`
16. `15_V4_SUPPLEMENT_AUTOGENERATOR.md`
17. `16_V4_REPRODUCIBILITY_CAPSULE_VALIDATOR.md`
18. `17_V4_RESULT_FREEZE_AND_LOCKFILE.md`
19. `18_V4_SUBMISSION_CHECKLIST_AND_DEADLINE_MANAGER.md`
20. `19_V4_RUNBOOK_TROUBLESHOOTING_ASSISTANT.md`
21. `20_V4_DATASET_LICENSE_EXPANSION.md`
22. `21_V4_HUMAN_REVIEW_QUALITY_CONTROL_PLUS.md`
23. `22_V4_REALISTIC_PAPER_ABLATION_PLANNER.md`
24. `23_V4_FINAL_CVPR_INTERNAL_REVIEW_PACKET.md`
25. `24_V4_FINAL_ALL_SYSTEM_AUDIT.md`

Optional one-shot:
- `25_V4_SINGLE_MASTER_PROMPT.md`

After V4, stop building unless an actual real run exposes a concrete missing gate.
