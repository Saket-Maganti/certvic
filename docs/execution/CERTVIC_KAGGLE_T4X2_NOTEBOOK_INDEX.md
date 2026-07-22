# CertVIC CVPR Kaggle notebook index

The authoritative suite has 20 generated runbooks: 00A; three 00B snapshot checks; 00C1; three 00C2
real-model smokes; confirmatory 01-04; Main 10-13; and COCO 20-23. Exact bytes are listed in
`notebooks/kaggle/cvpr/notebook_manifest.json`.

All 20 runbooks are zero-edit, content-authenticated, owner/path/name independent, and runtime-profile
aware. They probe the kernel immediately, select exactly one CP310/CP312 profile, choose the unique
compatible authenticated wheelhouse, create or reuse only that profile's isolated offline venv, and
use its interpreter for every runtime-sensitive subprocess. No notebook accepts a mixed CP310/CP312
matrix.

00A and all three 00B notebooks require Accelerator Off. Generation, evaluation, and 00C2 validate
the declared T4 topology only after authorization checks. A real CP312 00A has not yet been run;
therefore 00B, 00C2, confirmatory, Main, and COCO remain blocked by prospective runtime evidence.

The separate provisioning runbook is
`notebooks/kaggle/provisioning/00_build_certvic_cp312_wheelhouse.ipynb` and must run with Accelerator
Off and Internet On. It is a dependency builder, not one of the 20 scientific runbooks.
