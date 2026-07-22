# NOT READY: QWEN_MODEL_SNAPSHOT

- Missing role: `QWEN_MODEL_SNAPSHOT`
- Why missing: Immutable model bytes are external.
- Prerequisite stage: `BUILD_MODEL_SNAPSHOT qwen2_5_vl_7b`
- Exact builder/notebook/command: `Run runbooks/00_PROVISIONING/01_build_qwen2_5_vl_7b_snapshot.ipynb`
- Expected filename: `qwen2_5_vl_7b_snapshot.zip`
- Expected size: 15-18 GB
- Completed-file destination: `kagglefiles/inputs/02_QWEN_SNAPSHOT/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
