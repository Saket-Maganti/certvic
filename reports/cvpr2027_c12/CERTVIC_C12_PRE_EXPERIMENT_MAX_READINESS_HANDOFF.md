# CertVIC C12 pre-experiment maximum-readiness handoff

Status: **ALL_REMAINING_HIGH_VALUE_LOCAL_PRE_EXPERIMENT_WORK_COMPLETE**. This is a software/design-readiness handoff, not paper evidence and not a submission-readiness claim.

## A. Live starting state

- Starting commit: `1ee0fcd0d0b241a88ff7b57cf5277800c4552e10`
- Handoff generated from committed head: `8c56a7036f39cc98d9854c374f437a270d2cc592`
- Origin/main at generation: `1ee0fcd0d0b241a88ff7b57cf5277800c4552e10`
- Authenticated identity details: `C12_IDENTITY_BASELINE.json`

## B. Design-power decision

**AMENDED_BEFORE_PROSPECTIVE_OUTCOMES**: old allocation 120 relevant / 120 irrelevant; new allocation 120 relevant / 240 irrelevant, plus 30 / 60 reserve. At the declared 0.70/0.03 design scenario, all-three six-gate power changes from 0.333528 to 0.901036. Thresholds, six-gate Bonferroni family, relevant n, endpoints, and fail-closed semantics are unchanged. No prospective outcome was observed or used.

## C. Completed C12 work

The v3 amendment, real-smoke intake, zero-edit 00C2 and full-universe primary runbooks, outcome-blind matching/detectability, human-review infrastructure, nine golden analysis fixtures, evidence-class claim registry, reviewer-attack suite, secondary gating, conditional Main/second-domain frameworks, CI, and clean reproduction are implemented. Phase B passed 17/17 commands with 1023 pytest passes, 4 skips, zero local failures, no GPU runs, and `paper_evidence=false`. Clean reproduction matched 18/18 compared artifacts with zero mismatch.

## D. Remaining external actions

1. **P0** — Provide two real, user-owned/license-eligible original/edited image pairs and affirm research plus redistribution rights.
2. **P0** — Build the canonical two-item bundle and three permissions, then execute/import the three 00C2 runs.
3. **P0** — Provision and license-verify the prospective source universe; current feasibility is SOURCE_BYTES_MISSING.
4. **P0** — Generate candidates, build the blind packet, complete two independent qualified reviews and adjudication.
5. **P0** — Run outcome-blind matching/detectability, freeze the v3 task universe, mint permissions, and execute the four primary confirmatory runs.
6. **P1** — Only after the primary freeze, consider separately permissioned robustness arms and optional-model expansion.
7. **P2** — Select a second domain by the evidence-backed template; keep Main unauthorized until the hash-bound confirmatory GO artifact exists.

## E. Exact next user action

**`PROVIDE_TWO_REAL_LICENSED_SMOKE_PAIRS`**

Check the intake state with `python3 local_operator/prepare_real_smoke_items.py --status`; then supply four genuine image paths and the explicit user-owned/research-use/redistribution affirmations. Do not open Kaggle yet.

## F. Kaggle run order

Account names are scheduling suggestions only; the contracts authenticate content identities and are owner/path independent.

| # | Stage | Notebook | Account suggestion | Accelerator / Internet | Input | Planning estimate | Output / import |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | 00C2_QWEN | `00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb` | lancerdevsm | T4x2 / OFF | `kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/Qwen snapshot and inputs/05_REAL_TWO_ITEM_SMOKE` | planning range 20/40/60 minutes optimistic/typical/conservative | `00C2_qwen2_5_vl_7b_real_model_smoke.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/00C2_qwen2_5_vl_7b_real_model_smoke.zip` |
| 2 | 00C2_INTERNVL | `00C2_internvl_8b_real_model_two_item_smoke.ipynb` | saket9500 | T4x2 / OFF | `kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/InternVL snapshot and inputs/05_REAL_TWO_ITEM_SMOKE` | planning range 20/40/60 minutes optimistic/typical/conservative | `00C2_internvl_8b_real_model_smoke.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/00C2_internvl_8b_real_model_smoke.zip` |
| 3 | 00C2_LLAVA | `00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb` | examhelps | T4x2 / OFF | `kagglefiles/inputs/06_PRE_SMOKE_PERMISSIONS plus authenticated common/wheelhouse/LLaVA snapshot and inputs/05_REAL_TWO_ITEM_SMOKE` | planning range 20/40/60 minutes optimistic/typical/conservative | `00C2_llava_onevision_7b_real_model_smoke.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/00C2_llava_onevision_7b_real_model_smoke.zip` |
| 4 | CONFIRMATORY_GENERATION_AFTER_ALL_LOCAL_GATES | `01_specificity_confirmatory_generation_T4x2.ipynb` | saket9500 (convenience only; identities are content-bound) | T4x2 / OFF | `kagglefiles/inputs/07_CONFIRMATORY_GENERATION` | planning estimate 2-8 hours; recalibrate after measured 00C2 | `confirmatory_generation_return.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/confirmatory_generation_return.zip` |
| 5 | CONFIRMATORY_QWEN | `02_qwen_specificity_confirmatory_T4x2.ipynb` | lancerdevsm | T4x2 / OFF | `kagglefiles/inputs/08_CONFIRMATORY_QWEN` | planning estimate 2-5 hours | `confirmatory_qwen_return.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/confirmatory_qwen_return.zip` |
| 6 | CONFIRMATORY_INTERNVL | `03_internvl_specificity_confirmatory_T4x2.ipynb` | saket9500 | T4x2 / OFF | `kagglefiles/inputs/09_CONFIRMATORY_INTERNVL` | planning estimate 3-7 hours | `confirmatory_internvl_return.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/confirmatory_internvl_return.zip` |
| 7 | CONFIRMATORY_LLAVA | `04_llava_specificity_confirmatory_T4x2.ipynb` | examhelps | T4x2 / OFF | `kagglefiles/inputs/10_CONFIRMATORY_LLAVA` | planning estimate 2-5 hours | `confirmatory_llava_return.zip`; `python3 kagglefiles/import_kaggle_return.py /path/to/confirmatory_llava_return.zip` |

