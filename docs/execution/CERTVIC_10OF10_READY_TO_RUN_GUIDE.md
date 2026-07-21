# CertVIC 10-of-10 Ready-to-Run Guide

Local pre-run implementation is complete; real evidence is not. No model inference, genuine review,
COCO run, or new paper result is represented by this readiness status.

The next sequence is exact:

1. Attach the hash-locked offline wheelhouse.
2. Attach the byte-verified Qwen, InternVL, and LLaVA unified snapshots.
3. Run 00A and download its three canonical artifacts.
4. Run 00B once per provider and download each provider's three canonical artifacts.
5. Run 00C2 once per provider and download the three canonical smoke ZIPs.
6. Return the artifacts unchanged and run `certvic.cvpr.smoke_handoff`.

After all three real smoke rows pass, follow `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`. Scientific
notebooks derive authorization inputs from active variables before hardware/model/output actions,
use one provider-local permission per Kaggle session, and return proof-bearing ZIPs for recoverable
local import.

External blockers remain wheelhouse bytes, model snapshots, source datasets/licenses, real Kaggle
runs, genuine human review, and real model evidence. `paper_evidence=false`; Main and COCO remain
blocked.
