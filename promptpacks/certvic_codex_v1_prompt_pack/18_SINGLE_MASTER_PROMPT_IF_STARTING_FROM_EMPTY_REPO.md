# Single Master Codex Prompt — Build CertVIC V1 From Empty Repo

Use this only if you want Codex to attempt a larger multi-stage build in one session. Prefer the numbered prompts for cleaner results.

You are building a new zero-cost research repository named `certvic`.

Project:
Certified Visual Consistency / CertVIC

Working title:
“Certifying When Vision-Language Models See the Change: Anytime-Valid Consistency Under Controlled Real-Image Interventions”

Hard rule:
No cost, no paid APIs, no paid cloud GPUs, no paid datasets, no paid annotation, no paid credits. Use only open-source/local/free resources. Anything involving a free-tier reference must be disabled by default and clearly marked reference-only.

Build V1 of the full project with:

1. Repo skeleton
2. Configs
3. Pydantic schemas
4. Source/license manifest tooling
5. Smoke fixtures
6. Mock provider
7. Prompt builder and parser
8. Batch/resume evaluation runner
9. Scoring
10. Bootstrap metrics
11. Confseq wrapper for anytime-valid confidence sequences
12. Certification gate
13. Baselines
14. Human validation workflow
15. Reporting/failure gallery/claim ledger
16. Audit gates
17. Kaggle markdown guides
18. CVPR paper scaffold with RESULT REQUIRED placeholders
19. End-to-end smoke audit report

Required repo structure:

```text
certvic/
  README.md
  pyproject.toml
  configs/
  data/
  certvic/
  notebooks/kaggle/
  tests/
  paper/
  docs/
```

Important implementation priorities:
- All normal tests must run without GPU.
- Heavy packages are optional extras only.
- No module should import torch/diffusers/transformers at top level.
- Real VLM adapters should be import-safe skeletons.
- Smoke mode must run end-to-end with generated tiny PIL images and mock providers.
- Every JSONL writer must flush after every record.
- Evaluation must resume by `(run_id, item_id, image_variant)`.
- Sharding must be deterministic.
- Task prompts must not leak labels or edit types.
- Claim ledger must prevent uncertified claims.
- Paper must not contain fake results or overclaims.

Run:
```bash
python -m pytest -q
```

Then run smoke pipeline:
```bash
python -m certvic.data.build_tasks --smoke --out data/manifests/smoke_tasks.jsonl
python -m certvic.data.manifest_checks --tasks data/manifests/smoke_tasks.jsonl --strict
python -m certvic.eval.run_eval --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --out data/predictions/smoke_mock_inconsistent.jsonl --provider mock_inconsistent --run-id smoke_mock_inconsistent_v1 --max-items 10
python -m certvic.metrics.score_predictions --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-scores data/results/smoke_pair_scores.jsonl --out-summary data/results/smoke_summary.json
python -m certvic.reporting.build_report --tasks data/manifests/smoke_tasks.jsonl --scores data/results/smoke_pair_scores.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --out-dir data/results/smoke_report --alpha 0.05 --gap-threshold 0.05
python -m certvic.audit --config configs/smoke.yaml --tasks data/manifests/smoke_tasks.jsonl --preds data/predictions/smoke_mock_inconsistent.jsonl --scores data/results/smoke_pair_scores.jsonl --paper paper/main.tex --strict
```

Create:
```text
docs/V1_SMOKE_AUDIT_REPORT.md
```

At the end, print:
- files changed
- tests run
- smoke commands run
- smoke audit verdict
- known limitations
- next recommended step: run numbered prompt 16 for ADE20K pilot preparation
