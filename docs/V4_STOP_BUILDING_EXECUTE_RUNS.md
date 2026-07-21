# V4 Stop Building — Execute Runs

V4 is run-later infrastructure. After the final audit is green, stop adding
general infrastructure unless a real run exposes a concrete missing gate.

## First Commands

```bash
python3 -m certvic.v4.final_all_system_audit --out docs/V4_FINAL_ALL_SYSTEM_AUDIT_REPORT.md --json-out data/results/v4_final_all_system_audit.json
python3 -m certvic.commands.generate_real_run_commands --stage tiny_pilot --out-dir commands/tiny_pilot
bash commands/tiny_pilot/commands.sh
```

Run generated scripts manually and gate-by-gate. Planned, dry-run, simulated,
mock, and review artifacts remain non-evidence until real open-local VLM
predictions are scored, locked, audited, and claim-gated.
