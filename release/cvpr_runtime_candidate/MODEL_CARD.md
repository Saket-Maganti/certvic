
# Model Runtime Card

Planned families: Qwen2.5-VL-7B-Instruct, InternVL2-8B, and LLaVA-OneVision-7B. Weights are excluded.
Users must supply immutable offline snapshots, model/processor commits, expected architecture, and a
strict file manifest. Snapshot smoke output is non-evidence. T4 execution uses float16 or explicitly
verified NF4; InternVL BF16 is forbidden without capability proof.
