# CertVIC multi-account Kaggle handoff

CertVIC supports four independent Kaggle accounts without rebuilding scientific bytes. Upload an
identical authenticated bundle to any account or organization under any dataset title, archive
name, extension, mount folder, or nesting. The runbooks authenticate schema, role, provider, study,
stage, immutable identity, hashes, and exact file universe; account and location metadata are
operational provenance only.

## Account substitution

1. Copy the unchanged bundle bytes to the selected account.
2. Use any private dataset title and any archive label. ZIP extensions are optional.
3. Attach the required role datasets to the relevant notebook. The notebook itself may also be
   renamed.
4. Keep Internet off. Use accelerator Off for 00A/00B and the declared T4 topology for GPU stages.
5. Click Run All without editing paths, slugs, owners, hashes, providers, commits, or permissions.
6. Download the canonical return ZIP unchanged and reconcile it locally.

`CERTVIC_INPUT_ROOTS` can narrow nonstandard local/test roots. Optional
`CERTVIC_EXPECTED_CONTENT_ID_*` variables can narrow an accepted identity, but ordinary runs need
no overrides.

## Mirrors, ambiguity, and tampering

Byte-identical attached copies are mirrors of one content identity. The runbook records all mirrors
and chooses deterministically. Two distinct valid identities for a required role fail with
`CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT`; missing content and authentication failures have
their own stable error codes. No path, title, timestamp, or file size breaks a tie.

## Authorization and nonce safety

Authorizations bind authenticated content identities and prospective scientific roles, never a
Kaggle username or mount path. Moving unchanged bytes between accounts therefore preserves the
authorization binding. Provider permissions remain single-use and nonce-bound. Do not run the same
permission concurrently on multiple accounts; issue a fresh permission after an audited failed or
consumed run.

Kaggle sessions never share mutable permission state. Each canonical return carries its provider
proof and hash-bound event chain. Download returns unchanged and reconcile them locally through the
trusted matrix/nonce ledger; duplicate, reused, expired, or mismatched nonces fail closed.

`paper_evidence=false` remains in force until the existing prospective gates authorize evidence.
