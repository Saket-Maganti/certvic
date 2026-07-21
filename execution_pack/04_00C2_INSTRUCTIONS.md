# 00C2: authorized two-item real-model smoke

Prerequisites are a passing 00A artifact, the provider's passing 00B artifact, the parent pre-smoke
matrix, and an unexpired provider-specific one-run permission. Run
`notebooks/kaggle/cvpr/00C2_certvic_real_model_two_item_smoke.ipynb` in three separate fresh Kaggle
T4x2 sessions, one provider per session. Budget 20–60 minutes each.

Before CUDA access or model loading, the notebook must verify the parent, child, provider, snapshot,
environment, prompt, parser, run-contract, task-bundle, and nonce bindings. The only downloadable
output is `00C2_<provider>_real_model_smoke.zip`; it must contain the ten canonical members documented
in the master plan and finish in provider state `OUTPUT_PACKAGED`.

Download every ZIP unchanged. Validate all three with the smoke handoff described in
`05_SMOKE_HANDOFF.md`. OOM, unresolved warnings, incomplete cleanup, member mismatch, or permission
mismatch fails closed. A failed permission is not reset; preserve its event log and request a new
permission only after the failure is audited.

