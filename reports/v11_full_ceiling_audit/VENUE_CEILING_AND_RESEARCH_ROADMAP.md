# Venue Ceiling and Research Roadmap

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Venue fit is conditional and does not predict acceptance.

| State | Evidence and maturity | Best-fit level | Ceiling limits |
|---|---|---|---|
| Current | Real pilot outputs; incomplete human validity; one domain; retrospective V2 only | benchmark/evaluation workshop or internal technical report | not main-conference ready |
| Minimum credible completed | Blinded review, pinned three-model rerun, powered unseen specificity control, complete release | WACV or strong evaluation workshop; possible specialized conference paper | breadth and novelty comparison remain limited |
| Highest realistic | Powered Main-500, independent specificity, second-domain confirmation, source-backed novelty, full anonymous release | CVPR/ICCV/ECCV or ML evaluation venues if empirical story is strong | acceptance depends on novelty and evidence, not tooling volume |
| Journal extension | Multi-domain, broader models, longitudinal/version robustness, mature theory and release | TPAMI or IJCV candidate | requires substantially more evidence than the current pass |

## Venue fit by completed state

| Venue | Current fit | Minimum credible completed fit | Highest realistic requirement |
|---|---|---|---|
| WACV | weak pilot/workshop today | best-fit first full venue after human review, unseen specificity, pinned runs, and release | stronger domain confirmation improves odds |
| CVPR / ICCV / ECCV | not ready | still risky without breadth/novelty comparison | powered Main-500, one independent domain, clear scientific story, full artifact |
| NeurIPS / ICML / ICLR | not ready | poor fit as a vision-only benchmark | methodology must generalize beyond one visual benchmark with strong statistical/evaluation baselines |
| benchmark/evaluation workshops | suitable for transparent pilot discussion | strong fit after mandatory blockers | useful launch venue, not evidence of main-track ceiling |
| TPAMI / IJCV | not journal-ready | insufficient breadth | multi-domain, broader models/scales, longitudinal replication, deeper theory, mature public benchmark |

## Prioritized research plan

| Level / action | Scientific question | Required input / current status | Expected evidence | Compute / human burden | Dependency / acceptance value / stop condition |
|---|---|---|---|---|---|
| L1: pilot91 + V1-94 blinded review | are the intended and irrelevant edits visually valid? | private packet ready; labels pending | two raw sheets, adjudication, agreement, raw/filtered sensitivity | CPU only / high human | before unblinding new outputs; critical; stop on unresolved validity or pool overlap |
| L1: independent specificity set | does specificity hold on outcome-unseen controls? | source archive and TBD rules unresolved | immutable tasks/images/hashes and pre-output exclusions | local prep + image generation / high human | after rule/source lock; critical; stop if power/quality/source independence fails |
| L1: pinned three-model execution/import | do Qwen and comparators pass prospective specificity? | static notebooks/importer ready, revisions and real outputs absent | schema-v3 raw rows, manifests, one-sided decisions | free Kaggle GPU / low human after review | after independent set; critical; stop on any hash/key/parse/revision mismatch |
| L1: specificity sign-off | which model-dependent narrative is supported? | analysis specification ready | raw and validity-filtered gate ledger | CPU / scientific sign-off | after import; critical; stop if conclusion changes under predeclared sensitivity |
| L2: balanced Main-500 | does responsiveness remain strong across powered strata? | design locked, execution NO-GO | powered primary/stratified estimates and CS | high GPU/edit generation / high review | only after GO; main-track value; stop if quality cells cannot be filled prospectively |
| L2: small COCO confirmation | does the separation generalize across image/annotation distribution? | ranked plan only; no assets/license verification | preregistered cross-domain interaction and replication | medium GPU / medium review | after specificity; high reviewer value; stop if license or semantic mapping fails |
| L2: paper/literature/release completion | is the protocol novel, interpretable, and reproducible? | V11 draft/audit ready; bibliography/license absent | source-backed comparisons, anonymous pointer-safe artifact | low compute / high researcher | parallel after L1; critical; stop unsupported priority claims |
| L3: fourth complementary open family | is behavior architecture/training-family dependent? | optional, no model selected | pinned paired replication | medium/high GPU / no new review if same locked items | after core evidence; moderate value; stop if it delays L1/L2 |
| L3: prompt/edit-family replication | are findings stable to prompt and control construction? | diagnostics exist but are exploratory | preregistered sensitivity and replication | medium GPU / targeted review | after primary result; moderate value; stop when qualitative conclusion is stable |
| L4: multi-domain/longitudinal benchmark | how stable is specificity across domains, scales, and model versions? | not started | several domains, repeated commits, public benchmark governance | very high / very high | journal only; stop if first extension adds no new scientific interaction |
| L4: deeper theory/challenge | can the empirical certificate support a reusable evaluation theory? | current theorem scope limited | formal assumptions, external replication, challenge protocol | high research / community | TPAMI/IJCV ceiling; stop before inventing guarantees unsupported by executable estimands |

NeurIPS, ICML, and ICLR become plausible only if the statistical/evaluation methodology generalizes
beyond a vision benchmark and is compared rigorously with strong baselines. The shortest path is:
two-rater blinded review of pilot91 and V1-94; build a powered independent unseen control; pin and run
the existing model matrix; decide the specificity branch; then unlock Main-500 and a small second domain.
