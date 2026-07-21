# V9 Master State

## Current Real Evidence

- V8/V8.1 imported provider outputs exist under `kaggleoutputs/newruns` and `data/results/main_real_200/v8_upgrade`.
- Qwen2.5-VL-7B failed the spurious specificity gate: `12/94 = 0.1277`, threshold `<= 0.10`.
- InternVL and LLaVA passed the existing V8 spurious specificity gate (`1/94` and `3/94`).
- Detectability diagnostics report `n_items=94`, AUC about `0.6682`, and `artifact_risk=false`.

## Current Blockers

- no real human validation of preliminary labels
- raw Qwen gate remains failed
- no claim-valid recompute scenario passes
- Main-500 remains blocked unless the paper is reframed honestly

## Must Not Be Claimed

- No CVPR-ready claim.
- No clean all-provider spurious specificity claim.
- No real human-validation claim for V8.1 preliminary labels.
- No Main-500 result claim.
- No `paper_evidence=true` for V9 scaffolds.

## Next Prompt

`01_PRELIM_LABEL_HYGIENE_AND_AUDIT_REPAIR.md`

## Main-500 Status

Main-500 remains blocked unless Qwen is resolved by a real, preregistered V9 gate or the paper is honestly reframed as model-dependent specificity.
