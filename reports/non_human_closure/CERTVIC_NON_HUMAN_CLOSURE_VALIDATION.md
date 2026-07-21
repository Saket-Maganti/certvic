# CertVIC Phase C non-human closure validation

Final local validation date: 2026-07-21. All records below are non-evidence execution or synthetic
proofs. `paper_evidence=false`; genuine `human_reviewed=true` count is zero.

## Scientific and operational contracts

- Exactly one prospective protocol is authoritative: `configs/studies/specificity_confirmatory_cvpr.yaml`.
- Protocol SHA-256: `bb82612e09346599b0cabe3d1876369a652fc56e3406cd98ac21ce699a62ca25`.
- Primary-analysis SHA-256: `a3f3b4a3d8c942f5d753589a079b2c62dab63a7f6bd742d74f4a89022da3920d`.
- Semantic-update success and the separate irrelevant-flip endpoint pass adversarial tests; a
  never-updating model fails responsiveness.
- The V11 protocol is `DEPRECATED_NOT_FOR_EXECUTION`; the old gap is secondary descriptive only.
- Doctor result: `READY_FOR_00A`, no local blockers, stale replacement-archive requirement absent.
- Run graph and next-action agree on `run_00a`; 00A/00B are CPU integrity checks and 00C2 is the
  first genuine model-load/inference stage.

## Executed validation

| Validation | Result |
| --- | --- |
| `python3 scripts/run_phase_b_cpu_workflows.py --out reports/non_human_closure/phase_c_final_validation` | 15/15 commands PASS |
| `python3 -m pytest -q` | 875 passed, 1 skipped, 1 expected duplicate-member warning; exit 0 |
| `python3 -m ruff check --no-cache certvic scripts tests` | PASS; exit 0 |
| `python3 -m compileall -q certvic scripts tests` | PASS; exit 0 |
| canonical CVPR notebook validation | 16/16, zero stored code-cell outputs; exit 0 |
| synthetic canonical notebook execution proof | all declared routes PASS; synthetic only; exit 0 |
| legacy T4x2 static validation | 6/6 PASS; CPU static only |
| artifact registry verification | 24 artifacts, 0 errors; exit 0 |
| claim guard | PASS, 0 errors; no fabricated outputs/bytes/review |
| privacy/path/secret audit | PASS, 0 findings |
| paper compilation | two successful `pdflatex -halt-on-error` passes; 3 pages |
| post-human-review continuation synthetic proof | confirmatory/Main/COCO PASS; exit 0 |
| post-confirmatory-return continuation synthetic proof | confirmatory/Main/COCO PASS; exit 0 |
| deterministic Phase C release rebuild and clean extraction | PASS; final digest is stored outside the archive in `PROJECT_DISTRIBUTION_MANIFEST.json` |

## Provisioning validation

- Linux CPython 3.10 wheelhouse: 81 wheels; 94 ZIP members; 3,188,416,530 bytes; SHA-256
  `d62fe562ee7d012062c03fad3537f0a4da71e0e860b04b9dc7b6f942f4d15bda`.
- Clean `linux/amd64` Docker install used all five offline lockfiles with `--no-index --find-links`.
  Imports passed for PyTorch 2.4.1+cu121, torchvision 0.19.1+cu121, Transformers 4.46.3,
  Accelerate, Diffusers, OpenCV, pandas, SciPy, and scikit-learn.
- A second wheelhouse build was byte-identical. Exact machine record:
  `reports/non_human_closure/wheelhouse_clean_linux_validation.json`.
- Five Kaggle code/input bundles rebuilt deterministically. Final 00A handoff hashes are recorded in
  `reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md`.
- Three immutable model downloads were attempted and remain resumable partial caches. No snapshot
  ZIP or root hash was promoted. The Internet-enabled parameterized provisioning notebook is the
  validated external continuation.

## Preserved boundaries

- No canonical 00A, 00B, or 00C2 return exists; therefore `REAL_SMOKE_COMPLETE` is not claimed.
- No licensed zero-overlap two-item smoke manifest exists.
- No licensed prospective source census, generated candidate pool, automated QA result, or final
  prospective review packet exists; therefore `CONFIRMATORY_PRE_HUMAN_PIPELINE_COMPLETE` and
  `READY_FOR_GENUINE_HUMAN_REVIEW` are not claimed.
- The historical 91-relevant/94-control blank packet remains historical forensic review only.
- Main and COCO retain `execution_allowed=false`; V2-30 remains retrospective sensitivity evidence.
