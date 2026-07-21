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

# 01 — Execution State Graph and Gate Ledger

Build a formal execution graph so the next phase cannot run out of order. Create `execution_state_graph.json`, `EXECUTION_STATE_GRAPH.md`, `gate_status_matrix.csv`, and `GATE_STATUS_MATRIX.md` under `v10_pre_execution`.

Nodes: Spurious V1, V8/V8.1 forensics, V9 label hygiene, Qwen failed-12 human review, Spurious V2 build, Spurious V2 Kaggle predictions per provider, Spurious V2 ingest/gate, model-dependent specificity branch, Main-500 planning/diffusion/quality/human/VLM, second-domain mini-run, release/paper compile.

Each node needs status, evidence_status, predecessors, blocker, command/notebook/runbook, outputs, and can_run_now. Main-500 must depend on Spurious V2 decision or explicit model-dependent signoff. Add tests for acyclic graph and no DONE node without artifacts.
