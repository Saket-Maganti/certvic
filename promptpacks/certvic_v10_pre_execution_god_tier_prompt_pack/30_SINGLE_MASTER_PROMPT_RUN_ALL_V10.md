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

# 30 — Single Master Prompt to Run All V10

Use this controller prompt in Codex:

You are Codex in `/Users/saketmaganti/Projects/certVIC`. Execute the CertVIC V10 Pre-Execution God-Tier Hardening prompt pack from `00_MASTER_V10_ORIENTATION.md` through `29_FINAL_PRE_EXECUTION_VALIDATION.md`, excluding this controller except as context. Run in numeric order, update the V10 ledger after each prompt, create no fake predictions/human labels/results, weaken no gates, execute no Main-500 GPU/human stage, prepare execution-only handoff, run focused tests after major blocks and full tests at the end. If anything is blocked, record exact missing artifact and continue safe prep. Final answer must list files changed, tests/guards, verdict, next exact Kaggle run, and evidence status changes. Start by reading `00_MASTER_V10_ORIENTATION.md`.
