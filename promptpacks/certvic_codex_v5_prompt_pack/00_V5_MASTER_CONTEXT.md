# CertVIC V5 Prompt 00 — Master Context

You are working in:

`/Users/saketmaganti/Projects/certVIC`

Project:
CertVIC / Certified Visual Consistency

Target:
CVPR 2027 main submission.

Current status:
V1 through V4 are reported complete. V4 added final run-later infrastructure:
- real-run command bundles
- generated notebooks
- model-cache manifests
- fallback datasets
- CC0 showcase packaging
- edit sweep planning
- static review app
- recovery/repair
- prediction merge/dedup
- model comparison
- statistical sensitivity
- qualitative figures
- LaTeX/supplement tooling
- reproducibility capsule validation
- result lockfiles
- submission planning
- troubleshooting
- reviewer QC
- ablation planning
- internal review packet
- final V4 audit

Reported latest verification:
- around 451 tests passing
- V4 final audit 6/6 passing
- no GPU/VLM/data jobs executed
- no fake claims/results

## V5 mission

Build the last major infrastructure layer so the project is **CVPR-ready except for actual runs/results**.

V5 should prepare:
- paper theory and proof appendix
- preregistered analysis plan
- item validity certificate
- human rater calibration
- model/eval cards
- experiment registry
- paper skeleton that is complete except result values
- rebuttal and reviewer simulation
- final result-free submission package
- final V5 audit

## Non-negotiables

Do not:
- initialize git
- commit/tag
- use paid APIs
- use paid cloud
- use paid datasets
- download datasets/weights
- run GPU jobs
- run VLM inference
- fabricate results
- insert fake paper numbers
- claim evidence from planned/simulated/mock artifacts

Do:
- preserve backward compatibility
- inspect existing modules first
- add tests
- add docs
- add CLIs where useful
- keep heavy imports lazy
- mark planned/simulated artifacts non-evidence
- run `python3 -m pytest -q`
- update V5 command index and reports

## Final V5 standard

After V5, the repo should be able to withstand a harsh internal audit asking:

“Is this basically ready for CVPR once the real result tables/figures are generated?”

The answer should be yes, with only empirical artifacts missing.
