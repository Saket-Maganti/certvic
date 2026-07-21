# Confirmatory construction

Inputs are licensed ADE20K validation bytes, a verified source manifest, the frozen exclusion
inventory, frozen study config, code bundle, and the passing real-model smoke handoff. Use Kaggle T4x2
for `01_specificity_confirmatory_generation_T4x2.ipynb`; expected runtime is 2–8 hours.

Generate outcome-unseen candidates, protected-region controls, QA records, and reserve oversampling.
Validate zero overlap with V1 and V2-30, exact source/image hashes, licenses, geometry, quality,
balance, and deterministic queue resume. Then export the blinded review packet; no provider outcome
may be present.

The outputs are candidate and QA manifests, image pairs in the private task workspace, a packet
manifest, and blank rater sheets. They remain `paper_evidence=false` and `HUMAN_REVIEW_PENDING`.

Resume only from the frozen job queue. A generation failure may retry its exact job parameters; never
replace items or change thresholds after seeing a real provider outcome.

