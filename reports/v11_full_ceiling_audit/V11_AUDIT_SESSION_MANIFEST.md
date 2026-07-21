# V11 Audit Session Manifest

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

This manifest anchors the local-only full-ceiling audit without exposing a private root path.

## Environment

- Audit date: 2026-07-12 Asia/Kolkata
- Repository root: `<PROJECT_ROOT>`
- Git state: not applicable; this directory is not a Git worktree
- Python: 3.11.9
- OS/architecture: Darwin / arm64
- Logical CPUs: 10
- Physical memory: 16.0 GiB
- Accelerator execution: none; this audit used local CPU-safe operations only
- Key dependencies: numpy=2.4.4, pandas=2.3.3, pillow=12.1.1, pydantic=2.12.5, pyyaml=6.0.3, scikit-learn=1.8.0, matplotlib=3.10.8, pytest=9.0.2, ruff=0.15.8, nbformat=5.10.4, scipy=1.17.1, confseq=not installed

## Initial evidence counts

- Intervention pilot: 91 paired items and 182 rows per provider for 3 providers.
- V1 specificity: 94 paired items and 188 rows per provider for 3 providers.
- Current V2 package: 30 items, 60 images, zero provider-output files.
- Human validity: assistant-generated preliminary screening only; independent second-rater fields blank.
- Main-500: planned, not executed, and formally blocked.

## Initial failures and audit corrections

1. Historical task metadata called machine screening human reviewed; V11 supersedes that label without rewriting hash-bound raw files.
2. The 91-item pilot does not meet the 150 overall or 40-per-family policy.
3. Qwen fails the frozen V1 specificity gate at 12/94.
4. The current 30-item V2 set reuses every V1 item and has no model outputs.
5. Exact historical model revisions are not recorded.
6. Private-path and release-package scope differ from the older scoped privacy claim.

## Commands represented in this build

The generator reads local JSON/JSONL/CSV/config/package artifacts, recomputes pair flips,
exact McNemar tests, deterministic paired bootstrap intervals, hashes, and inventory counts.
External validation commands and their exit codes are tracked in
`V11_COMMAND_AND_EXIT_CODE_LOG.md`; a not-run entry is never interpreted as a pass.

## Files modified during the V11 pass

See `V11_CHANGE_MANIFEST.csv`. Raw model-output files were read and hash-bound, not overwritten.
Derived reports, task-package metadata, notebooks, tests, and release manifests were regenerated
only where the V11 audit identified a concrete defect.
