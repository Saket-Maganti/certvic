# CertVIC V6 Prompt — Minimum Viable CVPR Bar Checker

Read `00_V6_MASTER_CONTEXT.md` first.

You are correcting project direction, not building generic infrastructure.

Hard constraints:
- Do not initialize git.
- Do not commit or tag.
- Do not use paid APIs.
- Do not use paid cloud.
- Do not download data or weights.
- Do not run GPU jobs.
- Do not run VLM inference.
- Do not fabricate results.
- Do not fabricate citations.
- Do not insert fake paper numbers.
- Do not make evidence claims from mock/smoke/simulated/planned/unreviewed/simple-edit-only artifacts.
- Keep tests local and CPU-only.
- Heavy dependencies must be optional/import-safe.

Create a checker for whether the empirical package meets borderline/weak/strong CVPR bars.

Create:
- `certvic/review/cvpr_bar_checker.py`
- `configs/cvpr_bar_thresholds.yaml`

Bars:
- borderline
- weak_accept
- strong_accept
- highlight_possible

Thresholds include:
- reviewed item count
- model count
- IAA
- detectability AUC
- control flips
- parse failures
- certified lower bound
- ablations present
- main figure/table present
- related work/proof complete

CLI:
`python3 -m certvic.review.cvpr_bar_checker --results-root data/results --out docs/CVPR_BAR_CHECK.md --json-out data/results/cvpr_bar_check.json`

Tests:
- no-data state fails
- moderate fixture reaches borderline only
- strong fixture reaches strong_accept
- missing detectability blocks

At the end report:
- files changed
- tests added/updated
- commands added
- docs added
- verification commands run
- whether this prompt passed
- next prompt
