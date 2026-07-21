# V8 Scaled Held-Out Perception Control Report

`status=complete` `evidence_status=HELDOUT_PERCEPTION_CONTROL_PILOT_NON_EVIDENCE` `paper_evidence=false`

| provider | n | absent | present | overall accuracy |
| --- | ---: | --- | --- | ---: |
| `qwen2_5_vl_7b` | 369 | 165/177 (0.9322) | 166/192 (0.8646) | 0.897 |
| `internvl_8b` | 369 | 160/177 (0.904) | 185/192 (0.9635) | 0.935 |
| `llava_onevision_7b` | 369 | 156/177 (0.8814) | 188/192 (0.9792) | 0.9322 |

This is a control run. It does not by itself clear the spurious specificity gate.
