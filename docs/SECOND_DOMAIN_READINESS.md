# Second-Domain Readiness (free / open data)

**Status: readiness assessment, NOT evidence**
(`evidence_status = READINESS_ASSESSMENT_NON_EVIDENCE`). No dataset is downloaded here.

A single ADE20K domain is a paper weakness. A second domain improves external validity —
but only if its **masks**, **object classes**, and **license/provenance** support the
CertVIC edit-and-recheck protocol. License facts below are standard/public and **still
require manual confirmation** against the specific release before any evidence run.

Machine-readable: [`registry/datasets/second_domain_candidates.json`](../registry/datasets/second_domain_candidates.json).

## Scoring criteria (weights)

mask availability (3) · class overlap with table/sofa/chair/car (3) · license compatibility
(3) · edit suitability (3) · free feasibility / size (2) · expected reviewer objections — low
(2) · annotation-format simplicity (1) · review burden — low (1). Each scored 1–5; weighted
total out of 90.

## Ranking

| # | candidate | weighted | % | usable now? |
|---|---|---|---|---|
| 1 | **COCO 2017 (instances + panoptic)** | 80 | 88.9% | yes |
| 2 | LVIS v1 | 78 | 86.7% | yes |
| 3 | Open Images V7 (segmentation subset) | 66 | 73.3% | yes (more plumbing) |
| 4 | Cityscapes | 57 | 63.3% | **blocked** |
| 5 | SA-1B (Segment Anything) | 43 | 47.8% | **blocked** |

## Blocked candidates (and why)

- **SA-1B** — masks are **class-agnostic** (no semantic labels), so we cannot form
  object-named presence questions without an extra labeling pass; and ~11M images / ~10TB
  is not free-tier feasible.
- **Cityscapes** — non-commercial research license + mandatory registration friction, and a
  driving-only domain with no household-object overlap.

## Top 2 (recommended path)

1. **COCO 2017 (instances/panoptic)** — direct class overlap (`chair`, `couch`→sofa, `car`,
   `dining table`→table); **instance masks** are ideal for clean single-object removal;
   annotations are CC-BY 4.0; mature CPU tooling (pycocotools); a free **val2017** subset
   (~5k images) is enough for a pilot. Image pixels stay un-redistributed (same policy as
   ADE20K). Lowest-friction independent second domain.
2. **LVIS v1** — instance masks + 1200 classes for diversity, but it is **built on COCO
   images**, so it is not a fully independent domain (a reviewer may flag image overlap with
   a COCO arm). Best as a *class-diversity* extension rather than a separate domain.

## Recommendation

**Add COCO 2017 as the next domain.** A minimal, import-safe pointer stub already exists at
`certvic/data/coco_adapter_stub.py` (class-overlap map + a loader that refuses to download).
Build the full adapter only once COCO is explicitly selected.

## Hard rules honored

- No dataset downloaded; no paid/restricted data touched.
- No dataset is claimed usable without its license/provenance recorded **and** a
  `requires_manual_verification` list.
- No full adapter built — only a pointer stub for the recommended candidate.

## Exact next local check

```bash
# Confirm nothing COCO is already local, then plan a small val2017 subset (do NOT download yet):
ls ade20k_root ade20kdataset
find / -iname 'instances_val2017.json' 2>/dev/null | head
python3 -c "from certvic.data.coco_adapter_stub import adapter_summary; print(adapter_summary())"
```
