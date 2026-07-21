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

# 02 — Spurious V2 Large Candidate Expansion

V9 strict Spurious V2 found only 30 feasible controls. Try to expand a stricter **candidate** pool locally without weakening quality. Implement `scripts/build_spurious_v2_large_candidates.py`, `certvic/v10/spurious_v2_large_quality.py`, `commands/spurious_v2_large/build_candidates.sh`, and `SPURIOUS_V2_LARGE_CANDIDATE_REPORT.md`.

Search existing spurious V1, ADE20K train/validation if available, and eligible CertVIC object classes. Constraints: target mask untouched, object-region pixel diff near zero, patch bbox not intersecting target bbox, documented distance threshold, lower salience if possible, balanced classes, no cherry-picking from model outputs. Target 150–300 if feasible; otherwise maximum feasible with exact reason. No VLM results.
