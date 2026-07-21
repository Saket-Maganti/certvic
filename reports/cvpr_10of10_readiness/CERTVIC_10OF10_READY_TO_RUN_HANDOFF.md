# CertVIC 10-of-10 Ready-to-Run Handoff

Verdict: `CVPR_PRE_EXECUTION_READY`. Local pre-run readiness is 10/10; real evidence remains pending.

## Exact next sequence

1. Attach the frozen offline wheelhouse bytes.
2. Attach the byte-verified Qwen, InternVL, and LLaVA unified snapshots.
3. Run `00A_certvic_code_and_environment_smoke.ipynb` and return its three canonical artifacts.
4. Run `00B_certvic_model_snapshot_smoke.ipynb` once per provider and return all canonical artifacts.
5. Run `00C2_certvic_real_model_two_item_smoke.ipynb` once per provider.
6. Return the three `00C2_<provider>_real_model_smoke.zip` files unchanged.

Then run the printed `certvic.cvpr.smoke_handoff` command. Only three exact, non-synthetic PASS rows
print the matrix-authorization command. Continue from `CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md`.

Each 00C2 ZIP contains the exact ten-member canonical contract, including the verified snapshot,
provider permission, and provider event chain. The strict handoff rejects run-contract or prompt
drift, cleanup failure, failed model/CUDA release, OOM events, and unresolved warnings.

## External blockers only

- wheelhouse bytes;
- model/processor snapshot bytes;
- source datasets and licenses;
- real Kaggle runs;
- genuine two-rater human review and adjudication;
- real model evidence.

No local filename repair, JSON editing, hash copying, shared-ledger copying, or manual permission
merge remains in the documented route. Do not substitute 00C1, the simulator, synthetic smoke,
blank review sheets, or a hand-written PASS for real execution.
