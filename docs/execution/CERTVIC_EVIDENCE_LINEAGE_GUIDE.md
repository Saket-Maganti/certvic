
# CertVIC Evidence Lineage Guide

Every run binds task, prompt, image, parser, schema, code, environment, model/processor identity,
snapshot manifests, decoding, seed, and sharding in `run_contract_hash`. Resume revalidates the hash;
stale data moves to `quarantine/<reason>/<UTC timestamp>/` with a pointer record.

The all-providers importer stages all ZIPs before promotion. It separately records returned archive
SHA-256, raw merged JSONL SHA-256, canonical normalized JSONL SHA-256, and promoted artifact SHA-256.
Raw returned archives are `REAL_OBSERVED_EVIDENCE`; canonical rows are
`DERIVED_FROM_REAL_EVIDENCE` with an upstream hash. Analysis requires validated adjudicated inclusion
and writes raw, filtered, exclusion, agreement/adjudication, and artifact-lineage outputs. Paper
promotion remains a separate branch gate; successful import alone leaves `paper_evidence=false`.
