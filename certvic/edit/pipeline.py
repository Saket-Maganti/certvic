"""Edit pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from certvic.edit.control import color_control_edit
from certvic.edit.displace import displace_object
from certvic.edit.masks import load_binary_mask
from certvic.edit.occlude import occlude_region
from certvic.hashing import sha256_file
from certvic.schema import EditSpec, EditType, SourceImageRecord
from certvic.schema.source import MaskRecord


def build_edit_for_task(
    source_record: SourceImageRecord,
    mask_record: MaskRecord,
    task_family: str,
    edit_type: str,
    config: dict,
) -> EditSpec:
    out_dir = Path(config.get("out_dir", "data/edits/smoke"))
    out_path = out_dir / f"{source_record.source_id}_{edit_type}.png"
    mask = load_binary_mask(mask_record.mask_path)
    if edit_type == EditType.DISPLACE.value:
        displace_object(source_record.local_path, mask, str(out_path), offset=tuple(config.get("offset", (16, 0))))
    elif edit_type == EditType.OCCLUDE.value:
        occlude_region(source_record.local_path, mask, str(out_path))
    else:
        color_control_edit(source_record.local_path, mask, str(out_path))
    return EditSpec(
        edit_id=f"edit_{source_record.source_id}",
        source_id=source_record.source_id,
        mask_id=mask_record.mask_id,
        edit_type=edit_type,
        task_family=task_family,
        domain=config.get("domain", "synthetic_sanity"),
        seed=int(config.get("seed", 0)),
        params=config,
        expected_effect=f"{task_family} smoke edit",
        single_factor=True,
        edited_image_path=str(out_path),
        edited_sha256=sha256_file(out_path),
    )
