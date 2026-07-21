# Offline Wheelhouse Installation Guide

00A first verifies every locked package/version. If exact, it records
`EXACT_PREINSTALLED_ENVIRONMENT_ACCEPTED`. Otherwise it verifies every wheel filename, package,
version, Python/platform tag, size, SHA-256, and role, installs with `pip --no-index --find-links`,
then re-verifies and records `OFFLINE_WHEELHOUSE_INSTALLED_AND_VERIFIED`. Hugging Face,
Transformers, Diffusers, datasets, telemetry, and pip indexes are forced offline.
