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

# 07 — T4x2 Notebook Self-Test Suite

Create a CPU-only validator that catches unsupported diagnostic formats, broken indentation from hotfixing, missing code bundle detection, and bad shard outputs. Create `scripts/validate_t4x2_notebooks.py`, tests, and a report. Check nbformat, syntax of worker code cells, CUDA_VISIBLE_DEVICES, shard0/shard1, merge validation, single-GPU fallback, freeform mechanism parser for `object_list` and `describe_then_yes_no`, strict spurious/perception parsing, no private paths, no fake fixtures.
