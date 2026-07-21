# Spurious-Control Quality Audit

`paper_evidence=false`

Items audited: 94

- Missing or invalid image pairs: 0
- Shape mismatches: 0
- Patch bbox intersects target bbox: 20
- Patch overlaps target mask at threshold 20: 0
- Detectability AUC: 0.7123
- Artifact risk flag: False
- High-detectability items: 19

Patch geometry was recomputed from the preserved image pairs, while target-mask geometry was reused from the frozen derived-real-evidence audit because the external ADE annotation tree is not currently mounted. This is not a fresh annotation rerun. This is objective CPU forensics, not human validation.

No target-mask overlap was found, but 20/94 patch bboxes intersect target bboxes. Bbox intersection is conservative and can overstate true object contact, but it is the requested objective pathology rule.
