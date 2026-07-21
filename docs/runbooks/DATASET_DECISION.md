# Which ADE20K archive does CertVIC use?

**Answer: `ade20kdataset/ade20k.zip` → `ADEChallengeData2016/`.**

Point `ADE20K_ROOT` at the extracted `ADEChallengeData2016/` directory.

## Why (verified against the code, not assumed)

`certvic/data/ade20k_adapter.py` requires a layout with an **`images/`** directory
and an **`annotations/`** directory, each split into `training/` + `validation/`,
where annotations are **semantic-index PNGs** (`build_ade20k_manifests` raises
otherwise — adapter line 203; config `mask_manifest_mode: semantic_png_manifest_only`).
Running the adapter's inspector on the extracted root returns:

```json
{ "layout_status": "supported_layout", "mask_parser_status": "semantic_png_supported",
  "supported_for_mask_manifest": true, "matched_pair_count": 22210,
  "train_image_count": 20210, "val_image_count": 2000, "warnings": [] }
```

## Why not the other two

| Archive | Size | Contents | Verdict |
| --- | --- | --- | --- |
| **`ade20k.zip`** | 1.18 GB | `ADEChallengeData2016/{images,annotations}/{training,validation}/` — semantic-PNG masks, `objectInfo150.txt`, `sceneCategories.txt` | ✅ **Exact match.** 22,210 image/annotation pairs. |
| `ADE20K-main.zip` | 5.3 MB | CSAILVision GitHub **toolkit** repo (`ADE20K_2021_17_01`): per-image `.json` + per-instance PNGs, only a one-image sample | ❌ Code/toolkit, not the dataset; per-instance format, no `annotations/{training,validation}` → unsupported layout. |
| `ade20k-DatasetNinja.tar` | 6.37 GB | DatasetNinja **Supervisely** export: `{train,validation}/ann/*.json` (polygon JSON) + `img/` | ❌ Annotations are JSON, not semantic PNG → `parser_required`, mask manifest cannot be built. |

## Extraction (done)

Extracted **outside** the repo because `certvic/storage/dataset_roots.py`
`validate_root` flags a root located inside the repo (risk of committing/packaging
pixels; CertVIC is recipe-first and never rehosts pixels):

```bash
# extract OUTSIDE the repo (a sibling dir); never commit pixels
unzip -q ade20kdataset/ade20k.zip -d "$HOME/ade20k_root"
export ADE20K_ROOT="$HOME/ade20k_root/ADEChallengeData2016"
```
