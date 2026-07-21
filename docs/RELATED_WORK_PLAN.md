# Related Work Plan (V3)

A non-fabricating scaffold for the related-work section. It fixes the **categories**
and CertVIC's **positioning** in each, but contains **no invented citations** —
real references are added by a human after verification (see `docs/CITATION_TODO.md`).
The machine-readable matrix is `paper/related_work_matrix.yaml`; the audit is
`certvic.paper.related_work_audit`.

## Categories and positioning

1. **VLM evaluation and robustness** — orthogonal: decision-update under a
   controlled change, not fixed-image accuracy.
2. **Counterfactual / minimal-pair VQA** — real images, recipe-documented,
   single-factor-validated pairs; certified gap, not point estimate.
3. **Causal visual reasoning** — we measure consistency under a known
   answer-changing edit; we explicitly avoid causal-cognition overclaims.
4. **Image editing for evaluation** — edit realism / single-factor validity are
   *measured* (quality gates + IAA + detectability probe), not assumed.
5. **Robustness and consistency** — consistency against an edit-derived expected
   answer change, certified anytime-validly.
6. **Anytime-valid inference** — confidence sequences / betting tests applied to
   an evaluation gap; the core methodological contribution.
7. **Dataset licensing and reproducible artifacts** — recipe-first, pixels never
   rehosted, zero-cost reproducibility.
8. **Budget-constrained evaluation** — free-compute-only; a small certified study
   suffices under anytime-valid CS.

## Rules

- Never invent authors, titles, venues, or years.
- Keep novelty claims qualified and defensible; the audit flags phrases like
  "first to" / "novel" for human review.
- `representative_works` stay empty until verified citations are added.
