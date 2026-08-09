# CertVIC C11 maximum-ceiling handoff

Status: `ALL_AVAILABLE_LOCAL_C11_WORK_COMPLETE`. Paper evidence remains `false`; genuine human-reviewed count is 0; 00C2, Main, and the second domain are not authorized.

## A. What was completed locally

- full repository/gap audit
- exact power/design and confidence-sequence validation
- pilot baselines/ablations/pairwise/heterogeneity/stability
- image quality/balance/detectability
- duplicate/leakage/contamination
- human-review infrastructure
- outcome-blind selection tooling
- certificate API
- claim/evidence registry
- scientific red team
- compute ledger
- deterministic tables/figures and manifests
- GPU/resource/operator contracts
- Main and second-domain conditional contracts
- clean-room reproduction
- identity comparison

## B. CPU results

| Package | Status | Runtime (s) | Main finding | Interpretation | Evidence class |
| --- | --- | ---: | --- | --- | --- |
| exact power/design/FWER/boundary/missingness | `COMPLETE` | 55.984 | At n=120 the exact gates require >= 74 semantic updates and <= 4 flips. Design-scenario three-model joint power is 0.334. | The frozen marginal gates are exact, but simultaneous three-model certification has modest power under the declared 0.70/0.03 design scenario. | `DESIGN_VALIDATION_NOT_MODEL_EVIDENCE` |
| confidence-sequence validation | `PASS_EMPIRICAL_VALIDATION` | 55.984 | Maximum empirical noncoverage plus three Monte Carlo SE was 0.005514. | No material undercoverage was detected in the declared Bernoulli simulation grid; fixed-sample CP intervals remain invalid for optional peeking. | `SOFTWARE_STATISTICAL_VALIDATION` |
| pilot baselines/ablations/pairwise/heterogeneity/stability | `COMPLETE_RETROSPECTIVE_DIAGNOSTIC` | 0.101 | qwen2_5_vl_7b: update=0.176, flip=0.128; internvl_8b: update=0.099, flip=0.011; llava_onevision_7b: update=0.143, flip=0.032 | All historical models fail the strict responsiveness gate; Qwen also fails specificity, and LLaVA's multiplicity-corrected upper bound narrowly exceeds 0.10. Naive metric rankings reverse across endpoints. | `RETROSPECTIVE_DIAGNOSTIC` |
| image quality/balance/detectability | `COMPLETE_DIAGNOSTIC_WITH_GATE_FAILURE` | 22.064 | Historical endpoint-arm symmetric AUC=0.998831, 95% bootstrap [0.996377, 1.000000], permutation p=0.000999. | Historical relevant and irrelevant arms are highly distinguishable from low-level features. This is a reviewer-risk diagnostic and cannot satisfy the prospective original-vs-edited gate. | `RETROSPECTIVE_DIAGNOSTIC` |
| duplicate/leakage/contamination | `PASS_WITH_DOCUMENTED_RETROSPECTIVE_V2_REUSE` | 2.021 | 0 prospective collisions; V1/V2 overlap=30 as documented retrospective reuse. | No absent prospective evidence was fabricated or contaminated; V2 remains retrospective-only. | `PROVENANCE_AUDIT` |
| human review infrastructure | `INFRASTRUCTURE_COMPLETE_EXECUTION_BLOCKED_HUMAN` | 0.002 | State=WAITING_FOR_RATER_1; genuine human-reviewed count remains zero. | Infrastructure is ready, but no human-validity claim is available. | `INFRASTRUCTURE_ONLY` |
| prospective census and exact outcome-blind selection | `BLOCKED_LICENSE` | 0.001 | CONFIRMATORY_SOURCE_BYTES_MISSING | Selection code is ready and rejects provider outcomes, but cannot select without licensed source bytes. | `INFRASTRUCTURE_ONLY` |
| clean-room reproduction | `CLEAN_REPRODUCTION_COMPLETE` | 82.167 | mismatch_count=0 | All selected deterministic CPU artifacts reproduce from committed immutable inputs in a clean checkout. | `REPRODUCIBILITY_VALIDATION` |

## C. Remaining GPU runs

See `gpu/GPU_EXECUTION_MATRIX.csv` for the full provider-level matrix. The first three runnable scientific rows remain 00C2 and require the missing shared licensed smoke input plus distinct permissions.

