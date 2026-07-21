"""Backward-compatible import shim for the renamed canonical COCO adapter."""

from certvic.data.coco_adapter import (  # noqa: F401
    COCOAdapterNotReady,
    COCO_TO_CERTVIC_VOCAB,
    adapter_summary,
    annotation_mask,
    attach_insertion_assets,
    build_feasibility_tasks,
    coco_category_overlap,
    load_coco_instances,
    main,
)


if __name__ == "__main__":
    raise SystemExit(main())
