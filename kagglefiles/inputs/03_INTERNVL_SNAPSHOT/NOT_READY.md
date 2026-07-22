# NOT READY: INTERNVL_MODEL_SNAPSHOT

- Missing role: `INTERNVL_MODEL_SNAPSHOT`
- Why missing: Immutable model bytes are external.
- Prerequisite stage: `BUILD_MODEL_SNAPSHOT internvl_8b`
- Exact builder/notebook/command: `Run runbooks/00_PROVISIONING/02_build_internvl_8b_snapshot.ipynb`
- Expected filename: `internvl2_8b_snapshot.zip`
- Expected size: 16-20 GB
- Completed-file destination: `kagglefiles/inputs/03_INTERNVL_SNAPSHOT/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
