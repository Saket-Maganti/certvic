# CertVIC CVPR Scientific Protocol

Status: prospectively specified, not executed; `paper_evidence=false`.

## Frozen confirmatory negative-item policy

Expected-answer `no` items use `absent_category_protected_scene_v1`. The queried category must be
verified absent. No false target geometry is assigned to that category; the union of all annotated
objects and text is protected answer-relevant scene geometry. The irrelevant control is placed only
in verified background at least 75 pixels from every protected region. Both outcome-blind reviewers
must accept answer invariance before exact selection. This prospective rule cannot change after model
outcomes are observed.

Generated controls are enriched only by `certvic.cvpr.confirmatory_qa`; manual PASS insertion is
invalid. Exact selection consumes the hash-locked enriched manifest. Main candidates are
annotation-backed and pass the frozen engine/automated-QA policy before human review.

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
