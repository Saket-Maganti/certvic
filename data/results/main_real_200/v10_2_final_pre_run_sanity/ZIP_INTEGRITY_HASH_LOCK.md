# ZIP Integrity Hash Lock

All zips OK: `true`

| Zip | SHA256 | Members | Expected contents | Actual local private paths | Fake prediction files | OK |
| --- | --- | ---: | --- | --- | --- | --- |
| `dist/certvic_kaggle_main200_bundle.zip` | `12962bb9a0e518c998ae90ddacaac4c372cf10e7761db56c21aaf38ee7e11b77` | 358 | `true` | `0` | `0` | `true` |
| `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip` | `edfa44d3aae4dc9ba7cadde42c11eb3d38de0a6a23a8a92055d21c0dd2269102` | 64 | `true` | `0` | `0` | `true` |

## Top-level Contents

- `dist/certvic_kaggle_main200_bundle.zip`: `README_KAGGLE_BUNDLE.md, certvic, commands, configs, data, docs, notebooks, pyproject.toml, scripts`
- `dist/kaggle_remaining_runs/certvic_spurious_v2_control.zip`: `data`

## Expected Content Notes

- The main code/config zip is checked for runtime code, runbooks, and bundle README. The local Spurious V2 importer is not required inside the Kaggle runtime zip; it is used after downloading provider outputs.
- The Spurious V2 data zip is checked for `pilot_eval_tasks_reviewed.jsonl`, `spurious_v2_manifest.json`, `bundle_manifest.json`, and 60 image files.

## Privacy / Fake Output Notes

- The code/config zip contains allowlisted scanner literals in security source files; these are path-audit constants/examples, not the local host path.
- No actual local host private paths were found inside either zip.
- No provider prediction output files are present in either zip.
