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

# README — V10 Pre-Execution God-Tier Hardening Pack

This pack is intentionally pre-execution. It adds one more serious engineering/evaluation layer before real Kaggle/human execution.

Core goal: targeted safeguards so execution cannot go out of order; Spurious V2 candidate expansion; human review ops; IAA; strict importer validation; dashboards; release/paper freeze; Main-500 readiness checks; final execution handoff.

Recommended use: run `30_SINGLE_MASTER_PROMPT_RUN_ALL_V10.md` in Codex, inspect final handoff, then execute Spurious V2 Kaggle runs first.

This pack should not produce new GPU predictions, fake human labels, fake Main-500 evidence, all-model specificity claims, or CVPR-ready claims. Expected final verdict: `EXECUTION_READY_SPURIOUS_V2_FIRST` or a clear blocker.
