# Genuine human review and adjudication

Inventory and validate the blind packet first:

```bash
python3 -m certvic.cvpr.review inventory --packet-root PRIVATE_PACKET_ROOT
python3 -m certvic.cvpr.review verify-blind-ids \
  --coordinator-key PRIVATE_PACKET_ROOT/coordinator_key.csv \
  --sheet PRIVATE_PACKET_ROOT/rater_1.csv --sheet PRIVATE_PACKET_ROOT/rater_2.csv
```

Two distinct humans must pass unexpired qualification, review independently with provider outcomes
hidden, and complete every row. Track each sheet with `review progress`; compute agreement, create the
disagreement packet, assign a qualified adjudicator, validate adjudication, and run `review finalize`.
The command-specific required arguments are listed by `python3 -m certvic.cvpr.review --help`.

Expected effort is 8–20 total reviewer hours. Outputs are qualification and validation artifacts,
immutable timeline, agreement, adjudication, final-inclusion state, exclusion HTML, and packet-version
diff. Validation requires two identities, complete identical blind-ID universes, current
qualifications, exact packet hashes, resolved disagreements, and a signed final ledger.

Never invent identities, auto-fill sheets, or mark a blank sheet complete. Missing rows return to the
same reviewer; changed packets require a new version and explicit diff, not silent edits.

