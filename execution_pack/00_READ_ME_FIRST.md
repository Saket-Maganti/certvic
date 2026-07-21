# CertVIC execution pack: read this first

This pack begins the real external phase. It does not authorize inference and it does not turn
smoke, synthetic, planned, or retrospective artifacts into paper evidence.

## Start and stop rules

1. From the checkout root run `python3 -m certvic.cvpr.doctor --json`.
2. Confirm `local_ready=true`, `paper_evidence=false`, and note the returned readiness state.
3. Run `python3 -m certvic.cvpr.run_graph next` for the next graph node.
4. Provision only the bytes in `01_EXTERNAL_ASSETS_CHECKLIST.md`.
5. Run 00A, 00B, and 00C2 in that order. Pre-smoke authorization and scientific authorization are
   separate artifacts; neither may substitute for the other.
6. Stop on any hash, schema, permission, nonce, review, detectability, or license error. Preserve the
   failed bytes and use `10_FAILURE_RECOVERY.md`.

The current evidence boundary is fixed: Qwen V1 is `12/94`, InternVL V1 is `1/94`, LLaVA V1 is
`3/94`; the frozen pass rule is observed rate at most `0.10`; V2-30 is retrospective sensitivity;
Main and COCO are blocked; no real COCO evidence or genuine completed human review exists.

## Validation

Run `python3 -m pytest -q`, `python3 -m certvic.cvpr.doctor`, and
`python3 -m certvic.cvpr.chaos` before uploading a code bundle. The expected outputs are a green
software suite, an external-action readiness state, and a passing non-evidence chaos report.

## Retry and recovery

Local validators are idempotent. Real provider permissions and their nonces are not resettable.
Never edit returned JSON or ZIP files; rerun only under a newly issued permission after an audited
failure.

