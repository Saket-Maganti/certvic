# 01 Make Masks

Purpose: build mask manifests from existing dense masks first.

Inputs: local/pointer source manifest and optional dense labels.

Outputs: `data/manifests/masks.jsonl`.

Use existing masks when possible. Optional SAM/Grounded-SAM hooks must cache
weights and avoid paid segmentation APIs.

Verify by checking mask dimensions, bbox validity, and source IDs.
