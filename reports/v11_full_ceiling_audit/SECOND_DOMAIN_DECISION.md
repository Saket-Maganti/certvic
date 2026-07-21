# Second-Domain Decision

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Decision: prepare a small COCO-2017 confirmatory plan after specificity repair; execute no second domain now.

## Existing repository ranking

| Rank | Candidate | Weighted score / 90 | Percent | Blocked in registry |
|---|---|---|---|---|
| 1 | COCO 2017 (instances + panoptic) | 80 | 88.9% | False |
| 2 | LVIS v1 | 78 | 86.7% | False |
| 3 | Open Images V7 (segmentation subset) | 66 | 73.3% | False |
| 4 | Cityscapes | 57 | 63.3% | True |
| 5 | SA-1B (Segment Anything) | 43 | 47.8% | True |

The scoring registry evaluates class overlap, edit suitability, masks, licensing, free-compute
feasibility, annotation simplicity, review burden, and likely reviewer objections. These are
planning scores, not observed evidence, and the stored licensing notes require current primary-source
verification before acquisition or release.

## Decision and scope

Current real evidence is ADE20K-derived and concentrated on household/object-presence questions.
No ready, license-verified second-domain asset pool is present locally. COCO 2017 ranks first at
80/90 because it overlaps chair/couch/car/table while offering instance masks and a practical small
validation split; LVIS is second but shares COCO pixels, Open Images adds pipeline burden,
Cityscapes has domain/license friction, and SA-1B lacks semantic labels at impractical scale.

After an independent specificity set passes its validity/import gates, prepare only a small,
preregistered COCO confirmation using pointer-only image handling. Its purpose is to test whether
the responsiveness--specificity separation survives a different image/annotation distribution.
Do not let this main-paper confirmation expand into a multi-domain journal program. TPAMI/IJCV scope
may later add multiple domains, longitudinal model versions, and broader interaction analysis.