| Stage | Provider | Notebook | Accelerator | Internet | Estimate | Output | Prerequisites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 00C2_REAL_MODEL_SMOKE | qwen2_5_vl_7b | runbooks/04_REAL_MODEL_SMOKE/00C2_qwen2_5_vl_7b_real_model_two_item_smoke.ipynb | T4x2 | OFF | 20–60 min (planning) | 00C2_qwen2_5_vl_7b_real_model_smoke.zip | two licensed real items; current 00A/00B; distinct permission |
| CONFIRMATORY_PROVIDER | qwen2_5_vl_7b | runbooks/06_CONFIRMATORY_MODELS/02_qwen_specificity_confirmatory_T4x2.ipynb | T4x2 | OFF | 60–240 min (planning) | confirmatory_qwen2_5_vl_7b_return.zip | 00C2 PASS; generation QA; human review; freeze; detectability PASS |
| REPEAT_DETERMINISM | qwen2_5_vl_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 30–90 min (planning) | secondary_repeat_determinism_qwen2_5_vl_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| PROMPT_ROBUSTNESS | qwen2_5_vl_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_prompt_robustness_qwen2_5_vl_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| DECODING_ROBUSTNESS | qwen2_5_vl_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_decoding_robustness_qwen2_5_vl_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| NATURAL_ABSENCE_CONTROL | qwen2_5_vl_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–180 min (planning) | secondary_natural_absence_control_qwen2_5_vl_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| 00C2_REAL_MODEL_SMOKE | internvl_8b | runbooks/04_REAL_MODEL_SMOKE/00C2_internvl_8b_real_model_two_item_smoke.ipynb | T4x2 | OFF | 20–60 min (planning) | 00C2_internvl_8b_real_model_smoke.zip | two licensed real items; current 00A/00B; distinct permission |
| CONFIRMATORY_PROVIDER | internvl_8b | runbooks/06_CONFIRMATORY_MODELS/03_internvl_specificity_confirmatory_T4x2.ipynb | T4x2 | OFF | 60–240 min (planning) | confirmatory_internvl_8b_return.zip | 00C2 PASS; generation QA; human review; freeze; detectability PASS |
| REPEAT_DETERMINISM | internvl_8b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 30–90 min (planning) | secondary_repeat_determinism_internvl_8b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| PROMPT_ROBUSTNESS | internvl_8b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_prompt_robustness_internvl_8b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| DECODING_ROBUSTNESS | internvl_8b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_decoding_robustness_internvl_8b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| NATURAL_ABSENCE_CONTROL | internvl_8b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–180 min (planning) | secondary_natural_absence_control_internvl_8b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| 00C2_REAL_MODEL_SMOKE | llava_onevision_7b | runbooks/04_REAL_MODEL_SMOKE/00C2_llava_onevision_7b_real_model_two_item_smoke.ipynb | T4x2 | OFF | 20–60 min (planning) | 00C2_llava_onevision_7b_real_model_smoke.zip | two licensed real items; current 00A/00B; distinct permission |
| CONFIRMATORY_PROVIDER | llava_onevision_7b | runbooks/06_CONFIRMATORY_MODELS/04_llava_specificity_confirmatory_T4x2.ipynb | T4x2 | OFF | 60–240 min (planning) | confirmatory_llava_onevision_7b_return.zip | 00C2 PASS; generation QA; human review; freeze; detectability PASS |
| REPEAT_DETERMINISM | llava_onevision_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 30–90 min (planning) | secondary_repeat_determinism_llava_onevision_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| PROMPT_ROBUSTNESS | llava_onevision_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_prompt_robustness_llava_onevision_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| DECODING_ROBUSTNESS | llava_onevision_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–240 min (planning) | secondary_decoding_robustness_llava_onevision_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| NATURAL_ABSENCE_CONTROL | llava_onevision_7b | CONTRACT_PREPARED; executable notebook intentionally pending frozen secondary input | T4x2 | OFF | 60–180 min (planning) | secondary_natural_absence_control_llava_onevision_7b_return.zip | primary frozen/completed; separate secondary task identity; no selection contamination |
| CONFIRMATORY_GENERATION | shared | runbooks/05_CONFIRMATORY_GENERATION/01_specificity_confirmatory_generation_T4x2.ipynb | T4x2 | OFF | 120–480 min (planning) | confirmatory_generation_return.zip | 00C2 PASS; license/source validation |
| MAIN500_CONDITIONAL | all | runbooks/07_MAIN_CONDITIONAL/10-13 provider suite | T4x2 | OFF | DERIVE–DERIVE min (planning) | main_*_return.zip | CONDITIONAL_NOT_AUTHORIZED until genuine GO |
| SECOND_DOMAIN_CONDITIONAL | all | runbooks/08_SECOND_DOMAIN_CONDITIONAL/20-23 suite | T4x2 | OFF | DERIVE–DERIVE min (planning) | second_domain_*_return.zip | dataset selection and execution authorization |

## D. Remaining human tasks

1. After licensed generation, freeze the blinded candidate packet and its byte manifest. Estimated: 0.5-1 coordinator.
2. Qualify two distinct independent raters; preserve hashed identities and raw sheets. Estimated: 0.5-1 per rater.
3. Each rater reviews every frozen candidate without provider outputs. Estimated: 4-8 per rater, refine after timed pilot.
4. Adjudicate every disagreement and lock final inclusion before selection/model execution. Estimated: 1-3 adjudicator/coordinator.

