# NOT READY: SECOND_DOMAIN_INTERNVL_INPUT

- Missing role: `SECOND_DOMAIN_INTERNVL_INPUT`
- Why missing: Second-domain execution_allowed=false until separately authorized.
- Prerequisite stage: `Separate second-domain feasibility and execution authorization`
- Exact builder/notebook/command: `python3 -m certvic.cvpr.build_all_kaggle_inputs --with-external-roots local_inputs/second_domain_external_roots.yaml`
- Expected filename: `certvic_coco_internvl_input.zip`
- Expected size: 1 MB-60 GB depending on role
- Completed-file destination: `kagglefiles/inputs/17_SECOND_DOMAIN_INTERNVL/`
- Evidence boundary: `paper_evidence=false`; do not fabricate the missing bytes.
