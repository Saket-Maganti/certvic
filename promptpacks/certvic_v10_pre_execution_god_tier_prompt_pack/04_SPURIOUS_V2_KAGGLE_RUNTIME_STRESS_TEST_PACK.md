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

# 04 — Spurious V2 Kaggle Runtime Stress-Test Pack

Create tiny non-evidence stress-test notebooks/cells to validate Kaggle setup, paths, T4x2 sharding, model loading, and output packaging on 2–4 pairs. Create provider stress notebooks, `certvic_spurious_v2_stress_bundle.zip`, and a runbook. Mark all stress outputs `NON_EVIDENCE_STRESS_TEST`. Tests must ensure stress outputs cannot satisfy the Spurious V2 importer.
