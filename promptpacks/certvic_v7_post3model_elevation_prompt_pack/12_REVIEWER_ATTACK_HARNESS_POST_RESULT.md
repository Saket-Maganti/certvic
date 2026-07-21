# 12 — Post-Result Reviewer Attack Harness

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
Now that the result is real, the project needs an adversarial reviewer audit focused on the actual finding.

## Task
Build or update a reviewer attack harness that enumerates likely CVPR objections and checks whether current artifacts answer them.

## Create/update
- `docs/POST_RESULT_REVIEWER_ATTACKS.md`
- `data/results/post_result_reviewer_attack_audit.json`
- `certvic/audit/post_result_reviewer_attack_audit.py` or equivalent

## Attacks to include
1. “Models simply do not perceive the object.”
2. “The question presupposes the object.”
3. “The edited images have residual artifacts.”
4. “Models are sticky under any perturbation.”
5. “Only one dataset.”
6. “Only one reviewer.”
7. “n=91 is too small.”
8. “Prompt polarity caused the effect.”
9. “The result is not reproduced across models.”
10. “The statistics are optional-stopping hacked.”
11. “Old reports are mock-labeled.”
12. “The benchmark is just another edited-image dataset.”

## For each attack
Report:
- status: answered / partially_answered / unanswered / blocked
- artifact evidence
- remaining action
- severity

## Hard rules
- Be harsh.
- Do not downgrade a blocker just to look good.
- Missing evidence must be marked missing.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give top 5 unresolved reviewer attacks and next actions.
