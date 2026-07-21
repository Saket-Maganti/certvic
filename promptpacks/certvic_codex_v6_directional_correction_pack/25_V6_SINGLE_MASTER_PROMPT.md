# CertVIC V6 Single Master Prompt — Directional Correction + Final Pre-Run Upgrades

You are working in:

`/Users/saketmaganti/Projects/certVIC`

Project:
CertVIC / Certified Visual Consistency

Target:
CVPR 2027 main submission.

Current state:
- V1–V5 complete.
- Destructive audit complete.
- Four real audit bugs fixed:
  1. certification-policy global-state mutation
  2. paper-number guard bypass
  3. item certificate detectability_status was inert
  4. release-dir text/secret scanning blind spot
- Latest reported tests: 471 passed.
- V5 CVPR-ready-except-results audit passed.
- Claim-language guard passed.
- No real ADE20K/diffusion/VLM evidence yet.
- No paper claims yet.

Strategic correction:
The project must stop looking like "another edited-image VLM benchmark."

Correct identity:
**CertVIC: certified, confound-controlled measurement of visual decision updates in vision-language models.**

Core thesis:
VLMs may be accurate on an original image yet fail to update their answer after a photorealistic, human-validated, single-factor intervention. CertVIC admits intervention pairs as evidence only after item-validity certification and then certifies the decision-update gap under optional stopping.

What matters most:
- item-validity certification is the main methodological moat
- detectability must be measured and controlled
- the certificate must be load-bearing
- the tiny pilot is the existential test
- after V6, run; do not build V7

Hard constraints:
- no git init/commit/tag
- no paid APIs/cloud/datasets/annotation
- no downloads
- no GPU jobs
- no VLM inference
- no fake results
- no fake citations
- no evidence claims
- tests CPU/local

Execute the full V6 directional correction pack in one pass:

1. Paper identity rewrite around certified, confound-controlled decision updates.
2. Item-validity load-bearing analysis.
3. Detectability-first tiny-pilot gate.
4. Staged command safety fix so no wholesale dry-run→GPU→VLM script is encouraged.
5. Main figure/table redesign around detectability vs certified gap.
6. Mechanism probe infrastructure.
7. Intervention-that-moves-the-gap analysis.
8. Open-only evaluation defense.
9. Related-work real citation task scaffold; do not fabricate citations.
10. Formal proof TODO and CS implementation bridge.
11. Tiny-pilot decision dashboard.
12. Validity-gated scoring path.
13. Naive vs validity-gated result story.
14. Edit-family risk matrix.
15. Minimum viable CVPR bar checker.
16. No-more-generic-infrastructure stop condition.
17. Directional claim-language guard against benchmark-only framing.
18. Reviewer attacks for the new direction.
19. Safe result-free abstract/title/contribution variants.
20. Run-after-V6 checklist.
21. Final V6 directional audit.
22. V6 full-pack report and command index.
23. Post-V6 audit prompt.
24. Single-file handoff summary.

Final required outputs:
- `docs/V6_FULL_PACK_REPORT.md`
- `docs/V6_COMMAND_INDEX.md`
- `docs/V6_FINAL_DIRECTIONAL_AUDIT.md`
- `data/results/v6_final_directional_audit.json`
- `docs/V6_FINAL_GO_NO_GO.md`
- `docs/V6_STOP_BUILDING_BEGIN_RUNS.md`
- `docs/RUN_AFTER_V6_CHECKLIST.md`
- `docs/V6_SINGLE_FILE_HANDOFF_SUMMARY.md`

Required final verification:
- `python3 -m pytest -q`
- `python3 -m certvic.v6.final_directional_audit --out docs/V6_FINAL_DIRECTIONAL_AUDIT.md --json-out data/results/v6_final_directional_audit.json`
- claim-language/directional language guards, if implemented
- all command safety tests

Final response:
A. What changed strategically
B. Files/modules/docs added
C. Tests run and result
D. V6 audit result
E. Whether empirical runs may begin
F. Exact next commands
G. What number decides whether the paper is real: tiny-pilot edit detectability AUC
