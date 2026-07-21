
# CertVIC Main Final Task Construction Guide

The Main lane is candidate build, prospective engine routing, semantic generation, automated QA,
blinded packet, two qualified independent reviews, agreement, adjudication, final inclusion, exact
family/source-bounded selection, primary/reserve assignment, and freeze. Candidate output is directly
accepted by `certvic.cvpr.semantic_edits`; no schema translation is hidden in the generator.

```bash
python3 -m certvic.cvpr.main_task_builder --source-root <ROOT> --source-manifest <SOURCE.jsonl>   --config configs/studies/main_study_cvpr.yaml --out <CANDIDATES.jsonl> --report <REPORT.json>
python3 -m certvic.cvpr.main_task_builder --qa-enriched-manifest <QA.jsonl>   --final-inclusion-ledger <FINAL_REVIEW.json> --config configs/studies/main_study_cvpr.yaml   --finalize-out-dir <FINAL>
```

Successful finalization writes `main_primary_tasks.jsonl`, `main_reserve_tasks.jsonl`,
`main_exclusions.jsonl`, `main_balance_report.json`, `main_solver_report.json`, and
`main_freeze_manifest.json`. Frozen targets are 500 primary (200 removal, 200 insertion, 100
attribute) and 125 reserve (50/50/25), at most one task per source. The balance report covers family,
category, answer transition, size, position, complexity, difficulty, source diversity, and engine.
Shortage blocks freeze. Every semantic output remains human-review pending until genuine review.
