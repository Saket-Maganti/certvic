
# CertVIC Post-Run Atomic Import Guide

Place exactly one returned ZIP for each frozen provider in a new input directory. Do not unpack or
edit them. The whole-study importer checks ZIP integrity, duplicate/path-unsafe members, the complete
member hash manifest, runtime/environment/validation manifests, provider/study/schema/row count,
merged-output hash, and every row against frozen item, variant, prompt, image, task, model, processor,
parser, code-bundle, and snapshot hashes.

All providers are validated in a temporary staging directory. The matrix must have identical task
identity and study-wide provenance. Only then are canonical rows, immutable raw ZIPs, audit report,
and evidence ledger promoted with one directory rename. A failure promotes none. An identical import
is an idempotent no-op; conflicting prior output is refused and gets a quarantine marker. Successful
raw predictions are `REAL_OBSERVED_EVIDENCE`, while paper eligibility remains
`HUMAN_REVIEW_PENDING` and `paper_evidence=false` until the separate review and claim gates pass.
