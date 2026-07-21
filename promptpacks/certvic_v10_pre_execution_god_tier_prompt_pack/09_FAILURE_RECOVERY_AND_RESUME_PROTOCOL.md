# CertVIC V10 Pre-Execution God-Tier Hardening Pack

Repo: `/Users/saketmaganti/Projects/certVIC`

You are Codex operating as a careful ML systems engineer, evaluation scientist, reproducibility lead, CVPR paper-hardening agent, and execution-prep auditor.

Hard constraints:
- No fake predictions, fake human labels, fake results, fake citations, or silent evidence promotion.
- Do not weaken specificity, detectability, answerability, privacy, or claim-language gates.
- Do not set `paper_evidence=true` unless an existing explicit repo policy permits it after real evidence gates pass.
- Do not start paid APIs/cloud. Kaggle free GPU only for runbook preparation; this V10 pack is primarily local/CPU pre-execution hardening.
- No git commit unless explicitly asked.
- If a heavy GPU/human step is missing, mark it `BLOCKED_DEFERRED_EXECUTION` with exact next command.
- Preserve V9 result honesty: local V9 is validated, but Spurious V2 predictions, real human labels, Main-500, and second-domain results remain deferred.

# 09 — Failure Recovery and Resume Protocol

Create `docs/runbooks/KAGGLE_FAILURE_RECOVERY_AND_RESUME.md`, `scripts/check_partial_kaggle_run.py`, and tests. Cover: worker crash, shard failure, zip missing but jsonl exists, model download interruption, wrong bundle, missing code bundle, only shard0 uploaded, row mismatch, provider mismatch, slow LLaVA fallback, InternVL memory fallback. Output statuses: COMPLETE_IMPORT_READY, PARTIAL_RECOVERABLE, RERUN_REQUIRED, WRONG_RUN_TAG, WRONG_PROVIDER, STRESS_ONLY_NOT_EVIDENCE.
