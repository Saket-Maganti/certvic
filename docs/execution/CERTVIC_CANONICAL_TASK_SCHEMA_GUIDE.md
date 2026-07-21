
# CertVIC Canonical Task Schema Guide

`certvic.cvpr.task.v1` is the sole task contract for confirmatory, Main, and COCO lanes. The complete
field list and conditional null policy live in `certvic/cvpr/task_schema.py`. Convert legacy rows once
with `convert_legacy_task`; runtime, generation, import, analysis, and paper paths must not implement
aliases. `task_hash` covers every field except itself. File verification binds source, target-mask,
and protected-scene bytes. Mixed, incomplete, duplicated, or hash-drifted matrices fail closed.

```bash
python3 -m certvic.cvpr.task_schema --input <LEGACY.jsonl> --study <STUDY> --out <CANONICAL.jsonl> --verify-files
python3 -m certvic.cvpr.task_schema --input <CANONICAL.jsonl> --verify-files
```

Main uses `original_expected_answer` and `edited_expected_answer` directly. Attribute rows require a
registered exact transition and `original_attribute_verified=true`. Absent-category rows require the
protected-scene mask. Final execution rows require `qa_status=PASS`,
`review_status=VALID_ADJUDICATED`, and a primary/reserve role. Schema conversion is compatibility;
it is not review, evidence, or permission.
