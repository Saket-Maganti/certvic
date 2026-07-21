# Model Matrix Decision

**Status:** evidence-bounded V11 audit; `paper_evidence=false`

Keep the three-model open-weight matrix for continuity; do not add models before pinning the existing runs.

| Provider | Repository ID | Historical revision | Current role |
|---|---|---|---|
| qwen2_5_vl_7b | Qwen/Qwen2.5-VL-7B-Instruct | unpinned / `unloaded` | primary specificity model |
| internvl_8b | OpenGVLab/InternVL2-8B | unpinned / `unloaded` | paired comparator |
| llava_onevision_7b | llava-hf/llava-onevision-qwen2-7b-ov-hf | unpinned / `unloaded` | paired comparator |

Before a new run, record immutable model and processor commits, tokenizer/processor configuration,
precision/quantization, image preprocessing, framework versions, hardware class, decoding settings,
and input/package hashes. Preserve Qwen as the predeclared primary V2 model; a three-model statement
requires the Bonferroni rule. The V11 runbooks freeze `max_new_tokens=16`, `do_sample=false`,
`temperature=0`, strict yes/no parsing, exact model commits, and hash-locked code/control inputs.

## Optional expansion ranking

| Rank | Expansion | Scientific value | Feasibility / license condition | Decision |
|---|---|---|---|---|
| 1 | Size-controlled checkpoint in an existing family | separates family from scale effects | only an open, immutable revision that fits free Kaggle | planned after core evidence |
| 2 | A fourth open model with a distinct vision encoder/training family | increases architectural diversity | reproducible processor, redistributable metadata, T4x2 fit required | high-value optional |
| 3 | Larger open checkpoint | tests scale trend | likely higher memory/runtime and must not delay independent controls | enhancement only |
| 4 | Closed/API model | external relevance | cost, version opacity, and reproducibility conflict with the core protocol | exclude from core; reference-only if separately authorized |

No expansion can repair invalid item selection or missing human review. Do not add a fourth model
until the three current revisions and processors are pinned and the independent specificity set is locked.
