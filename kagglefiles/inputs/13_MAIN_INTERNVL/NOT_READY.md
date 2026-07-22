# NOT READY: MAIN_INTERNVL_INPUT

- Missing role: `MAIN_INTERNVL_INPUT`
- Why missing: Main execution_allowed=false until confirmatory gates pass.
- Prerequisite stage: `Genuine confirmatory GO decision`
- Exact builder/notebook/command: `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/main_external_roots.yaml`
- Expected filename: `certvic_main_internvl_input.zip`
- Expected size: 1 MB-60 GB depending on role
- Completed-file destination: `kagglefiles/inputs/13_MAIN_INTERNVL/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
