# NOT READY: MAIN_QWEN_INPUT

- Missing role: `MAIN_QWEN_INPUT`
- Why missing: Main execution_allowed=false until confirmatory gates pass.
- Prerequisite stage: `Genuine confirmatory GO decision`
- Exact builder/notebook/command: `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/main_external_roots.yaml`
- Expected filename: `certvic_main_qwen_input.zip`
- Expected size: 1 MB-60 GB depending on role
- Completed-file destination: `kagglefiles/inputs/12_MAIN_QWEN/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
