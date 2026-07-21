# CertVIC Codex V5 Prompt Pack — Final CVPR-Readiness Infrastructure Batch

Purpose:
V5 is the final large infrastructure sprint before a full audit and then real empirical runs.

Target:
Make CertVIC as close as possible to a CVPR 2027 main submission **except for the missing real ADE20K/diffusion/VLM results**.

Assumed state:
- V1–V4 complete.
- Tests reported around 451 passing.
- V4 final audit reported 6/6 passing.
- No real GPU/VLM/data runs yet.
- No fake results.
- No paper claims.
- The project is now a run-later machine.

V5 adds the final layers:
- theory/proof appendix infrastructure
- preregistration and analysis-plan hardening
- construct-validity protocol
- human-rater training/calibration
- edit realism rubric
- model card/eval card system
- experiment registry
- result-free paper completion
- reviewer simulation escalation
- statistical robustness audit
- conference-submission packaging
- final “CVPR-ready except results” audit

Hard rules:
- No paid APIs.
- No paid cloud.
- No paid datasets.
- No paid annotation.
- No downloads.
- No GPU/VLM runs.
- No fake numbers.
- No evidence claims.
- No git unless the user asks.
- Heavy deps optional.
- Tests local and CPU-only.

Recommended order:
1. `00_V5_MASTER_CONTEXT.md`
2. Run prompts `01` through `24` in order.
3. Use `25_V5_SINGLE_MASTER_PROMPT.md` only for one-shot execution.
4. After V5, run the audit pack.
