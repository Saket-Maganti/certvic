# CertVIC V5 Prompt — CVPR Reviewer Score Simulator

Read `00_V5_MASTER_CONTEXT.md` first.

Do not initialize git. Do not create commits or tags. Do not use paid services. Do not download datasets or weights. Do not run GPU jobs. Do not run VLM inference. Do not fabricate results. Do not make evidence claims.

Build a structured reviewer-score simulator.

Create:
- `certvic/review/score_simulator.py`

CLI:
`python3 -m certvic.review.score_simulator --paper-dir paper --reports-root data/results --out-dir docs/cvpr_score_simulation`

Reviewer axes:
- novelty
- technical quality
- empirical strength
- clarity
- reproducibility
- construct validity
- significance
- recommendation

Output:
- simulated_reviews.json
- score_distribution.csv
- fatal_weaknesses.md
- action_plan.md

Tests:
- no results lowers empirical score
- strong artifacts raise reproducibility
- fake results not invented
- action plan generated

Docs:
- `docs/V5_CVPR_SCORE_SIMULATOR_REPORT.md`

At the end:
- list files changed
- list tests run
- list commands added
- state whether this prompt passed
- state next prompt