Stop after every download, import it transactionally, and run `bash kagglefiles/run_local_resume.sh` before continuing.

## G. Human review work

- `reports/cvpr2027_c12/human/rater_qualification_packet.csv`
- `reports/cvpr2027_c12/human/coordinator_qualification_answer_key.csv`
- `reports/cvpr2027_c12/human/review_assignment_template.csv`
- `reports/cvpr2027_c12/human/qualification_policy.json`
- `reports/cvpr2027_c12/human/review_timeline.template.json`

Instructions: Build and hash-lock the blind packet from licensed sources; qualify two distinct genuine raters; preserve raw sheets; validate exact row coverage; adjudicate only disagreements; never synthesize labels. Planning only: coordinator 4–8 hours after source bytes exist; each rater 2–4 hours; adjudication/validation 1–3 hours. Current genuine reviewed count: **0**.

## H. Protocol integrity

No prospective provider outcome was observed or used; matching contains no provider outcome; no post-outcome threshold, sample-size, or selection tuning occurred. Historical artifacts cannot satisfy prospective claims. `paper_evidence=false` throughout.

## I. Identity impact

`ALL_AUTHENTICATED_IDENTITIES_PRESERVED`. Common identities preserved: `true`; authenticated runtime returns preserved: `true`; 00A/00B rerun required: `false`.

## J. Remaining scientific blockers

- **P0:** two real licensed smoke pairs; three 00C2 GPU returns; SOURCE_BYTES_MISSING; genuine two-rater review; prospective matching/detectability and frozen task universe; four primary confirmatory GPU returns
- **P1:** secondary robustness outputs; optional-model implementation and evidence
- **P2:** evidence-backed second-domain selection; conditional Main500 authorization

## K. What NOT to do next

- Do not rerun authenticated 00A/00B or provisioning.
- Do not launch 00C2 before the real bundle and exact single-use permissions exist.
- Do not treat synthetic proofs, historical outputs, smoke, plans, or contracts as prospective evidence.
- Do not tune thresholds, sample size, matching, or candidate selection after outcomes.
- Do not start secondary, optional-model, Main, or second-domain runs before their separate gates.
- Do not add more generic infrastructure before external evidence arrives.

## Proven completion markers

- `CERTVIC_C12_DESIGN_POWER_RESOLVED`
- `CERTVIC_C12_SMOKE_INTAKE_READY`
- `CERTVIC_C12_00C2_SOFTWARE_READY`
- `CERTVIC_C12_PRIMARY_RUNBOOKS_READY`
- `CERTVIC_C12_SECONDARY_RUNBOOKS_PREPARED`
- `CERTVIC_C12_HUMAN_REVIEW_READY`
- `CERTVIC_C12_MATCHING_DETECTABILITY_READY`
- `CERTVIC_C12_PRIMARY_ANALYSIS_READY`
- `CERTVIC_C12_CLAIM_REGISTRY_V2_READY`
- `CERTVIC_C12_CLEAN_REPRODUCTION_PASS`
- `CERTVIC_C12_LOCAL_FAILURES_ZERO`
- `CERTVIC_C12_COMMON_IDENTITIES_PRESERVED`
- `CERTVIC_C12_00A_00B_RERUN_NOT_REQUIRED`

Explicit non-claims: `CVPR_READY`, `SUBMISSION_READY`, `PROSPECTIVE_EVIDENCE_COMPLETE`, and `PAPER_EVIDENCE_COMPLETE` are **not** claimed.
