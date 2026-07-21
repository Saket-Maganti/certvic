# Dockerless Reproduction (V3)

Normal-shell reproduction scripts for smoke, simulation, dry-run, and reports —
**no Docker, no downloads by default, no paid services**. Each script uses
`set -euo pipefail`, avoids destructive `rm -rf`, and documents any required
user-provided path.

## Scripts

| Script | What it does | GPU? | Data? |
| --- | --- | --- | --- |
| `scripts/reproduce_smoke.sh` | Tests + full CPU smoke pipeline (MOCK_ONLY, not evidence). | no | none |
| `scripts/reproduce_simulation.sh` | Anytime-validity stress lab (SIMULATED_ONLY, not evidence). | no | none |
| `scripts/reproduce_tiny_pilot_dry_run.sh` | Tiny pilot orchestrator in dry-run (plans only). | no | `ADE20K_ROOT` (local) |
| `scripts/reproduce_reports.sh` | Storage/scale plans, dashboard, number guard, reviewer sim. | no | none |

## Run

```bash
bash scripts/reproduce_smoke.sh
bash scripts/reproduce_simulation.sh
export ADE20K_ROOT=/path/to/ADEChallengeData2016   # local only; never rehosted
bash scripts/reproduce_tiny_pilot_dry_run.sh
bash scripts/reproduce_reports.sh
```

`reproduce_tiny_pilot_dry_run.sh` requires `ADE20K_ROOT` (it fails fast with a
clear message if unset) and runs strictly in `--dry-run` — no edits generated, no
models run.

## Audit

```bash
python3 -m certvic.release.reproduction_audit --scripts scripts --out docs/REPRODUCTION_AUDIT.md
```

`certvic.release.reproduction_audit` statically verifies every `reproduce_*.sh`
has a shebang + strict mode, no destructive commands, no paid/credential markers,
no Docker, and documents required user paths. It exits non-zero on any violation.
