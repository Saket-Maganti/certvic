# CertVIC Strict Smoke Integrity Guide

The smoke gate validates canonical bytes, trusted fixture rows, provider/model/snapshot/environment
identity, the frozen run contract, and the exact prompt template. A strict PASS also requires:

```text
cleanup_status=PASS
model_release_status=PASS
cuda_cleanup_status in {PASS, NOT_APPLICABLE}
teardown_complete=true
oom_events=0
unresolved_warnings=[]
```

Only `CUDA_CACHE_ALREADY_EMPTY` and `OPTIONAL_TELEMETRY_UNAVAILABLE` are accepted as explicitly
non-blocking warning codes. Unknown warnings fail closed. Peak-VRAM rules remain unchanged: a real
smoke requires a positive measurement, while an explicitly synthetic notebook proof remains
non-evidence and cannot authorize scientific execution.

Failures emit a provider, artifact, field, expected/observed classification, stable error code, and
remediation. Relevant codes include `SMOKE_SNAPSHOT_MISMATCH`, `SMOKE_RUN_CONTRACT_MISMATCH`,
`SMOKE_PROMPT_MISMATCH`, `SMOKE_CLEANUP_FAILED`, `SMOKE_OOM_DETECTED`,
`SMOKE_WARNING_UNRESOLVED`, and `SMOKE_PARENT_AUTHORIZATION_MISMATCH`.

