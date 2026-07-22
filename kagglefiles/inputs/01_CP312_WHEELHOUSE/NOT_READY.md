# NOT READY: CP312_WHEELHOUSE

- Missing role: `CP312_WHEELHOUSE`
- Why missing: The active CPython 3.12 Linux wheel bytes must be provisioned on Kaggle with Internet ON.
- Prerequisite stage: `BUILD_CP312_WHEELHOUSE`
- Exact builder/notebook/command: `Run runbooks/00_PROVISIONING/00_build_certvic_cp312_wheelhouse.ipynb`
- Expected filename: `certvic_offline_wheelhouse_cp312.zip`
- Expected size: approximately 3-18 GB; record actual bytes
- Completed-file destination: `kagglefiles/inputs/01_CP312_WHEELHOUSE/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
