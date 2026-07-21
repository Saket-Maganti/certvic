from certvic.data.source_manifest import enrich_source_record
from certvic.hashing import stable_record_hash
from certvic.schema import SourceImageRecord


def test_source_manifest_enriches_release_mode():
    record = SourceImageRecord(source_id="s", source_name="n", license_category="cc0", redistribution_allowed=True)
    enriched = enrich_source_record(record, split="smoke")
    assert enriched["release_mode"] == "pixel_release_ok"
    assert stable_record_hash(enriched)
