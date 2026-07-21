# CERTVIC — C.2 UNIVERSAL CONTENT-BASED DATASET DISCOVERY AND MULTI-ACCOUNT KAGGLE PORTABILITY PATCH

## Coordination override

This is a narrow portability patch on top of the completed Phase C.1 zero-edit workflow.

Do not begin another broad audit, infrastructure rebuild, scientific redesign, or evidence-generation phase.

The user executes CertVIC across four different Kaggle accounts. Therefore, every runbook and dataset loader must work regardless of:

- Kaggle account or organization;
- dataset owner;
- dataset slug;
- dataset title;
- mount-folder name;
- uploaded archive filename;
- nested folder structure;
- whether the bundle is attached as a ZIP or already extracted;
- where it appears beneath `/kaggle/input`;
- where the notebook file itself is stored or what it is renamed to.

The system must discover inputs by authenticated content identity, not by names or locations.

Required terminal status:

```text
CERTVIC_UNIVERSAL_DATASET_DISCOVERY_PATCH_COMPLETE
ALL_KAGGLE_ACCOUNTS_SUPPORTED
ALL_DATASET_NAMES_AND_MOUNTS_LOCATION_AGNOSTIC
ALL_ACTIVE_RUNBOOKS_CONTENT_DISCOVERY_ENABLED
NO_OWNER_SLUG_BINDING_IN_EXECUTION
SECURE_AMBIGUITY_AND_TAMPER_GATES_PRESERVED
READY_TO_RUN_00A_FROM_ANY_KAGGLE_ACCOUNT
```

## Repository

```text
/Users/saketmaganti/Projects/certVIC
```

Read first:

```text
reports/non_human_closure/CERTVIC_KAGGLE_ZERO_EDIT_SMOKE_HANDOFF.md
reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
```

Inspect:

```text
certvic/cvpr/notebook_bootstrap.py
certvic/cvpr/notebook_builder.py
certvic/cvpr/kaggle_config.py
certvic/cvpr/kaggle_bundle.py
certvic/cvpr/snapshot_bundle_builder.py
certvic/cvpr/pre_smoke_packager.py
notebooks/kaggle/cvpr/
tests/test_zero_edit_kaggle_smoke.py
```

Preserve commit history. Commit and push the final validated patch to:

```text
Saket-Maganti/certvic
branch: main
```

Do not include weights, wheel archives, local caches, secrets, private datasets, credentials, or generated provider outputs in Git.

## Frozen boundary

Do not change the authoritative prospective protocol, primary endpoint, two-gate certificate, thresholds, historical values, V2-30 status, prompts, parser contracts, model commits, task definitions, human-review state, Main/COCO authorization, or `paper_evidence=false`.

This patch changes only runtime discovery and portability.

## Core rule

Replace:

```text
exact owner-qualified Kaggle slug
+ exact mount folder
+ exact archive filename
```

with:

```text
search allowed roots recursively
→ identify candidates from authenticated manifests
→ verify schema, role, provider, study, stage, immutable identities, hashes, and file universe
→ deduplicate byte-identical copies
→ require one unique content identity
→ materialize securely
```

Human-facing names and locations are operational provenance only. They must not determine scientific identity or permission validity.

## Discovery roots

Support:

1. optional `CERTVIC_INPUT_ROOTS`;
2. `/kaggle/input`;
3. `/kaggle/working`;
4. local fixture roots in tests.

Default Kaggle execution recursively inspects `/kaggle/input`.

Do not assume fixed mount names, one folder level, Kaggle username, dataset title, archive filename, or notebook location.

## Supported representations

Support:

### Arbitrarily named ZIP-compatible files

The same valid bundle must work as:

```text
certvic_code_bundle.zip
code.zip
random.bin
payload.dat
nested/anything/blob
```

Detect ZIP content safely; do not rely on extension.

### Extracted bundle directories

Recognize valid nested directories containing the required authenticated manifests.

### Model snapshot directories

Support renamed ZIPs, extracted directories, nested snapshot roots, and existing supported multipart representations. Avoid hashing every unrelated large file during initial discovery.

## Shared content discovery API

Create or refactor:

```text
certvic/cvpr/content_discovery.py
```

