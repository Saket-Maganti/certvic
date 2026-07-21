
        # Spurious-Control V2 Design

        `paper_evidence=false` `no_gpu_run_performed=true`

        V2 should be built before any clean Qwen specificity claim is made.

        Design requirements:

        - Target n = 200-300 no-change controls if ADE candidate supply supports it.
        - Class-balanced sampling across table, chair, sofa, and car.
        - Patch/object mask overlap must be exactly 0.
        - Patch/object bbox overlap must be 0.
        - Minimum patch-to-object bbox distance should be preregistered, default at least 96 px and at least 15 percent of the shorter image side when possible.
        - Patch area should be lower salience than V8, default 2-3 percent of image area.
        - Perturbation should use mild blur/jitter/noise, not a large high-contrast patch.
        - Original and edited arms must use the same JPEG re-encoding pipeline.
        - No manual cherry-picking. All exclusions must be deterministic and logged.
        - Add a cheap detectability cap before model inference; flag or reject candidates above the preregistered cap.

        Gate policy:

        - Keep `control_spurious_flip_max <= 0.10`.
        - V2 is a new preregistered control, not a retroactive edit to the V8 raw result.
        - Report V8 raw and V2 separately.
