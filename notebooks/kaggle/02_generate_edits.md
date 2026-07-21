# 02 Generate Edits

Purpose: create controlled edits from source and mask manifests.

Use CPU smoke fallback for tests. Optional SD2 inpainting requires local/free
weights and must checkpoint after every batch.

Outputs: edited images plus `data/manifests/edits.jsonl`.

Resume by skipping edit IDs already present in the output manifest.