Provide APIs equivalent to:

```python
discover_authenticated_input(
    role,
    provider=None,
    study=None,
    stage=None,
    roots=None,
    expected_identity=None,
)
```

Support at least:

```text
CODE
CONFIGS
EXECUTION_TOOLS
OFFLINE_LINUX_WHEELHOUSE
MODEL_SNAPSHOT
REAL_TWO_ITEM_SMOKE
PRE_SMOKE_PERMISSIONS
CONFIRMATORY_GENERATION_INPUT
SCIENTIFIC_PROVIDER_INPUT
TASK_BUNDLE
CANONICAL_RETURN
```

Return:

```text
role
provider
study
stage
representation
discovered_path
materialized_root
bundle_schema
manifest_sha256
content_identity_sha256
archive_sha256 when applicable
verified_file_count
verified_total_bytes
observed_mount
observed_dataset_folder
paper_evidence
```

Observed paths and names are provenance only.

## Classification and verification

For every candidate:

1. cheap probe;
2. inspect small manifests/configs;
3. classify role;
4. validate schema and required fields;
5. validate provider/study/stage;
6. validate immutable expected identities;
7. perform full hash verification only for relevant candidates.

Do not execute Python from attached datasets.

Do not follow symlinks.

Reject traversal, duplicate members, malformed JSON, device files, unsafe links, manifest/file-universe mismatch, hash mismatch, provider mismatch, study mismatch, stage mismatch, commit mismatch, task mismatch, and permission mismatch.

## Ambiguity

No valid candidate:

```text
CERTVIC_DISCOVERY_01_REQUIRED_ROLE_NOT_FOUND
```

Multiple byte-identical candidates:

- treat as mirrors;
- select deterministically by normalized path;
- record every mirror;
- continue.

Multiple distinct valid candidates:

```text
CERTVIC_DISCOVERY_02_AMBIGUOUS_DISTINCT_CONTENT
```

Do not choose using path, name, owner, slug, timestamp, or size.

Tampering:

```text
CERTVIC_DISCOVERY_03_CONTENT_AUTHENTICATION_FAILED
```

## Scientific identity

Derive scientific identity only from authenticated content.

Never bind scientific identity or permission validity to:

```text
Kaggle username
owner-qualified slug
dataset title
mount path
archive filename
notebook filename
```

Those may only be recorded as operational provenance.

## Regenerate all active runbooks

Update all active notebooks, including 00A, all provider-specific 00B and 00C2 notebooks, confirmatory notebooks 01–04, Main notebooks 10–13, and second-domain notebooks 20–23.

Every runbook must:

- work under any Kaggle owner;
- work under any dataset title;
- work under any mount folder;
- work with any archive filename;
- work with nested paths;
- support valid extracted directories;
- not depend on its own filename;
- require no manual path, slug, owner, hash, provider, or permission editing;
- preserve canonical output ZIP names;
- print discovered provenance;
- fail closed on ambiguity.

Provider identity may remain embedded in provider-specific notebooks, but must not be inferred from the notebook filename at runtime.

## Optional content-identity overrides

Support optional environment variables that narrow accepted authenticated identities:

```text
CERTVIC_INPUT_ROOTS
CERTVIC_EXPECTED_CONTENT_ID_CODE
CERTVIC_EXPECTED_CONTENT_ID_CONFIGS
CERTVIC_EXPECTED_CONTENT_ID_TOOLS
CERTVIC_EXPECTED_CONTENT_ID_WHEELHOUSE
CERTVIC_EXPECTED_CONTENT_ID_SNAPSHOT
CERTVIC_EXPECTED_CONTENT_ID_TASKS
CERTVIC_EXPECTED_CONTENT_ID_PERMISSIONS
```

Normal runs require no overrides. Invalid overrides fail closed.

## Multi-account support

Create:

```text
reports/non_human_closure/CERTVIC_MULTI_ACCOUNT_KAGGLE_HANDOFF.md
```

Document that identical bundles can be uploaded under any names to any of the four accounts.

Support account substitution without rebuilding scientific bytes.

Do not bind authorizations to Kaggle accounts.

Explain nonce safety and local return reconciliation.

## Manifest compatibility

