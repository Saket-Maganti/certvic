# Restoring historical Kaggle outputs

The active project and historical `kaggleoutputs` bytes are a two-part distribution. The historical
archive is immutable evidence transport, not source code and not a dependency for tests that do not
inspect historical runs.

Place the separately distributed archive anywhere outside the checkout, then run:

```bash
python3 scripts/restore_historical_outputs.py \
  --archive /absolute/path/certvic_historical_kaggleoutputs.zip \
  --manifest PROJECT_DISTRIBUTION_MANIFEST.json \
  --project-root . \
  --dry-run
python3 scripts/restore_historical_outputs.py \
  --archive /absolute/path/certvic_historical_kaggleoutputs.zip \
  --manifest PROJECT_DISTRIBUTION_MANIFEST.json \
  --project-root .
```

The restorer verifies the locked archive SHA-256 before reading members. It accepts only members
under `kaggleoutputs/`, rejects traversal, duplicate names, and symlinks, preserves identical files,
and refuses any conflicting existing byte. It never silently overwrites. Historical-output-dependent
tests must skip with `historical Kaggle outputs archive not restored` when the canonical directory is
absent; all other tests remain runnable.
