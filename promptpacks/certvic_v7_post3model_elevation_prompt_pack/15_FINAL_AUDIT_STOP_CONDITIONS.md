# 15 — Final Audit and Stop Conditions

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
The project must avoid endless infrastructure work. This audit defines when to stop building and run/scale, and when to stop scaling and write.

## Task
Create a post-3-model final audit with explicit stop conditions.

## Create/update
- `docs/V7_POST3MODEL_FINAL_AUDIT.md`
- `data/results/v7_post3model_final_audit.json`
- `certvic/audit/v7_post3model_final_audit.py` or equivalent

## Audit categories
1. Canonical result artifacts
2. Multi-model replication
3. Control status
4. Human review/IAA status
5. Scale readiness
6. Second-domain readiness
7. Mechanism probes
8. Statistical validity
9. Paper/report language
10. Release/privacy/security

## Stop/build policy
Mark each proposed future task as:
- RUN_NOW
- WRITE_NOW
- BUILD_ONLY_IF_BLOCKED
- DO_NOT_DO

Likely policy:
- More generic infra: DO_NOT_DO
- Spurious control integration: RUN_NOW/BUILD_IF_OUTPUTS_EXIST
- More models after 3: BUILD_ONLY_IF reviewer need
- Scale to 500/800+: RUN_NOW after controls pass
- Paper pilot section: WRITE_NOW

## Hard rules
- Be harsh.
- Missing blockers must stay blockers.
- Do not mark paper-grade readiness unless scale/control/review gates pass.

## Validation
Run:
```bash
python3 -m pytest -q
```

## Final response
Give a stop/go table and the one next highest-leverage action.
