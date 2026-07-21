# 01 — Canonical Artifact Lock and Result Ledger

You are Claude Opus acting as a senior CVPR research advisor, ML systems engineer, statistician, VLM evaluation scientist, reproducibility lead, and adversarial reviewer.

Repo:
/Users/saketmaganti/Projects/certVIC

Project:
CertVIC — Certified, Confound-Controlled Measurement of Visual Decision Updates in Vision-Language Models.

Hard constraints:
- No paid APIs.
- No paid cloud GPUs.
- No paid datasets.
- No paid annotation.
- No paid credits.
- Use local Mac/M4 CPU, Kaggle free GPU, Colab free fallback, public/free datasets, and open-source models only.
- No fake results, fake citations, or paper numbers not backed by real artifacts.
- No evidence claims from mock/smoke/synthetic/planned/unreviewed/simple-edit-only artifacts.
- Keep tests CPU/local.
- Heavy dependencies must be optional/import-safe.
- Do not weaken quality, detectability, evidence, leakage, claim, or paper-number gates.
- Do not initialize, commit, or tag unless explicitly asked.
- Keep all current results explicitly pilot-only unless the repo's evidence gates say otherwise.

Current real pilot facts to preserve:
- Same 91 reviewed presence/intervention items.
- Same 120 absent-object control items.
- Same protocol across Qwen2.5-VL-7B, InternVL2-8B, and LLaVA-OneVision-7B.
- Qwen2.5-VL-7B: a=0.923, p=0.176, Delta=0.747, CS lower bound=0.364, certified=true, absent control 60/60, present control 50/60.
- InternVL2-8B: a=0.923, p=0.099, Delta=0.824, CS lower bound=0.441, certified=true, absent control 58/60, present control 58/60.
- LLaVA-OneVision-7B: a=0.890, p=0.176, Delta=0.714, CS lower bound=0.331, certified=true, absent control 60/60, present control 58/60.
- The scientific core: open VLMs can detect natural absence, but often fail to revise after controlled low-detectability removals/edits.
- Current status: strong pilot, not paper-grade yet.
- Claude is already working separately on the spurious-flip/control_irrelevant arm. Do not duplicate that work; integrate its outputs only after they exist.

Before coding:
- Inspect existing files and commands.
- Reuse existing infrastructure.
- Do not invent paths.
- Explain briefly what you will do, then execute.

After coding:
- Run relevant CPU tests.
- Run security/privacy/claim guards if docs/results/reporting changed.
- Give exact commands and artifact paths.

## Motivation
The real pilot result is now valuable. It must be impossible to accidentally cite stale, mock-labeled, or non-canonical artifacts.

## Task
Build a canonical result ledger that maps every pilot number to the exact source artifact, hash, generation command, model, provider, task file, prediction file, scoring file, and report file.

Do not recompute numbers unless needed for verification. Do not alter the numbers.

## Create/update
- `registry/results/main200_pilot_result_ledger.json`
- `registry/results/main200_pilot_result_ledger.md`
- `certvic/audit/result_ledger_audit.py` or equivalent CLI if no such audit exists
- tests for ledger integrity

## Ledger fields
Each row/item must include:
- result_id
- model/provider/run_label
- task_set: presence or absent_control
- task_file path + sha256
- raw prediction path + sha256
- scoring artifact paths + sha256
- metric values if applicable
- evidence_status
- claim_level: pilot_only / evidence_candidate / blocked
- generated_by command or notebook
- timestamp if present in artifacts
- caveats

## Hard gates
The audit must fail if:
- a number appears without an artifact path;
- an artifact path does not exist;
- a hash mismatches;
- a row cites `final_report/` or `final_report_v2/` as canonical;
- InternVL/LLaVA rows are populated from Qwen files;
- any mock/smoke artifact is marked claim-eligible.

## Validation
Run:
```bash
python3 -m pytest -q
python3 -m certvic.audit.result_ledger_audit --ledger registry/results/main200_pilot_result_ledger.json
```

## Final response
Report files changed, commands run, pass/fail status, and any non-canonical artifact warnings.
