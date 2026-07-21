# Playbook: Edit Realism Failure

**Symptoms: low edit-quality pass rate, or high edit-detectability AUC (a trivial classifier separates edited from original).**

## Actions

1. Switch the crude `simple` engine for photorealistic diffusion inpainting (`diffusers_inpaint_optional`) on free Kaggle/Colab GPU.
2. Re-run `certvic.validation.edit_detectability`; require AUC well below 0.8 before trusting any gap.
3. Tighten edit-quality gates (mask area, inside/outside change, sharpness) and drop degenerate/duplicate edits.
4. Route flagged items through extra human review; keep only photorealistic, single-factor edits.
5. Add original-only and edited-only ablations to bound artifact-driven flips.

Do not fabricate results to clear this symptom; if the honest outcome is a null
result or an ineligible claim, report it and adjust the protocol, not the numbers.