## E. Remaining licensed-data tasks

- **P0 — REAL_TWO_ITEM_SMOKE:** two real original/edited pairs, optional masks, non-synthetic, license_eligible=true, concrete auditable license_id, zero historical overlap, frozen prompt/parser/run-contract bindings
- **P0 — CONFIRMATORY_SOURCE:** genuine ADE20K validation images/annotations at runtime plus auditable source/license manifest; do not redistribute where not cleared
- **P1 — SECOND_DOMAIN_SOURCE:** only after domain selection: license verification, source manifest, category mapping, endpoint compatibility, and review plan

## F. CVPR scientific blocker ranking

| Rank | Priority | Blocker | Effect |
| ---: | --- | --- | --- |
| 1 | `P0` | Two real licensed non-synthetic smoke pairs absent | 00C2 remains NOT_AUTHORIZED; no genuine primary GPU inference may start. |
| 2 | `P0` | Prospective licensed confirmatory source bytes absent | No candidate census, generation, review, freeze, or permission can complete. |
| 3 | `P0` | No genuine independent human review | Human validity and prospective paper-evidence promotion remain false. |
| 4 | `P0` | No prospective provider returns | No joint certificate, model comparison, or Main GO decision exists. |
| 5 | `P0` | Historical endpoint arms are low-level detectable | AUC ~0.999 exposes matching/confounding risk; prospective construction must pass its unchanged gate. |
| 6 | `P1` | Frozen three-model design-scenario joint power is modest | Monte Carlo joint power ~0.334 at update=0.70/flip=0.03; record larger-n design only as a future protocol idea. |
| 7 | `P1` | Strict historical semantic responsiveness is low | All three pilot models are below 0.18; scientific viability must be judged prospectively, not rescued by raw answer-change metrics. |
| 8 | `P1` | Secondary robustness notebooks are not yet executable | Contracts and estimates exist, but frozen secondary inputs/permissions and executable notebooks wait until primary freeze/completion. |
| 9 | `P1` | Single-domain and three-model scope | Cross-domain and broader-architecture claims remain blocked/optional. |

## G. Identity impact

`ALL_AUTHENTICATED_IDENTITIES_PRESERVED`. Common identities preserved: `true`. Runtime returns preserved: `true`. 00A/00B rerun required: `false`.

## H. Project ceiling scorecard

| Dimension | Score / 5 | Evidence |
| --- | ---: | --- |
| novelty clarity | 3.0 | Clear certificate framing in infrastructure; manuscript wording was deliberately untouched. |
| statistical rigor | 4.5 | Exact six-gate rule, power/FWER/boundary/missingness and CS validation are implemented and tested. |
| experimental design | 3.0 | Prospective freeze/gates are strong, but joint power is modest and external execution is absent. |
| human validation | 1.0 | Complete tooling, but zero genuine human-reviewed rows. |
| model breadth | 3.0 | Three current open VLMs; two optional candidates scored but not run. |
| domain breadth | 1.0 | No executed second domain. |
| baselines | 4.0 | Historical accuracy/change/update/specificity baselines and exact bounds generated. |
| ablations | 4.0 | Gate, multiplicity, parser, missingness, estimator, and human-filter states represented. |
| robustness | 3.0 | Strong CPU red team and contracts; secondary GPU notebooks/results remain pending. |
| reproducibility | 4.5 | Full clean archive reproduction matched 18/18 semantic artifacts. |
| artifact integrity | 5.0 | Authenticated identities preserved; transactional and claim guards pass. |
| compute transparency | 4.0 | Per-stage runtime/RAM and NOT_MEASURED energy/carbon are explicit; GPU actuals absent. |
| paper-readiness inputs | 2.0 | Tables/figures are generated, but prospective, human, GPU, and cross-domain evidence is absent. |

## I. Next exact operator action

`PROVIDE_TWO_REAL_LICENSED_SMOKE_ITEMS`

Do not open a GPU session until the two paired items pass the local license, non-synthetic, overlap, prompt, parser, and run-contract checks.

## Proven truth markers

- `CERTVIC_C11_ALL_AVAILABLE_CPU_WORK_COMPLETE`
- `CERTVIC_C11_STATISTICAL_VALIDATION_COMPLETE`
- `CERTVIC_C11_REPRODUCIBILITY_COMPLETE`
- `CERTVIC_C11_SCIENTIFIC_RED_TEAM_COMPLETE`
- `CERTVIC_C11_LOCAL_FAILURES_ZERO`
- `CERTVIC_C11_COMMON_IDENTITIES_PRESERVED`
- `CERTVIC_C11_00A_00B_RERUN_NOT_REQUIRED`

Not claimed: `CVPR_READY`, `SUBMISSION_READY`, `PAPER_EVIDENCE_COMPLETE`, or complete secondary GPU runbooks.
