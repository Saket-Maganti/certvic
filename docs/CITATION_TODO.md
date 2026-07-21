# Citation TODO (V3)

Slots for verified citations, one per related-work category. **Do not fabricate.**
Fill each only with references you have personally verified (author, title, venue,
year). Update `representative_works` in `paper/related_work_matrix.yaml` as you go,
then re-run `certvic.paper.related_work_audit`.

| Category | Citations needed | Status |
| --- | --- | --- |
| VLM evaluation and robustness | several anchor benchmarks | TODO |
| Counterfactual / minimal-pair VQA | minimal-pair / counterfactual VQA works | TODO |
| Causal visual reasoning | interventional / causal visual reasoning works | TODO |
| Image editing for evaluation | inpainting / object-removal-for-eval works | TODO |
| Robustness and consistency | consistency / contrast-set / invariance works | TODO |
| Anytime-valid inference | confidence sequences / betting / e-values | TODO |
| Dataset licensing and artifacts | recipe-first / reproducible-artifact works | TODO |
| Budget-constrained evaluation | sample-efficient / sequential evaluation works | TODO |

## Process

1. Find and verify each reference (do not rely on memory).
2. Add a BibTeX entry to the paper bibliography.
3. Add the cite key to `representative_works` for the category in the matrix.
4. Cite it in `paper/sections/02_related.tex`.
5. Re-run the audit; `unverified_cite_keys` must be empty before submission.
