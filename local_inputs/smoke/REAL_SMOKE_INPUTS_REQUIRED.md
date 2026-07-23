# Two real licensed smoke items are required

Current status: `BLOCKED_BY_TWO_REAL_LICENSED_SMOKE_ITEMS`.

The repository does not currently contain two items that satisfy the real-model
smoke boundary. Existing CertVIC smoke images are synthetic fixtures. Existing
ADE20K-derived pilot images and edits do not have an affirmative item-level
`license_eligible: true` declaration with a concrete `license_id`; the active
source registry also prohibits redistributing those source bytes without
external verification.

Do not rename the template to `real_smoke_tasks.jsonl` until every placeholder
has been replaced and the license assertion has been independently verified.
The executable manifest must contain exactly two JSON objects, one per line,
at:

`local_inputs/smoke/real_smoke_tasks.jsonl`

Each row must contain:

- a unique, non-placeholder `item_id`;
- `original_image_path` and `edited_image_path` pointing to real regular files;
- an optional `mask_path` pointing to a real regular file;
- `license_eligible: true`;
- a concrete, auditable `license_id`;
- a 64-character lowercase SHA-256 `prompt_template_hash`;
- a non-placeholder `parser_version`;
- a 64-character lowercase SHA-256 `run_contract_hash` shared by the three
  provider-specific 00C2 runbooks;
- `synthetic_fixture: false`;
- `paper_evidence: false`.

Expected source layout:

```text
local_inputs/smoke/assets/<item_id>/original.<ext>
local_inputs/smoke/assets/<item_id>/edited.<ext>
local_inputs/smoke/assets/<item_id>/mask.<ext>   # optional
```

All item IDs and all asset bytes must have zero overlap with historical
manifests. Symlinks and duplicate asset bytes are rejected. When the two
qualified rows and files exist, run:

```bash
python3 local_operator/pre_smoke_operator.py prepare
```

That command uses the canonical smoke builder, verifies the resulting bundle,
and only then issues the three single-use `REAL_MODEL_SMOKE` permissions.
Confirmatory, Main, COCO, scientific execution, and paper evidence remain
unauthorized.
