# Local Run Dashboard (V3)

A self-contained static HTML dashboard over whatever run artifacts exist locally:
runs, metrics, quality gates, review progress, claim eligibility, and
provenance/artifacts. Static files only — **no external services, no JS
framework, no pixel copying**. It highlights missing gates and non-evidence flags
so nothing reads as evidence that is not.

## Module

`certvic.dashboard.build_dashboard` — scans the results root (and sibling
`predictions/`, `provenance/`, `annotations/` roots), aggregates artifacts, and
writes `index.html` + one page per section + `dashboard_data.json`.

## Pages

`index` (overview: certified-claim badge, missing gates, non-evidence flags),
`runs`, `quality`, `review`, `metrics`, `claims`, `artifacts`. Every collector
tolerates missing inputs — an empty project renders cleanly with the gaps flagged.

## Command

```bash
python3 -m certvic.dashboard.build_dashboard \
  --results-root data/results --out-dir data/dashboard
```

Optional `--predictions-root`, `--provenance-dir`, `--annotations-dir` (default to
siblings of the results root). Open `data/dashboard/index.html` in a browser.

## Safety

CSS is inlined; there are no external `http(s)` resources and no `<script src=...>`
(verified by test). The dashboard copies no pixels, runs nothing, and makes no
evidence claim (`evidence_claims_made=false`, `external_services_used=false`,
`pixels_copied=false`). Non-evidence statuses (`MOCK_ONLY`, `SIMULATED_ONLY`, …)
and any `paid_services_used` run are surfaced on the overview page.