Treat `expected_kaggle_dataset_slug` and `mount_path` as optional suggestions only.

Add policy fields equivalent to:

```text
discovery_policy: CONTENT_AUTHENTICATED_ANY_LOCATION
owner_binding_required: false
filename_binding_required: false
path_binding_required: false
accepted_representations:
  - zip_archive
  - extracted_directory
```

Maintain backward compatibility when safe.

## Doctor and next action

Add:

```text
multi_account_portability:
  passed: true
  owner_slug_binding: false
  filename_binding: false
  mount_binding: false
  content_authentication_required: true
```

The doctor must verify that no active runbook requires exact owner slugs, filenames, or mount paths.

## Tests

Add tests for:

- arbitrary owner and mount names;
- arbitrary archive names and extensions;
- nested extracted directories;
- byte-identical mirrors;
- distinct-content ambiguity;
- tampering;
- wrong provider/commit/study/stage;
- traversal, symlink, duplicate members;
- notebook-name independence;
- four independent Kaggle-account layouts;
- efficient probing among many unrelated files.

Run synthetic execution of all active notebook routes using arbitrary names and mounts.

## Documentation cleanup

Update:

```text
README.md
CERTVIC_CVPR_EXECUTION_MASTER_PLAN.md
kaggle_uploads/CERTVIC_KAGGLE_DATASET_MAP.md
kaggle_uploads/CERTVIC_KAGGLE_UPLOAD_MANIFEST.csv
reports/non_human_closure/CERTVIC_KAGGLE_ZERO_EDIT_SMOKE_HANDOFF.md
reports/cpu_execution/CERTVIC_FIRST_GPU_WAVE_HANDOFF.md
execution_pack/00_READ_ME_FIRST.md
```

Remove all implications that the owner must be `certvic`, names must be fixed, or mounts must match fixed slug folders.

Canonical names should be described as optional recommended labels.

Remove stale README/master-plan language about the obsolete replacement archive blocker.

## Validation

Run:

```bash
python3 -m pytest -q
python3 -m ruff check --no-cache certvic scripts tests
python3 -m compileall -q certvic scripts tests
python3 -m certvic.cvpr.notebook_validation --root notebooks/kaggle/cvpr
python3 scripts/validate_t4x2_notebooks.py
python3 -m certvic.cvpr.artifact_registry verify
python3 -m certvic.cvpr.doctor --json
python3 -m certvic.cvpr.next_action
python3 -m certvic.cvpr.run_graph status
```

Also run universal-discovery tests, four-account simulation, all notebook synthetic routes, bundle-security tests, permission-order tests, claim guard, privacy/path audit, deterministic release twice, clean extraction, Git diff check, and secret scan.

Verify:

```text
no active runbook requires an owner-qualified slug
no active runbook requires a fixed mount
no active runbook requires a fixed input filename
all inputs are authenticated by content
byte-identical mirrors are deduplicated
distinct valid candidates fail closed
00A and 00B require zero GPUs
00C2 verifies permissions before hardware/model access
paper_evidence=false
human_reviewed count=0
Main execution_allowed=false
COCO execution_allowed=false
```

## Git requirements

Commit message:

```text
Make Kaggle input discovery account and path agnostic
```

Push to `origin/main`, verify remote HEAD, and leave a clean working tree.

## Required final response

Report:

1. universal discovery implementation;
2. multi-account behavior;
3. ambiguity and tamper behavior;
4. every notebook regenerated;
5. test totals;
6. documentation changes;
7. commit SHA and push verification;
8. exact next action:

```text
UPLOAD THE FOUR 00A INPUT BUNDLES UNDER ANY NAMES TO ANY KAGGLE ACCOUNT
ATTACH THEM TO THE 00A NOTEBOOK
KEEP ACCELERATOR OFF
KEEP INTERNET OFF
CLICK RUN ALL
```

## Success standard

```text
ANY ACCOUNT
ANY DATASET NAME
ANY ARCHIVE NAME
ANY MOUNT
ANY NESTING
SAME AUTHENTICATED CONTENT
SAME SCIENTIFIC IDENTITY
```

Implement universal content discovery, validate it across four simulated accounts, commit it, push it, and leave the repository ready for 00A.
