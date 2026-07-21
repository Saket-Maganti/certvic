# V6 Main Figure and Table Plan

The main paper story is detectability versus certified decision-update gap.

Required main figure:
- x-axis: edit detectability AUC
- y-axis: certified decision-update gap lower bound, or descriptive gap if not certified
- chance line at 0.5
- danger region for AUC >= 0.8
- point per model, family, and task family
- paired qualitative triptychs nearby

Required main table:
- n valid
- naive gap
- validity-gated gap
- certified lower bound
- detectability AUC
- control spurious-flip rate
- parse failure rate
- human IAA
- certificate pass rate

Source manifests:
- `paper/figure_manifest_v6.yaml`
- `paper/table_manifest_v6.yaml`

All values are `[RESULT REQUIRED]` until real certificate-eligible outputs exist.
