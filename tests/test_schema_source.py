import pytest
from pydantic import ValidationError

from certvic.schema import LicenseCategory, MaskRecord, SourceImageRecord


def test_valid_source_record():
    record = SourceImageRecord(
        source_id="s1",
        source_name="example",
        license_category=LicenseCategory.CC0.value,
        redistribution_allowed=True,
    )
    assert record.source_id == "s1"


def test_invalid_bbox():
    with pytest.raises(ValidationError):
        MaskRecord(
            mask_id="m1",
            source_id="s1",
            mask_path="mask.png",
            object_label="object",
            bbox_xyxy=[0, 0, 0, 5],
            method="test",
        )
