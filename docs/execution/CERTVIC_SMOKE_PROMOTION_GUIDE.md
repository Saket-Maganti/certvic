# Smoke Promotion Guide

For each primary model return validated 00A, unified-snapshot 00B, and 00C2 ZIP. `smoke_gate` checks
two distinct parsed predictions, output v2, runtime/environment/snapshot/run-contract hashes, peak
VRAM, validation, and absence of OOM/unresolved warnings. Status is PENDING, PASS, FAIL, or
BLOCKED_HARDWARE. Scientific notebooks proceed only when all three models are PASS.
