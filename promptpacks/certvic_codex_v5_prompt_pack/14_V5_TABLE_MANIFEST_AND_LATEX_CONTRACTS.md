# CertVIC V5 Prompt — Table Manifest and LaTeX Contracts

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Create table manifest and LaTeX table contracts.

Create:
- `paper/table_manifest.yaml`
- `certvic/paper/table_manifest_audit.py`

Tables:
- main result
- by family
- by domain
- by edit type
- model comparison
- baselines/ablations
- parser sensitivity
- certification
- human review quality
- edit detectability
- cluster diagnostics

Tests:
- tables have source artifact
- descriptive vs certified noted
- no fake numbers
- LaTeX path declared

Docs:
- `docs/V5_TABLE_MANIFEST_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
