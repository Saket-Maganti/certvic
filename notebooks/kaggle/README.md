# Kaggle Guides

These markdown guides describe free Kaggle workflows. They do not assume paid
services and do not store brittle notebook outputs.

## Generated job bundles (V3)

Instead of hand-copying commands into a Kaggle notebook, generate a copy-safe
bundle (README + preflight + commands + resume notes + manifest, paths
anonymized, no pixels/credentials):

```bash
python3 -m certvic.compute.kaggle_packager --job diffusion_tiny --config configs/real_pilot_ade20k.yaml --out-dir compute_bundles/kaggle_diffusion_tiny
python3 -m certvic.compute.kaggle_packager --job vlm_tiny       --config configs/tiny_reviewed_eval.yaml --out-dir compute_bundles/kaggle_vlm_tiny
```

Job types: `diffusion_tiny`, `diffusion_200`, `vlm_tiny`, `vlm_200`, `ablations`,
`reports_only`. Use `certvic.compute.colab_packager` for Colab. See
`docs/FREE_COMPUTE_BUNDLES.md`.
