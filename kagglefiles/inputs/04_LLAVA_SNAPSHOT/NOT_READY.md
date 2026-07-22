# NOT READY: LLAVA_MODEL_SNAPSHOT

- Missing role: `LLAVA_MODEL_SNAPSHOT`
- Why missing: Immutable model bytes are external.
- Prerequisite stage: `BUILD_MODEL_SNAPSHOT llava_onevision_7b`
- Exact builder/notebook/command: `Run runbooks/00_PROVISIONING/03_build_llava_onevision_7b_snapshot.ipynb`
- Expected filename: `llava_onevision_7b_snapshot.zip`
- Expected size: 15-18 GB
- Completed-file destination: `kagglefiles/inputs/04_LLAVA_SNAPSHOT/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
