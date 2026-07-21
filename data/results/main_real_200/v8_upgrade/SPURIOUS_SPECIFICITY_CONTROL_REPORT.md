# V8 Spurious Specificity Control Report

`status=blocked_failed_gate` `evidence_status=SPECIFICITY_CONTROL_PILOT_NON_EVIDENCE` `paper_evidence=false`

| provider | n | flipped | flip rate | threshold | gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `qwen2_5_vl_7b` | 94 | 12 | 0.1277 | 0.1 | FAIL |
| `internvl_8b` | 94 | 1 | 0.0106 | 0.1 | PASS |
| `llava_onevision_7b` | 94 | 3 | 0.0319 | 0.1 | PASS |

Integration status: `blocked` / `blocked`.

This control result does not create main-scale evidence. A failed provider keeps scaling and paper-grade claims blocked.
