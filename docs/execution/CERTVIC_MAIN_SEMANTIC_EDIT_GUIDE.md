
# CertVIC Main Semantic Edit Guide

Status: implementation complete; scientific generation and human validity are external;
`paper_evidence=false`.

Main tasks must set `required_change=true`, name one of `object_removal`, `object_insertion`, or
`attribute_modification`, provide original and edited expected answers that differ, and bind the
question, source bytes, target mask or box, edit parameters, and expected transition into the task
hash. `certvic.cvpr.semantic_edits` provides deterministic preliminary removal, hash-locked insertion,
and mask-scoped attribute edits. Every output is `MACHINE_ASSISTED_PRELIMINARY` and
`HUMAN_REVIEW_PENDING`; image metrics cannot certify the semantic transition.

Optional inpainting uses `OfflineInpaintingAdapter`: verify every local snapshot byte, load once,
enable attention/VAE slicing, generate batches, halve on OOM, and release once. It is never silently
substituted for a required path. The `10_main_study_generation_T4x2.ipynb` notebook launches both
visible workers concurrently and applies `MAX_ITEMS` once before sharding.
