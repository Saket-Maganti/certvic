# CertVIC Codex V6 Prompt Pack — Directional Correction + Final Pre-Run Upgrades

Purpose:
V6 is the final directional-correction pack before empirical execution.

The goal is not generic infrastructure. The goal is to steer CertVIC away from
"yet another VLM edited-image benchmark" and into:

**Certified, confound-controlled measurement of visual decision updates in VLMs.**

Core correction:
- The paper is not a benchmark paper.
- The paper is not a dataset paper.
- The paper is not "VLMs are inconsistent."
- The paper is a validity-and-inference protocol for deciding when an edited real-image pair is admissible evidence and then certifying whether VLMs update their decisions.

Assumed current state:
- V1–V5 infrastructure complete.
- Destructive audit completed.
- Four bugs fixed:
  1. certification-policy global-state mutation
  2. paper-number guard bypass
  3. detectability_status was inert in item certificates
  4. release-dir text/secret scan blind spot
- Full tests reported: 471 passed.
- V5 CVPR-ready-except-results audit passed.
- Claim-language guard passed.
- No real ADE20K/diffusion/VLM evidence yet.

V6 mission:
1. Rewrite the paper identity around confound-controlled decision updates.
2. Make item-validity certification load-bearing.
3. Make detectability-first tiny pilot the next existential gate.
4. Add mechanism/intervention infrastructure.
5. Strengthen open-model-only defense.
6. Fix command staging so no one runs dry-run→GPU→VLM wholesale.
7. Build the exact analysis needed to prove CertVIC is not just a benchmark.
8. Stop after V6 and run.

Hard rules:
- No paid APIs.
- No paid cloud.
- No paid datasets.
- No paid annotation.
- No downloads.
- No GPU/VLM runs in tests.
- No fake numbers.
- No fake citations.
- No evidence claims from mock/simulated/smoke/planned/unreviewed/simple-edit-only artifacts.
- Do not initialize git, commit, or tag unless explicitly asked.
- Heavy deps optional/import-safe.
- Tests CPU/local.

Recommended order:
Run prompts 00 through 24 in order, or use `25_V6_SINGLE_MASTER_PROMPT.md`.

After V6:
Run the ADE20K dry-run, then the 20-edit diffusion pilot, then edit detectability.
