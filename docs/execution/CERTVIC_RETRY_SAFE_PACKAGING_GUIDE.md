# CertVIC Retry-Safe Packaging Guide

The packaging lifecycle is:

```text
RUN_STARTED -> PACKAGING_STARTED -> PACKAGE_WRITTEN -> OUTPUT_PACKAGED
PACKAGING_STARTED or PACKAGE_WRITTEN -> PACKAGING_FAILED -> PACKAGING_STARTED
```

The packager writes a temporary deterministic ZIP, validates its member set and CRCs, fsyncs it where
supported, and atomically renames it to the canonical final path. `OUTPUT_PACKAGED` is appended only
after that final path exists and its SHA-256 is known.

A retry is permitted only when the previous attempt is `PACKAGING_FAILED`, the final ZIP is absent,
the validated runtime outputs still match their contracts, and the provider nonce remains
unconsumed. The recovery result records why retry is allowed. If a valid final ZIP already exists and
its hash matches the committed event, packaging returns an idempotent no-op. A ZIP with an unmatched
permission state or hash fails closed.

Do not reset a nonce, edit an event file, or promote a ZIP manually. Repair the underlying
storage/validation error and rerun the same packager command.

