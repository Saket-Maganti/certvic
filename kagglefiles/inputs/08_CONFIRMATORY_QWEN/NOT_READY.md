# NOT READY: CONFIRMATORY_QWEN_INPUT

- Missing role: `CONFIRMATORY_QWEN_INPUT`
- Why missing: Prospective human and authorization gates are incomplete.
- Prerequisite stage: `Genuine human review, exact selection, detectability, task freeze, and provider permission`
- Exact builder/notebook/command: `python3 -m certvic.cvpr.scientific_input_builder --study confirmatory --provider qwen --config local_inputs/08_confirmatory_qwen.json --run-tag specificity_confirmatory_v1`
- Expected filename: `certvic_confirmatory_qwen_input.zip`
- Expected size: 1 MB-25 GB
- Completed-file destination: `kagglefiles/inputs/08_CONFIRMATORY_QWEN/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
