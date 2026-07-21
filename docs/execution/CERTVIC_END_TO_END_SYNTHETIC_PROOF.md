
# CertVIC End-to-End Synthetic Proof

The authoritative local proof is deliberately non-empirical:

```bash
python3 -m certvic.cvpr.synthetic_closure --out-dir <NEW_EMPTY_DIR>
```

It executes the confirmatory protected-negative route through generation, QA, strict synthetic
review/adjudication, review-bound exact selection, freeze, and signed synthetic permission. It then
executes the Main attribute route through semantic generation, strict review, freeze, three mock
providers, package, permission-bound atomic import, analysis, paper fragment, and synthetic release.
Finally it builds an exact synthetic COCO-60 feasibility universe: 30 removal, 30 insertion, and 15
per category. Expected top status is `SYNTHETIC_ALL_STUDY_ROUTES_COMPLETE`.

Every artifact is `SYNTHETIC_END_TO_END_FIXTURE`, `paper_evidence=false`, and
`human_reviewed=false`. Synthetic rater identities exercise provenance logic but are not humans. The
proof validates joins and failure behavior only; it cannot support a CVPR result or model claim.
