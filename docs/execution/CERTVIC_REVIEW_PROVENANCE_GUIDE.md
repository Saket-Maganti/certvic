# Review Provenance Guide

Use only `python3 -m certvic.cvpr.review`. Qualification, completed-sheet validation, agreement,
adjudication validation, and finalization are separate immutable artifacts. Finalization refuses
identical identities/sheets/qualifications, packet or item-universe mismatch, stale agreement inputs,
unauthorized/incomplete adjudication, and hash drift. The final ledger retains every included and
excluded item, both decisions, disagreements, adjudication, reason, confidence, and artifact hashes.
