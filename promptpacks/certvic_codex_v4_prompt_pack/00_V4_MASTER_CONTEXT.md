# CertVIC Codex V4 Prompt 00 — Master Context

You are working in:

`/Users/saketmaganti/Projects/certVIC`

Project: **CertVIC / Certified Visual Consistency**
Target: **CVPR 2027 main submission**
Working title: **“Certifying When Vision-Language Models See the Change: Anytime-Valid Consistency Under Controlled Real-Image Interventions”**

## Assumed state

V1–V3 are complete. The latest reported state:
- test suite around 434 passing
- V3 final pre-real-run audit passes 13/13
- V2 audits still pass
- V3 code ruff-clean
- no real empirical evidence yet
- no paid services, no downloads, no GPU/VLM runs in tests, no fake numbers

## Why V4 exists

The user has coding/assistant limits expiring soon. They want to build as much **run-later infrastructure** as possible now, so later they can mostly execute runs.

V4 should not tell the user to stop. Build helpful systems that reduce future execution pain.

## V4 design principle

Build only things that help after credits expire:
- one-command real-run command generation
- Kaggle/Colab notebooks generated from configs
- offline model cache manifests
- fallback dataset adapters
- run recovery/repair tools
- prediction merging/deduplication
- multi-model comparisons
- statistical sensitivity reporting
- qualitative figure assembly
- LaTeX/supplement infrastructure
- result freezing and lockfiles
- CVPR checklist/deadline machinery
- troubleshooting assistants
- final all-system audit

## Hard constraints

Do not:
- initialize git
- create commits or tags
- use paid services
- download datasets/model weights
- run GPU jobs
- run VLM inference in tests
- fabricate results
- insert fake numbers into paper
- make evidence claims from synthetic/simulated/pre-run artifacts

Do:
- inspect existing modules before editing
- preserve backward compatibility
- add tests
- add docs
- add CLI commands
- keep heavy imports lazy
- keep planned/simulated artifacts non-evidence
- run `python3 -m pytest -q`
- produce handoff docs

## Final V4 success criterion

After V4, a future no-assistant version of the user can execute:
1. real ADE20K dry-run
2. tiny diffusion edit pilot
3. human review
4. open-VLM matrix
5. scoring/certification
6. paper update
7. artifact release

using generated commands, notebooks, audits, dashboards, and troubleshooting docs.
