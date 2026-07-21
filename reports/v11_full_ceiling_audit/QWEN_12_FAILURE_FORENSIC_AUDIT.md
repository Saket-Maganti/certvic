# Qwen 12-Failure Forensic Audit

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

The frozen V1 Qwen failures were reconstructed from raw paired rows without changing membership.

## Reproduced failures

- `sflip_car_ADE_train_00002029`
- `sflip_car_ADE_train_00002034`
- `sflip_car_ADE_train_00003061`
- `sflip_chair_ADE_train_00000194`
- `sflip_chair_ADE_train_00000268`
- `sflip_chair_ADE_train_00000436`
- `sflip_chair_ADE_train_00000617`
- `sflip_chair_ADE_train_00000630`
- `sflip_chair_ADE_train_00001105`
- `sflip_sofa_ADE_train_00000704`
- `sflip_sofa_ADE_train_00000719`
- `sflip_table_ADE_train_00000377`

Every listed pair changes from parsed `yes` on the original to parsed `no` on the edited image.
All 188 Qwen rows parse; item/variant keys are complete and unique; provider and run metadata are
internally consistent. InternVL and LLaVA do not flip on these twelve items. No parser, missing-row,
duplicate-row, or image-key defect explains the Qwen count.

The compact row-level table at
`analysis/supported_results/qwen_12_forensic_table.csv` records each source ID, both image paths and
SHA-256 values, prompt, expected answers, raw and parsed answers for all three providers, parse
status, objective overlap/distance metadata, and exclusion status. The outcome-blind image packet is
`human_review_packet/reviewer_bundle/tracks/diagnostic_subset12`; its reviewer materials do not
contain provider identity, failure status, source IDs, or the coordinator selection key.

Two failures have conservative difference bounding boxes that intersect the target box; all twelve
have zero target-mask overlap. This supports targeted follow-up, not an exclusion after viewing
outcomes. Machine-generated visual categories in historical forensics are diagnostics only and do
not establish validity or mechanism.

The defensible conclusion is narrow: Qwen shows model-specific sensitivity on these irrelevant-edit
pairs. Architecture, quantization, processor behavior, or visual salience cannot be separated with
the present unpinned runs and incomplete human review.
