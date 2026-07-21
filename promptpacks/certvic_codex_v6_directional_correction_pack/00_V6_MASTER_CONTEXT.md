# CertVIC V6 Prompt 00 — Master Context and Directional Correction

You are working in:

`/Users/saketmaganti/Projects/certVIC`

Project:
CertVIC / Certified Visual Consistency

Target:
CVPR 2027 main submission.

Current strategic diagnosis:
The project does not mainly have a framing problem. It has a "five versions of infrastructure and zero data" problem.
Still, the framing must be corrected before runs so that the paper does not become "yet another VLM edited-image benchmark."

The correct identity:

**CertVIC: certified, confound-controlled measurement of visual decision updates in vision-language models.**

Working title:
`CertVIC: Certified, Confound-Controlled Measurement of Visual Decision Updates in Vision-Language Models`

Alternative title:
`CertVIC: Anytime-Valid Certification of Confound-Controlled Visual Decision Updates`

Core question:
Do VLMs update their decisions when the visual world changes?

Core thesis:
VLMs can be accurate on an original image yet fail to update their answer after a photorealistic, human-validated, single-factor visual intervention. CertVIC admits an intervention pair as evidence only after validity certification and then certifies the decision-update gap under optional stopping.

The real methodological moat:
- Item-validity certificates are more novel than merely reporting confidence sequences.
- The certificate must be load-bearing: it must visibly affect which items are evidence and how the measured gap changes.
- Detectability must be measured and controlled. If edits are trivially detectable, the paper dies.

V6 goal:
Build final directional corrections and upgrades that make the tiny pilot decisive:
- paper identity rewrite
- item-validity certificate load-bearing analysis
- detectability-first pilot gate
- validity-gated gap analysis
- mechanism/intervention probes
- staged command execution
- open-only model defense
- paper figure/table redesign
- exact go/no-go thresholds
- final pre-run audit

Non-negotiables:
- Do not run real GPU jobs.
- Do not run VLM inference.
- Do not download data or weights.
- Do not fabricate citations or numbers.
- Do not make evidence claims.
- Do not build generic V7 infrastructure.
- Only build things that directly support the new direction and the imminent pilot.

Every prompt must end by reporting:
- files changed
- tests added/updated
- commands added
- docs added
- whether prompt passed
- next prompt
