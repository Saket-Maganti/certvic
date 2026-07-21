# CertVIC V6 Prompt — Naive vs Validity-Gated Result Story

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Build the comparison that proves CertVIC is not just a benchmark.

Create:
- `certvic/reporting/naive_vs_validity_gated.py`

CLI:
`python3 -m certvic.reporting.naive_vs_validity_gated --naive <all_scores.jsonl> --valid <valid_scores.jsonl> --certificates <item_certificates.jsonl> --out-dir data/results/naive_vs_validity_gated`

Outputs:
- naive gap
- validity-gated gap
- rejected-item gap
- rejection distribution
- gap shift
- caution labels
- paper-safe text draft with RESULT REQUIRED placeholders if real data absent

Tests:
- validity gating changes gap in fixture
- rejected items summarized
- non-real inputs produce non-evidence language
- no fake numbers

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
