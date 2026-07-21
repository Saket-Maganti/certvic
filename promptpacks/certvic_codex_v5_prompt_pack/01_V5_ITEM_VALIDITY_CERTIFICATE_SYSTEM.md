# CertVIC V5 Prompt — Item Validity Certificate System

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a machine-readable validity certificate for every future item.

Create:
- `certvic/validity/item_certificate.py`
- `certvic/validity/certificate_schema.py`
- `certvic/validity/certificate_report.py`

CLI:
`python3 -m certvic.validity.item_certificate --tasks <tasks.jsonl> --edits <generated_edits.jsonl> --review <visual_review_summary.json> --out data/validity/item_certificates.jsonl --report-dir data/results/item_validity`

Certificate fields:
- item_id
- source_id
- edit_id
- mask_id
- task_family
- domain
- label_policy_status
- quality_gate_status
- detectability_status
- visual_review_status
- human_answerability_status
- control_compatibility_status
- single_factor_status
- photorealism_status
- leakage_status
- provenance_status
- evidence_eligible_candidate
- blocking_reasons
- warnings
- certificate_version
- input_hashes

Tests:
- valid item passes candidate status
- failed quality/review/leakage blocks
- missing provenance warns
- certificates are deterministic
- report summarizes block reasons

Docs:
- `docs/V5_ITEM_VALIDITY_CERTIFICATES_REPORT.md`
- `docs/ITEM_VALIDITY_CERTIFICATES.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
