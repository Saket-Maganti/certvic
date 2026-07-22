# CertVIC Permission Consumption Guide

One matrix permission owns one atomic slot per provider. Initialize the immutable ledger before
authorization. A notebook verifies the exact currently mounted input map and then claims only its
provider/run-tag/task-universe slot. The lifecycle is `ISSUED -> CLAIMED -> RUN_STARTED ->
OUTPUT_PACKAGED -> IMPORTED -> CONSUMED`. `FAILED`, `REVOKED`, and `EXPIRED` are terminal. Events are
fsync'd, file-locked, and hash chained. A retry requires a new permission and ledger; never edit or
reset an old ledger. Workers start runs, packagers mark packages, and the all-provider importer
consumes slots. Replays and incompatible claims fail before adapter preparation.

The active scalar binding includes `runtime_profile_id` and `runtime_profile_hash`. A child created
for `kaggle_cp310_legacy` cannot authorize a CP312 venv, and a CP312 child cannot authorize a legacy
wheelhouse. Profile validation and permission comparison both occur before GPU inspection or model
loading.
