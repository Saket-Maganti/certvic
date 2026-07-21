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

# 00 — Master Orientation

Purpose: run one more **pre-execution-only** hardening pass before the project switches to actual Kaggle/human execution. Verify the V9 state from real artifacts: V9 validated locally, Qwen failed Spurious V1 specificity, Spurious V2 dataset/runbooks exist, provider predictions are missing, Main-500 is held, and human review packets are blank.

Create `data/results/main_real_200/v10_pre_execution/` with `v10_master_state.json`, `V10_MASTER_STATE.md`, `v10_task_ledger.json`, and `V10_TASK_LEDGER.md`.

Run first:
```bash
cd /Users/saketmaganti/Projects/certVIC
python3 --version
git status --short || true
find data/results/main_real_200/v9_mega_upgrade -maxdepth 3 -type f | sort | tail -200
find data/edits/spurious_v2_control -maxdepth 3 -type f | sort | head -200
find notebooks/kaggle -maxdepth 1 -type f | sort
```

Final response: exact repo state, V9 artifacts found/missing, what V10 will and will not execute, current blockers, and whether any evidence status changed. Expected evidence-status change: none.
