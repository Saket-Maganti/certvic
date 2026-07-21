# Paper Figure & Table Plan (post-3-model pilot)

**PILOT ONLY.** Scaffold sections live at `paper/sections/pilot_results_main200.tex` and
`paper/sections/limitations_current_pilot.tex`; both pass `paper_numbers_guard`
(numbers injected via `\input` of generated tables + a provenance manifest, never hand-typed)
and `claim_language_guard`.

## Tables (generated; do not hand-edit)

| ID | content | source artifact | generator |
|---|---|---|---|
| T1 | 3-model intervention ($a$, $p$, $\Delta$, CS LB/UB, certified, parse-fail) | `data/results/main_real_200/tables/main200_multimodel_results.tex` | `scripts/build_main200_paper_tables.py` |
| T2 | absent-object control (absent/present accuracy, n) | `tables/main200_control_results.tex` | same |
| T3 | per-edit-type (remove/occlude/displace; control_irrelevant = not_available) | `tables/main200_per_edit_type.csv` | same |

`\input` provenance is tracked in `paper/pilot_results_provenance.json` (entries marked
eligible = real run, still pilot-only).

## Figures (planned — generate from canonical artifacts only)

| ID | content | source | status |
|---|---|---|---|
| F1 | per-model CS trajectory on $\Delta$ (lower bound vs item index) | `pilot_report*/pilot_result.json` → `presence_intervention.certification.confidence_sequence` | data available; figure not yet rendered |
| F2 | $\Delta$ bar chart across the three models | `multimodel_pilot_summary.json` | data available |
| F3 | natural-absence vs edited-absence dissociation | control vs intervention | data available |
| F4 | qualitative failure gallery (paths + hashes; pixels not duplicated) | `failure_gallery/gallery.json` | candidate examples selected; render on demand |
| F5 | mechanism-probe dissociation (anchoring vs residual vs prompt) | `mechanism_probes/` | **pending** probe predictions |

## Section → artifact map

- §Pilot Results → T1, T2, T3, F1–F3 (all from canonical `pilot_report*/`).
- §Limitations → no numbers; references the project-state memo.

## Rules honored

- No citations added (add only verified references when scaled).
- No final/paper-grade or "state of the art" language; pilot-only throughout.
- Every number traces to a generated table or a `%`-comment artifact reference.
- Figures that depend on un-run arms (F5) are marked pending, not fabricated.

## Build / verify

```bash
python3 scripts/build_main200_paper_tables.py
python3 -m certvic.validation.paper_numbers_guard \
  --results paper/sections/pilot_results_main200.tex paper/sections/limitations_current_pilot.tex \
  --manifest paper/pilot_results_provenance.json
python3 -m certvic.validation.claim_language_guard \
  --root paper/sections data/results/main_real_200 --out /tmp/clg.md
```
