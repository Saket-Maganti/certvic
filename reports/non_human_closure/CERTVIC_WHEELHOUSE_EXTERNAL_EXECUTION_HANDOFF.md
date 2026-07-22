# CertVIC wheelhouse execution handoff

The prior Linux x86-64/CPython 3.10 bundle remains frozen at
`kaggle_uploads/01_wheelhouse/certvic_offline_wheelhouse.zip` with its historical clean-Linux
validation. It is now identified as `kaggle_cp310_legacy` and is not compatible with the observed
Kaggle CPython 3.12 runtime.

The CP312 deterministic provisioning workflow is ready at
`notebooks/kaggle/provisioning/00_build_certvic_cp312_wheelhouse.ipynb`. The expected output is
`certvic_offline_wheelhouse_cp312.zip`. No real CP312 wheelhouse bytes and no real fresh 00A PASS are
claimed in this repository state.

Next: run the provisioning notebook with Accelerator Off and Internet On, download its output,
upload the unchanged ZIP as a private dataset, then run a fresh zero-edit 00A with Accelerator Off
and Internet Off.
