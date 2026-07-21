# CertVIC CVPR Scientific Protocol

Status: prospectively specified, not executed; `paper_evidence=false`.

## Negative questions and exact selection

The frozen negative policy is `absent_category_protected_scene_v1`: ask about a verified absent
category, protect every annotated object/text region, and place the control only in verified
background. Protected geometry describes the answer-relevant scene, not an invented box for the
absent class. Absence, protected coverage, distance, QA, and unanimous outcome-blind invariance are
mandatory.

Primary and reserve sets are solved jointly by `certvic.exact_backtracking.v1`. The proof artifact
records constraints, achieved counts, conflicts, objective, seed, solver version, and full-manifest
hash with `FEASIBLE_SELECTION_FOUND` or `NO_FEASIBLE_SELECTION_EXISTS`.

CertVIC separates semantic responsiveness from intervention specificity. Original and relevant-edit
pairs measure correct answer updating; original and irrelevant-edit pairs measure inappropriate
answer flips. Primary rows retain raw provider text, parser status/version, image/task/prompt hashes,
and immutable model/processor identities. Certification-critical parsing fails closed.

The historical V1 decision remains observed flip rate <=0.10; Qwen remains 12/94 and fails it.
InternVL is 1/94 and LLaVA is 3/94 under that historical rule only. V2-30 overlaps V1 and remains
retrospective sensitivity evidence. The new `specificity_confirmatory_cvpr` set is outcome-unseen,
zero-overlap, 240 items plus 60 reserve, reviewed before outcomes, and evaluated under a one-sided
exact-binomial rule. Main-500 and COCO confirmation remain gated.

Raw provider artifacts, review sheets, source images, and source manifests are immutable. Derived
normalization is versioned and reproducible. No missing parse is converted into a valid answer; the
confirmatory primary analysis counts a missing/unparseable pair as a flip.


See the locked study YAML for thresholds and strata.
