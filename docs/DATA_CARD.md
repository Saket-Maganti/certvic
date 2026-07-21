# Data Card

CertVIC uses a recipe-first data policy:

- store source pointers and hashes
- store masks, edit parameters, and manifests
- re-host only CC0/public-domain or otherwise verified redistributable pixels
- keep research-only or pointer-only data as recipes
- track release mode for every source

Humans validate edit validity only: photorealism, single-factor validity, and
answer-change unambiguity. Humans do not create the primary labels; labels come
from controlled edits.

Pilot/main releases must include license verification and a drop list for items
that fail validity checks.

## ADE20K Pointer Policy

ADE20K inputs are user-provided local files. CertVIC does not download ADE20K,
copy pixels into release artifacts, or mark pixels as rehostable by default.
V1.3 source records use `pointer_only`, `redistribution_allowed=false`, and
`recipe_only` release mode unless redistribution terms are explicitly verified.

The V1.3 ADE20K adapter can create manifest-only mask records from semantic PNG
annotations. Each record stores the annotation pointer, label ID, bbox, area
fraction, and regeneration metadata. If label names are unavailable, labels are
recorded conservatively as `ade20k_label_<id>`.

Binary mask PNG export is disabled by default and must be explicitly requested.
Even exported local masks are not evidence by themselves and are not release
assets unless redistribution is verified.

V1.4 adds candidate selection, edit-plan, task-preview, and pilot-plan review
artifacts. These artifacts stay recipe-first and non-evidence:

- selected rows are `CANDIDATE_ONLY`
- edit-plan rows are `PLANNED_ONLY`
- task-preview rows are `PREVIEW_ONLY`
- rejected candidates record feasibility reasons
- no edited images are generated
- no VLM inference is run
- no evidence claims are enabled

Before V1.5 generation, manually inspect selected source/mask/label rows,
rejected candidates, release posture, task-family mapping, edit-type mapping,
mask areas, bboxes, and leakage summaries.

V1.5 simple generation creates tiny local edited images for quality-gate review
only. Generated rows use `GENERATED_EDIT_ONLY`; materialized tiny task rows use
`EDIT_READY_NON_EVIDENCE`. These images and task rows are not paper evidence and
do not imply VLM behavior.

Quality gates check structural image/edit properties, including mask area, bbox
validity, inside/outside change fractions, edit-specific allowed regions, image
size match, edited file/hash presence, changed-region non-emptiness, and simple
artifact warnings. Human validity checks are still required before any model
evaluation.

This remains non-evidence before accepted quality-gated edits, human validity
checks, and open local model runs.

## Label policy (V2)

`configs/ade20k_label_policy.yaml` maps ADE20K semantic label ids to eligible
task families and allowed edit types. It is an unverified template: the
label_id -> name mapping must be confirmed against the specific ADE20K release
before evidence runs. Background "stuff" labels (wall, sky, floor, ceiling,
road) are blocked from manipulation. Labels absent from the policy are treated
as unresolved and are eligible only for control (no-change) edits, so construct
validity is never silently assumed for an unknown object. Policy version and
hash are recorded in selection and edit-plan summaries for provenance.

## Visual review (V2)

Generated edits and materialized tasks pass through a human visual-review sheet
(photorealistic / single_factor / target_object_clear / required_change_unambiguous
/ prompt_answerable / keep_for_eval, each yes/no/uncertain). Items failing the
drop rule are removed; approved tasks are tagged HUMAN_REVIEWED_NON_EVIDENCE.
The sheet and gallery contain no model predictions; pixels are not copied by
default and no external services are used.

## Generated data card (V2)

`certvic.release.data_card` produces a recipe-first data card (source/mask counts,
license categories, task families) from manifests. Pixels are never redistributed.

## Storage and path policy (V3)

Dataset pixels (ADE20K) are never rehosted; the root is user-supplied at run time
and never committed or released (see `docs/STORAGE_AND_PATH_POLICY.md`). Storage
for a study is estimated conservatively before running:

```bash
python3 -m certvic.storage.plan_storage --config configs/real_pilot_ade20k.yaml --scale 2000 --out data/results/storage_plan_2000.json
```

Output paths are audited for private absolute paths, Kaggle-unsafe names, symlink
escapes, and unsafe overwrite roots. Rejected-edit pixels are hashed into the run
ledger and then pruned to reclaim disk.

## Scaled human review (V3)

At 1k–2k scale, visual review is split across reviewers with a balanced,
stratified batching that overlaps a subset for inter-annotator agreement:

```bash
python3 -m certvic.validation.review_batches --tasks data/manifests/pilot_eval_tasks_tiny.jsonl --out-dir data/annotations/review_batches --reviewers reviewer_a reviewer_b --overlap-rate 0.2 --seed 0
python3 -m certvic.validation.review_progress --ratings-dir data/annotations/review_batches --out data/annotations/review_progress.json
python3 -m certvic.validation.adjudicate_review --ratings data/annotations/visual_review_ratings.csv --out data/annotations/visual_review_adjudicated.csv
```

Review sheets contain no model outputs; no paid annotation services are used.
Disagreements are adjudicated by majority vote with ties flagged for a human. See
`docs/HUMAN_REVIEW_OPERATIONS.md`.

## Privacy audit before release (V3)

The recipe-first artifact never rehosts pixels. A security/privacy audit verifies
no private paths, secrets, `.env` files, paid endpoints, or accidental pixels ship:

```bash
python3 -m certvic.security.release_privacy_audit --root . --release-dir release/certvic_recipe_artifact --out docs/SECURITY_PRIVACY_AUDIT.md
```

See `docs/SECURITY_PRIVACY_POLICY.md`.
