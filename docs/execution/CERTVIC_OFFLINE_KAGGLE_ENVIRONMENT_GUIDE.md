# CertVIC offline Kaggle environment guide

The v2 lock at `configs/runtime/kaggle_t4x2_environment.lock.json` supports two mutually exclusive
runtime profiles:

| Profile | Interpreter | Wheelhouse | State |
|---|---|---|---|
| `kaggle_cp310_legacy` | CPython 3.10 / `cp310` | `certvic_offline_wheelhouse.zip` | preserved clean-Linux legacy validation |
| `kaggle_cp312_2026_07` | CPython 3.12 / `cp312` | `certvic_offline_wheelhouse_cp312.zip` | provisioning builder ready; fresh 00A not yet run |

Every active notebook immediately records `sys.executable`, implementation, Python version,
architecture, OS, libc, and `packaging.tags.sys_tags()`. Exactly one lock profile must match. It then
discovers an authenticated wheelhouse for that profile, checks every wheel tag before invoking pip,
and rejects missing direct pins, source distributions, foreign platforms, foreign architectures,
wrong ABIs, and ambiguous compatible content identities.

The notebook kernel remains a thin controller. Runtime packages are installed with
`--no-index --find-links --only-binary=:all:` into the selected profile's venv under
`/kaggle/working/certvic_runtime/`; system site packages are disabled. All model, generation,
evaluation, packaging, and worker subprocesses use the isolated interpreter recorded as
`RUNTIME_PYTHON`.

## Build CP312 wheelhouse

Open `notebooks/kaggle/provisioning/00_build_certvic_cp312_wheelhouse.ipynb`, attach authenticated
CODE, CONFIGS, and EXECUTION_TOOLS inputs, set Accelerator Off and Internet On, then Run All. The
builder uses only binary wheels from PyPI and the frozen official PyTorch `cu121` index, records the
resolved transitive closure and tags, requires two byte-identical deterministic bundle builds, then
creates a separate no-system-site-packages validation venv and performs a no-index install/import
smoke before declaring the downloadable bundle ready.

Download `certvic_offline_wheelhouse_cp312.zip` and upload the unchanged bytes as a private Kaggle
dataset. In a fresh 00A session use Accelerator Off and Internet Off. Do not run 00B until 00A has
returned a profile-aware PASS bundle.

Stable failures are `CERTVIC_RUNTIME_01_PYTHON_PROFILE_NOT_SUPPORTED`,
`CERTVIC_RUNTIME_02_WHEELHOUSE_ABI_MISMATCH`, `CERTVIC_RUNTIME_03_REQUIRED_WHEEL_MISSING`, and
`CERTVIC_RUNTIME_04_MULTIPLE_RUNTIME_PROFILES_AMBIGUOUS`.
