# Kaggle Main-scale T4x2 template

`notebooks/kaggle/diffusion_main_scale_T4x2_TEMPLATE.ipynb` is a template for a
later Main-500 diffusion session. It uses the same T4x2 layout as the earlier
diffusion runbook: shard0 on GPU0, shard1 on GPU1, shard-level logs/outputs,
resume checks, deterministic merge, and an output zip that excludes model
caches and weights.

Do not run Main-500 diffusion until remaining controls and go/no-go gates pass.
Planning is CPU (~10-30 min), diffusion is estimated at ~6-8 hr on T4x2,
quality/detectability is CPU (~15-60 min), and human review is ~20-25 hr.
