
        # Run Qwen Spurious V2 on Kaggle

        Do not fabricate predictions. Upload `data/edits/spurious_flip_control_v2/`
        after the CPU builder has produced a manifest and images.

        Expected output:

        - `pred_qwen2_5_vl_7b_spurious_v2_merged.jsonl`
        - shard manifests and logs
        - runtime summary JSON

        After download, ingest into a V2-specific directory and report V8 raw
        and V2 separately. Do not overwrite the V8 canonical spurious file.
