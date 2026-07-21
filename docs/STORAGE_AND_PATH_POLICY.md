# Storage and Path Policy (V3)

Prevents disk blowups, private-path leaks, broken symlinks, duplicate output
roots, and release packaging mistakes before large studies. Planning only — no
real dataset scanning unless a root is explicitly supplied, no downloads, no
paid services.

## Modules

| Module | Purpose |
| --- | --- |
| `certvic.storage.path_policy` | Pure path-safety checks: private absolute paths, Kaggle-unsafe names, symlink escapes, unsafe overwrite roots. |
| `certvic.storage.dataset_roots` | Dataset-root policy doc + opt-in (non-scanning) root validation. |
| `certvic.storage.plan_storage` | Conservative storage estimate by category at a target scale, with free-tier and path-policy warnings. |

## Path policy rules

- **Private absolute paths** (`/Users/...`, `/home/...`, the home dir) must never
  appear in committed configs or release artifacts.
- **Kaggle-safe names** are restricted to `[A-Za-z0-9._/-]` (no spaces) so dataset
  slugs and file paths survive Kaggle.
- **Symlink escapes** — a path resolving outside its declared root — are flagged.
- **Unsafe overwrite roots** — `/`, the home dir, the cwd, or the repo root — are
  never valid output targets.

## Dataset roots

CertVIC is recipe-first: dataset pixels (ADE20K) are never rehosted, the root is
supplied at run time (`--ade20k-root <ROOT>` or `ade20k_root` in config), never
hard-coded or committed, and automatic downloads are disabled. Outputs live under
`data/` (and `compute_bundles/`), never under a system or home root.

```bash
python3 -m certvic.storage.dataset_roots --out data/results/dataset_root_policy.md
# optional, no scanning:
python3 -m certvic.storage.dataset_roots --validate-root /path/to/ADE20K --out /tmp/policy.md
```

## Storage estimates

Conservative per-item byte estimates (photorealistic edits dominate): kept edits
~350 KB each, rejected edits the same until pruned, masks ~30 KB (only if binary
masks are exported), review-gallery thumbnails ~60 KB, predictions ~2.5 KB per
item × model × variant. Free-tier envelopes: Kaggle `/kaggle/working` ~20 GB,
Colab disk ~70 GB. A diffusion weight cache (~6 GB) is reported separately and
should be loaded from a Kaggle **input** dataset, not the working dir.

```bash
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 200  --out data/results/storage_plan_200.json
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 2000 --out data/results/storage_plan_2000.json
```

Reference estimates (default 2.5× overgeneration, 3 models):

| Scale | Working set | Fits Kaggle (~20 GB)? | Dominant category |
| --- | --- | --- | --- |
| 200 | ~0.18 GB | yes | edits (kept + rejected) |
| 2000 | ~1.8 GB | yes | edits (kept + rejected) |

The planner warns when rejected-edit pixels exceed kept-edit pixels — record
their hashes in the run ledger, then delete rejected pixels to reclaim disk.
