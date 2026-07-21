# CertVIC Model Matrix

Primary models remain Qwen2.5-VL-7B-Instruct, InternVL2-8B, and LLaVA-OneVision-Qwen2-7B. An optional
fourth model is not selected because the immediate value does not justify another execution family.
Planned non-VLM diagnostics are fixed-answer, text-only, image-shuffled, seeded random-change,
confidence-only heuristic, visual-difference detector, and a validity oracle where defined. They are
not observed model results. Prompt/decoding robustness is secondary and must not alter the primary
frozen prompt.
