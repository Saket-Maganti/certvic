# V9 Master Orientation and Ledger Bootstrap

You are Codex acting as a strict CertVIC V9 project lead, ML systems engineer, evidence auditor, statistician, and CVPR paper hardening agent.

## Global hard constraints for every V9 prompt

- Repo: `/Users/saketmaganti/Projects/certVIC`.
- Do not fabricate predictions, human labels, results, citations, or paper claims.
- Do not weaken `control_spurious_flip_max <= 0.10`.
- Do not manually delete Qwen failures to force a pass.
- Do not mark `paper_evidence=true` unless an existing, explicit repository policy allows it after real gates pass.
- Do not claim CVPR-ready unless the V9 final audit supports it.
- Do not commit unless explicitly asked.
- Keep all tests CPU/local.
- Heavy model/GPU work must be packaged for Kaggle/free GPU and never simulated locally.
- Any machine/AI triage label must be named `CODEX_PRELIM_*`, never `HUMAN_*`.
- Real human labels must be absent unless a person actually fills a review sheet.
- If a task is blocked, write a BLOCKED artifact with the exact missing file/action.
- Preserve V7/V8 canonical outputs; never destructively overwrite prior results.
- Every prompt must update a V9 task ledger.

## Current state to assume

- V8 ingested all 12 provider/run outputs from `kaggleoutputs/newruns`.
- Main pilot: Qwen2.5-VL-7B, InternVL2-8B, LLaVA-OneVision-7B on 91 reviewed items.
- Spurious specificity gate: Qwen failed with `12/94 = 0.1277`; InternVL passed `1/94`; LLaVA passed `3/94`.
- Detectability: `n_items=94`, AUC about `0.6682`, `artifact_risk=false`.
- Scaled perception: Qwen about `0.897`, InternVL about `0.935`, LLaVA about `0.9322`.
- Polarity and mechanism diagnostics are complete and diagnostic-only.
- V8.1 forensic audit says Qwen failures are Qwen-only; claim-valid recompute scenarios still fail; preliminary labels were machine/AI triage and must not be represented as human review.
- Recommendation before V9: do not start Main-500 until Qwen specificity is resolved or the paper is honestly reframed.

## Mission

Build and execute the V9 upgrade plan that resolves the actual blockers:

1. Repair any misleading V8.1 naming such as `HUMAN_PRELIMINARY_EVAL` when labels were not created by humans.
2. Create a real human-review packet for the 12 Qwen spurious failures.
3. Build and run a stricter Spurious V2 control before Main-500.
4. Decide whether Qwen can pass a stricter specificity gate or must be reframed as model-specific instability.
5. Only after specificity is resolved or honestly reframed, prepare Main-500 execution.
6. Add real human answerability / residual-cue / IAA workflows.
7. Upgrade paper, tables, figures, release package, reviewer attack harness, and CVPR readiness.

## First commands

```bash
cd /Users/saketmaganti/Projects/certVIC
pwd
python3 --version
git status --short || true
find data/results/main_real_200 -maxdepth 5 -type f | sort | tail -300
find data/results/main_real_200/v8_1_qwen_spurious_forensics -maxdepth 4 -type f | sort || true
find data/results/main_real_200/v8_upgrade -maxdepth 4 -type f | sort || true
find kaggleoutputs/newruns -maxdepth 4 -type f | sort || true
find docs/runbooks paper commands tests scripts certvic -maxdepth 3 -type f | sort | head -300
```

## Create V9 root

Create:

```text
data/results/main_real_200/v9_mega_upgrade/
```

Create a ledger:

```text
data/results/main_real_200/v9_mega_upgrade/v9_task_ledger.json
data/results/main_real_200/v9_mega_upgrade/V9_TASK_LEDGER.md
```

Every V9 prompt must write a task record with:

- task_id
- prompt_file
- status: DONE / BLOCKED / PARTIAL / NOT_APPLICABLE
- command(s) run
- input files
- output files
- evidence_status
- result summary
- blockers
- next action

## V9 task IDs

Use these IDs exactly:

```text
V9_00_orientation
V9_01_prelim_label_hygiene
V9_02_qwen_failure_human_review_packet
V9_03_spurious_v2_builder
V9_04_spurious_v2_t4x2_runbooks
V9_05_spurious_v2_ingest_gate_decision
V9_06_model_dependent_reframe
V9_07_main500_go_nogo
V9_08_main500_cpu_planning
V9_09_main500_diffusion_pack
V9_10_main500_quality_review_export
V9_11_main500_human_validation_iaa
V9_12_main500_vlm_eval_pack
V9_13_main500_ingest_certification
V9_14_second_domain_mini_run
V9_15_mechanism_polarity_deep_analysis
V9_16_statistical_inference_power_lock
V9_17_failure_taxonomy_gallery_final
V9_18_paper_compile_cvpr_scaffold
V9_19_release_privacy_reproducibility
V9_20_reviewer_attack_rebuttal_sim
V9_21_cvpr_readiness_stop_conditions
V9_22_final_validation_handoff
```

## Required output for this prompt

Create:

```text
data/results/main_real_200/v9_mega_upgrade/V9_MASTER_STATE.md
data/results/main_real_200/v9_mega_upgrade/v9_master_state.json
```

The state file must summarize:

- current real evidence
- current blockers
- what must not be claimed
- exact next prompt to run
- why Main-500 remains blocked unless V9 says otherwise

Run:

```bash
python3 -m pytest -q tests/test_v8_1_qwen_spurious_forensics.py || true
python3 -m pytest -q tests/test_v8_upgrade.py || true
```

Do not modify scientific results in this prompt.
