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

# 03 — Spurious V2 Pre-Human Review and Quality Dashboard

Create a visual pre-human review dashboard for Spurious V2/V2-large candidates. Create review CSV, gallery HTML, instructions, `scripts/apply_v10_spurious_v2_review.py`, and an apply report. Columns include item_id, object_class, original/control paths, patch bbox, target bbox, bbox distance, mask overlap, patch salience score, approve_control blank, reject_reason blank, notes blank. Apply script refuses blank/partial labels and never treats machine labels as human labels.
