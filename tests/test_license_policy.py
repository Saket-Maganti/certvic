from certvic.data.license_policy import release_mode_for_source, validate_license_for_split
from certvic.schema import SourceImageRecord


def test_license_policy_blocks_unknown_for_real():
    record = SourceImageRecord(source_id="s", source_name="n", license_category="unknown", redistribution_allowed=False)
    assert release_mode_for_source(record) == "blocked_until_verified"
    assert validate_license_for_split(record, "pilot")
