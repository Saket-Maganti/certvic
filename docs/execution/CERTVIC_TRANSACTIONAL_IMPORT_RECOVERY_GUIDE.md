# CertVIC Transactional Import and Recovery Guide

`certvic.cvpr.import_transaction` stages all three ZIPs, verifies all portable provider proofs,
reserves all nonces, prepares importer-grade canonical content, writes a recovery journal, atomically
promotes the destination, atomically consumes all three nonces, updates transaction-owned evidence
and gate ledgers, and commits the journal.

Journal states are `STAGED`, `VALIDATED`, `PREPARED`, `PROMOTED`, `LEDGER_COMMITTED`, `COMMITTED`,
`ROLLED_BACK`, and `RECOVERY_REQUIRED`. A failure before promotion releases reservations. A failure
after promotion preserves the destination and journal; do not remove either.

```bash
python3 -m certvic.cvpr.import_transaction recover \
  --journal <JOURNAL.json> \
  --nonce-ledger <CONSUMED_NONCES.json>
```

Recovery verifies the exact promoted tree and finishes all provider nonce and ledger transitions.
Repeating a committed import returns `IDEMPOTENT`; importing the same nonces elsewhere is rejected.
