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

# 05 — Unified Output Importer and Validator

Build `scripts/validate_and_import_kaggle_outputs.py`, `certvic/v10/kaggle_output_validation.py`, and tests. Support spurious_v2, main500_diffusion, main500_vlm, second_domain_mini, and stress_test. Validate provider/run_tag, row counts, JSONL, duplicate IDs, shard consistency, merged file, internal provider fields, no weights/cache in zip, runtime manifests, sha256 ledger, and overwrite refusal unless same hash.
