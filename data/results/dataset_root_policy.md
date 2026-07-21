# Dataset Root Policy

Generated: 2026-06-22

CertVIC is recipe-first. Dataset pixels are never rehosted; the dataset root
is supplied by the user at run time and never committed or released.

## Principles

- Dataset roots are user-supplied at run time (CLI flag or config), never hard-coded.
- Dataset roots are never committed to the repo and never written into release artifacts.
- Pixels are not rehosted; CertVIC is recipe-first (pointers + hashes + recipes).
- Automatic downloads are disabled; the user places the dataset locally first.
- Output roots live under data/ (or compute_bundles/), never under a system or home root.

## Known datasets (pointer-only)

| Dataset | License | Supply via | Note |
| --- | --- | --- | --- |
| ADE20K | pointer_only / research terms (not rehosted) | `--ade20k-root <ROOT> or config ade20k_root` | Semantic PNG annotations are read locally; pixels are never copied into the repo or release. |

## Canonical output roots

- `data/manifests/`
- `data/masks/`
- `data/edits/`
- `data/predictions/`
- `data/results/`
- `data/annotations/`
- `data/provenance/`
- `compute_bundles/`

Outputs must stay under these roots; never write under `/`, the home dir, or the repo root itself.
