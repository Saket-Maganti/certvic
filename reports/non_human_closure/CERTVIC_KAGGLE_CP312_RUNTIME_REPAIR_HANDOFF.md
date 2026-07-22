# CertVIC Kaggle CP312 runtime repair handoff

## Root cause and repair

The live Kaggle kernel used `/usr/bin/python3` at CPython 3.12.13 on Linux x86-64/glibc 2.35, while
the attached 81-wheel legacy bundle contained CPython 3.10 ABI wheels, including NumPy. Pip correctly
rejected that bundle. The repository now selects one live runtime profile before installation,
validates all wheel tags against `packaging.tags.sys_tags()`, and installs into an isolated no-system-
site-packages venv. All worker, generation, evaluation, packaging, and model subprocesses use the
selected venv interpreter.

`kaggle_cp310_legacy` is preserved. `kaggle_cp312_2026_07` targets CPython 3.12, Linux x86-64, glibc
2.17 minimum (2.35 observed), and the frozen PyTorch 2.4.1/torchvision 0.19.1 `cu121` family. The new
provisioning notebook downloads binary wheels and the full transitive closure from official sources,
records resolver/tag/hash metadata, and requires byte-identical rebuilds.

## Current boundary

- CP312 provisioning notebook: ready.
- Isolated offline venv bootstrap and runtime routing: implemented and locally unit-tested.
- All 20 active runbooks: regenerated profile-aware and content-portable.
- Real Kaggle CP312 wheelhouse build: not yet executed.
- Fresh real Kaggle 00A: not yet executed.
- 00B, 00C2, confirmatory, Main, COCO, and paper evidence: not authorized by this patch.

Runtime failure reports include observed interpreter/runtime, supported tags, selected profile and
wheelhouse, missing packages, incompatible wheels, authenticated content identities, and remediation.
Permission and return contracts carry the profile ID/hash so cross-profile reuse fails closed.

## Required next action

```text
RUN THE CP312 WHEELHOUSE PROVISIONING NOTEBOOK
ACCELERATOR OFF
INTERNET ON
DOWNLOAD certvic_offline_wheelhouse_cp312.zip
UPLOAD IT AS A PRIVATE KAGGLE DATASET
START A FRESH 00A SESSION
ACCELERATOR OFF
INTERNET OFF
RUN ALL
```

```text
CERTVIC_KAGGLE_CP312_RUNTIME_PATCH_COMPLETE
CP312_WHEELHOUSE_BUILDER_READY
ISOLATED_OFFLINE_VENV_RUNTIME_READY
ALL_ACTIVE_RUNBOOKS_PROFILE_AWARE
LEGACY_CP310_PROFILE_PRESERVED
READY_TO_BUILD_CP312_WHEELHOUSE
```
