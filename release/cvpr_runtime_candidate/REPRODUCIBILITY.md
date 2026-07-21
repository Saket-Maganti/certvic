
# Reproducibility

Install with `python3 -m pip install -e '.[dev]'`; run `python3 -m pytest -q`, Ruff, compileall, claim
and privacy guards, notebook checks, paper compile, and release audit. Real execution requires source
license confirmation and user-created all-file snapshot manifests. Returned three-model ZIPs are
imported atomically. Identical imports are idempotent and conflicts are refused.
