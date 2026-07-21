
# CertVIC Real Model Smoke Guide

00C1 is always `SYNTHETIC_MOCK_RUNTIME` and always passes `--mock-runtime`. 00C2 is always
`NON_EVIDENCE_REAL_MODEL_SMOKE`, contains no mock switch, and refuses execution until
`USE_REAL_MODEL=True`. Run 00A, then 00B for the exact mounted snapshot, then 00C2 for each of Qwen,
InternVL, and LLaVA. Success requires two items/four validated rows, model load, parsing, peak-VRAM and
runtime logs, cleanup, complete run-contract provenance, and a deterministic return ZIP.

Snapshot language is exact: local all-file validation is `LOCAL_SNAPSHOT_BYTES_VERIFIED`; a trusted
metadata check is `REMOTE_COMMIT_AUTHENTICATED`; a user-entered revision without authentication is
only `REMOTE_COMMIT_DECLARED`. Smoke output is never scientific evidence. InternVL uses NF4, float16,
at most six 448-pixel tiles plus thumbnail, and one process per visible T4. Failure at batch size one
blocks that provider and must name the alternative hardware rather than claiming compatibility.
