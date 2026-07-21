# Inputs matrix

Attach the CertVIC code bundle, for example `dist/certvic_kaggle_main200_bundle.zip`,
plus exactly one task bundle.

| RUN_TAG | notebook | task bundle | Kaggle accelerator | Internet | model cache |
|---|---|---|---|---|---|
| spurious | each VLM T4x2 notebook | `certvic_spurious_flip_control.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| perception_scaled | each VLM T4x2 notebook | `certvic_perception_control_scaled.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| polarity | each VLM T4x2 notebook | `certvic_polarity_ablations.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| mechanism | each VLM T4x2 notebook | `certvic_mechanism_probes.zip` | GPU T4 x2 | ON | `/kaggle/working/hf_models/...` |
| main500 diffusion | `diffusion_main_scale_T4x2_TEMPLATE.ipynb` | scale plan + ADE20K inputs | GPU T4 x2 | ON | excludes model cache from output zip |

The notebooks auto-detect `CERTVIC_DIR`, `BUNDLE_INPUT`, `OUTPUT_DIR`,
`MODEL_CACHE_DIR`, provider, and `RUN_TAG`, with explicit overrides in the config cell.
