# V4 Prompt 04 Report — Offline Model Cache Manifests

Implemented `certvic.models.cache_manifest` and `certvic.models.cache_check`.

Commands:

```bash
python3 -m certvic.models.cache_manifest --provider qwen2_5_vl_7b --cache-root /path/to/cache --out data/model_cache/qwen_manifest.json
python3 -m certvic.models.cache_check --manifest data/model_cache/qwen_manifest.json --out data/model_cache/qwen_check.json
```

The tools inspect user-managed local caches only and never download weights.
