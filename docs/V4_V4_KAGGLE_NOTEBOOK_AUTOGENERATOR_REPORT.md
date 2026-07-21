# V4 Prompt 02 Report — Kaggle Notebook Autogenerator

Implemented `certvic.notebooks.kaggle_notebook_builder`.

Commands:

```bash
python3 -m certvic.notebooks.kaggle_notebook_builder --job diffusion_tiny --out notebooks/generated/kaggle_diffusion_tiny.ipynb
python3 -m certvic.notebooks.kaggle_notebook_builder --job vlm_200 --out notebooks/generated/kaggle_vlm_200.ipynb
```

Generated notebooks are valid ipynb JSON with zero-cost warnings, commented
resume commands, input/output checklists, and no credentials.
