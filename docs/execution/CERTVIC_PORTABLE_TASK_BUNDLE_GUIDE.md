# CertVIC Portable Task Bundle Guide

Scientific tasks store only safe logical paths. Create or migrate a bundle with
`python3 -m certvic.cvpr.task_bundle migrate --tasks <TASKS> --bundle-root <NEW_ROOT>` and verify it
with `python3 -m certvic.cvpr.task_bundle verify --bundle-root <ROOT> --manifest <ROOT>/task_bundle_manifest.json`.
The manifest inventories every byte, size, role, task ID, study, schema, content lock, and final
bundle hash. Task hashes bind logical paths and file records, never the host root. Verification must
precede path resolution. Use `diff` to audit two manifests. Any absolute or parent-traversal path,
missing member, extra task identity, or changed byte blocks execution.
