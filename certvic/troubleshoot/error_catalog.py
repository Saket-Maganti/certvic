"""Static error catalog for offline troubleshooting."""

from __future__ import annotations

ERROR_CATALOG = [
    {
        "pattern": "CUDA out of memory",
        "diagnosis": "GPU memory exhausted",
        "playbook": "reduce max-items, shard more aggressively, or use 4-bit model loading",
        "next_command": "python3 -m certvic.eval.run_matrix_planner --num-shards 8 ...",
    },
    {
        "pattern": "cache path not found",
        "diagnosis": "model cache missing",
        "playbook": "check the user-managed cache manifest before running",
        "next_command": "python3 -m certvic.models.cache_check --manifest data/model_cache/qwen_manifest.json --out data/model_cache/qwen_check.json",
    },
    {
        "pattern": "Invalid JSONL",
        "diagnosis": "broken or partial manifest",
        "playbook": "inspect and dry-run repair first",
        "next_command": "python3 -m certvic.recovery.repair_manifests --input broken.jsonl --out repaired.jsonl --dry-run",
    },
]

