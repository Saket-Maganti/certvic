# Return ZIP Handoff

Download the single canonical ZIP printed by each notebook. Never download loose shards and manually merge them. Verify the local filename, SHA-256, CRC, member manifest, authorization proof, seed manifest, environment and snapshot identities, task-bundle identity, validation report, logs, and resume state before import.

00A returns `00A_environment_bundle.zip`. 00B returns one provider-specific snapshot bundle. 00C2 returns one provider-specific real-model smoke bundle. Scientific provider notebooks return `confirmatory_<provider>_return.zip`, `main_<provider>_return.zip`, or `coco_<provider>_return.zip`; generation notebooks return their lane-specific generation ZIP.

Use the exact handoff command printed by the notebook and documented in the dataset map. Provider matrices must be imported transactionally with all three returns together. The importer validates exact task/provider/schema/run-contract identities, consumes permission nonces, stages results, and promotes atomically. A failed validation leaves canonical results unchanged.

Corrupt downloads must be downloaded again. Permission mismatch, stale prompt/run contract, wrong snapshot, or unexpected file blocks import; do not rewrite the return archive. After a successful import, preserve the original return ZIP and import receipt as provenance.
