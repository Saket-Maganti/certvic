
# CertVIC Execution Realization Handoff

Verdict: `PARTIALLY_READY_WITH_BLOCKERS`; `paper_evidence=false`.

Start from the root `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`, then run the non-evidence smoke sequence:
00A once; 00B for Qwen, InternVL, and LLaVA; 00C with exactly two fixtures for each provider. Freeze
the six 40-character revisions and three snapshot-manifest hashes only after those pass. Then provision
and hash ADE20K, run outcome-blind candidate selection, generate deterministic controls, and complete
two-rater review/adjudication. Only after the final 240-task manifest is hash-locked may the three
confirmatory notebooks run. Return all three ZIPs together for atomic import.

Main remains blocked. V2-30 remains retrospective sensitivity only. Frozen V1 observations remain
Qwen 12/94, InternVL 1/94, and LLaVA 3/94; no result in this pass modifies them. Human sheets are blank,
no real GPU output exists, and smoke artifacts are `NON_EVIDENCE_RUNTIME_SMOKE`.

External blockers: source archives/license sign-off, real immutable model/processor snapshots and
commits, Kaggle T4 environment/model smoke, two distinct qualified reviewers plus adjudicator, and all
scientific runs. The exact next action is to build the code ZIP, attach it to Kaggle, and run 00A without
altering scientific configs or evidence directories.
