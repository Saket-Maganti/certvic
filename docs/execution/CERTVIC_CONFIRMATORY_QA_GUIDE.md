# Confirmatory QA Guide

Run `certvic.cvpr.confirmatory_qa` after generation and before selection. It recomputes source/output
hashes, geometry overlap/distance, changed fraction, MAD, SSIM-equivalent, contrast, edges,
perceptual distance, salience, corruption, dimensions, engine provenance, and deterministic PASS/FAIL
states. Selection rejects rows without the computed enrichment schema/source marker. Expected-answer
`no` items use `absent_category_protected_scene_v1`: the queried class is absent, all annotated
objects/text form the protected geometry, and the edit is placed only in verified background.
