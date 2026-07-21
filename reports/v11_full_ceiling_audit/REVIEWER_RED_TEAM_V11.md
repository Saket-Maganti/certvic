# Reviewer Red Team V11

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Likely reviewer attacks are listed with the evidence needed to answer them, not rhetorical workarounds.

| Reviewer persona | Criticism | Severity / valid? | Current evidence and repair | Experiment or action required | Acceptance threat |
|---|---|---|---|---|---|
| Benchmark skeptic | The 30-item V2 is too small and post-selected. | critical / yes | 30/30 overlap V1; V11 reclassifies it diagnostic and preserves V1. | Powered unseen set with frozen construction and review. | fatal to confirmatory specificity |
| VLM evaluation | Qwen's 12/94 failure may be edit salience, not specificity. | critical / yes | 12 raw flips reproduce; 2 failure boxes intersect conservative target boxes; mechanism unassigned. | Outcome-blind validity plus salience-matched independent controls and pinned rerun. | high |
| Statistics | The 0.10 threshold is arbitrary and observed-rate gating ignores uncertainty. | high / yes | Historical V1 rule remains frozen; prospective CP/Bonferroni rules are separated. | Justify threshold scientifically and lock operating characteristics before results. | high |
| Reproducibility | No independent human validation exists. | critical / yes | Assistant screening overridden; blank two-rater packet and fail-closed validator delivered. | Two raters, adjudication, agreement, raw/filtered sensitivity. | fatal to submission |
| VLM evaluation | Edits may be trivially detectable or contaminate targets. | high / yes | Grouped AUC .7123; 20/94 conservative bbox intersections, zero mask overlap; no causal attribution. | Review, complete pre-result metrics, salience-stratified sensitivity, no post-hoc drops. | high |
| Causal inference | V2 selection saw Qwen outcomes. | critical / yes | Four failures retained and eight filtered; V11 explicitly marks post-selection. | Zero-overlap source pool and immutable pre-output inclusion/exclusion ledger. | fatal to confirmation |
| VLM evaluation | Parser choices could manufacture flips. | medium / addressed for current yes/no | All V1 rows strict-parse; raw text reparses; malformed/contradictory cases fail closed. | Preserve raw outputs and apply the same parser/version to pinned reruns. | low now, high if drift recurs |
| Reproducibility | Model differences may be version, precision, or processor artifacts. | critical / yes | Historical `model_version=unloaded`; V11 notebooks now refuse null revisions and record bundle hashes. | Exact commits, processors, precision, packages, preprocessing, and retry rules. | high |
| VLM evaluation | Three open 7--8B models are not broad coverage. | medium / yes | Three distinct open families, but limited scale/training diversity. | Optional fourth distinct open family only after core blockers; closed model reference-only. | ceiling-limiting |
| Benchmark skeptic | One ADE20K-derived domain cannot support generalization. | high / yes | All real evidence is one household/object setting. | Small preregistered COCO confirmation after specificity repair. | high for main track |
| Statistics | Multiple models and exploratory diagnostics inflate false positives. | high / yes | Paired tests labeled retrospective; Holm applied; Qwen is prospective primary; joint rule Bonferroni. | Freeze confirmatory family and keep diagnostics secondary. | medium after repair |
| Statistics | “Certified” sounds like formal robustness certification. | high / yes | V11 says numerical time-uniform CS crossing, not deployment or perturbation-set robustness; full gate false. | Define guarantee in abstract/method and avoid unqualified certification. | high |
| Hostile novelty | This is a confidence-interval wrapper around another edit benchmark. | critical / unresolved | Best distinction is joint responsiveness vs irrelevant-edit specificity with traceable intervention pairs. | Source-backed related work and baselines that show what ordinary consistency misses. | fatal if not sharpened |
| Benchmark skeptic | The repository is overengineered relative to the science. | high / yes | V11 consolidates into canonical ledgers, one analysis rebuild, one review path, and one execution card. | Stop new wrappers; spend effort on independent items, humans, domain evidence, and paper. | medium |
| Reproducibility | Data/package release may violate licenses or leak paths. | high / yes | V2/reviewer images private; session2 ZIP quarantined; no repository license. | License determination, pointer-only release, exact-archive recursive audit, project license. | high for artifact track |
