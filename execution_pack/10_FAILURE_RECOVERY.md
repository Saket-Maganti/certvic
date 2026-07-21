# Failure recovery

## Local validators and packaging

Re-run read-only validators freely. For packaging interruption, keep the canonical destination
unchanged, remove only the transaction-owned temporary file after inspecting it, and retry the exact
same command. Run `python3 -m certvic.cvpr.chaos --out recovery_chaos.json` to confirm fault handling.

## Kaggle failures

Preserve the notebook log, permission events, partial checkpoints, and failure report. Do not rename or
edit them. OOM retries may only follow the frozen batch-halving rule down to one; prompt, decoding,
parser, task, snapshot, and environment bytes stay fixed. A permission retry requires an audited
failure and newly issued nonce.

## Import failures

Use:

```bash
python3 -m certvic.cvpr.import_transaction recover \
  --journal TRANSACTION_JOURNAL.json \
  --nonce-ledger CONSUMED_NONCES.json \
  --evidence-ledger EVIDENCE_UPDATES.json \
  --gate-ledger GATE_UPDATES.json
```

The expected result is committed completion or an exact stable blocker; canonical bytes must not be
partially changed. A repeated completed import is idempotent. A different ZIP or destination under a
consumed nonce is replay and must be refused.

## Human review and evidence

Missing review rows return to the assigned real reviewer. Qualification expiry requires
requalification. Packet changes require a version diff and fresh binding. No recovery step may set
`human_reviewed=true`, `paper_evidence=true`, Main authorization, or COCO authorization without the
genuine required artifacts.
