# CertVIC V6 Prompt — Mechanism Probe Infrastructure

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

Build minimal mechanism/diagnostic probe infrastructure.

Create:
- `certvic/mechanisms/diagnostics.py`
- `certvic/mechanisms/compare_prompts.py`
- `configs/mechanism_probes.yaml`

Mechanism families:
- answer inertia
- localization failure
- text-prior anchoring
- prompt-form sensitivity
- edit-type sensitivity
- crop/region sensitivity

Supported diagnostic prompts:
- direct answer
- localize-then-answer
- describe-changed-region-then-answer
- crop-focused diagnostic
- multiple-choice diagnostic

Important:
- diagnostic prompts must be clearly marked as diagnostic, not primary, unless preregistered
- no VLM inference in tests
- generate task/prompt manifests only

CLI:
`python3 -m certvic.mechanisms.diagnostics plan --tasks <tasks.jsonl> --out data/results/mechanism_probe_plan.jsonl`

Tests:
- diagnostic manifest generated
- primary vs exploratory status preserved
- no diagnostic result becomes primary claim by default
- prompt labels deterministic

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
