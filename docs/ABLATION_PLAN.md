# Ablation Plan

Scale: 2000
Models: qwen2_5_vl_7b, internvl_8b, llava_onevision_7b
Estimated GPU hours: 90.0
Free-compute budget respected: True

Required ablations:
- main_prompt
- text_only_baseline
- caption_only_baseline
- parse_failure_sensitivity

Optional ablations:
- prompt_variant
- edit_type_breakdown
- cluster_sensitivity
