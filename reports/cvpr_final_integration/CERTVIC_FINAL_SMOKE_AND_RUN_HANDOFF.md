# Final Smoke and Run Handoff

Local implementation status: `CVPR_PRE_EXECUTION_READY`. Real smoke status:
`REAL_MODEL_SMOKE_PENDING`; every model is PENDING. The exact external sequence is:

1. attach the offline wheelhouse and its rich manifest;
2. attach a verified unified model/processor snapshot for each primary model;
3. run 00A;
4. run 00B for each model;
5. run 00C2 for each model;
6. return all smoke artifacts and run `certvic.cvpr.smoke_gate`.

Do not run scientific notebooks until all three smoke rows are PASS. No real GPU evidence or human
labels are included here; `paper_evidence=false`, Main and COCO execution remain blocked.
