# CertVIC Codex V2 Prompt 11 — Major Paper Scaffold Upgrade

Do not fabricate citations. Do not fabricate results. Do not add fake numbers. Keep RESULT REQUIRED placeholders until real eligible outputs exist.

## Goal

Upgrade the CVPR paper scaffold so the project has a strong paper narrative ready to receive real tables and figures.

## Tasks

1. Upgrade paper sections:
   - `paper/sections/01_intro.tex`
   - `paper/sections/02_related.tex`
   - `paper/sections/03_method.tex`
   - `paper/sections/04_experiments.tex`
   - `paper/sections/05_results.tex`
   - `paper/sections/06_limitations.tex`
   - `paper/sections/07_conclusion.tex`
   - `paper/supp/supplement.tex`

2. Intro must cover:
   - accuracy vs update-under-intervention
   - controlled real-image edits
   - budget-aware evaluation
   - contributions

3. Method must define:
   - source/mask/edit/task pipeline
   - consistency indicator
   - intervention-consistency gap
   - anytime-valid CS
   - claim gate

4. Results section:
   - placeholders only
   - no fake numbers
   - table/figure slots

5. Add figure/table placeholders:
   - pipeline figure
   - edit examples
   - CS trajectory
   - main table
   - failure gallery
   - artifact release diagram

6. Add:
   - `docs/PAPER_CLAIM_CHECKLIST.md`
   - `docs/REVIEWER_ATTACKS_AND_DEFENSES.md`

7. Reviewer attack doc should cover:
   - edits are fake
   - not causal
   - small scale
   - label ambiguity
   - licensing
   - open-only models
   - frontier reference not core
   - optional stopping confusion
   - dataset contribution weakness

8. Add tests:
   - `tests/test_v2_paper_scaffold.py`

9. Create:
   - `docs/V2_PAPER_SCAFFOLD_UPGRADE_REPORT.md`

10. Run:
   - `python3 -m pytest -q`

## Final response

Report files changed, tests run, whether paper upgrade passed, and next prompt: `12_V2_END_TO_END_TINY_REAL_PILOT.md`.
