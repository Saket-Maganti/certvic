# V4 Prompt 03 Report — Colab Notebook Autogenerator

Implemented `certvic.notebooks.colab_notebook_builder`.

Commands:

```bash
python3 -m certvic.notebooks.colab_notebook_builder --job diffusion_tiny --out notebooks/generated/colab_diffusion_tiny.ipynb
python3 -m certvic.notebooks.colab_notebook_builder --job vlm_tiny --out notebooks/generated/colab_vlm_tiny.ipynb
```

Drive mount and GPU commands are disabled/commented by default. No automatic
downloads are enabled.
