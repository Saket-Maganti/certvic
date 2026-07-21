from certvic.eval.resume import load_completed_keys
from certvic.io import write_jsonl


def test_load_completed_keys(tmp_path):
    path = tmp_path / "preds.jsonl"
    write_jsonl(path, [{"run_id": "r", "item_id": "i", "image_variant": "original"}])
    assert ("r", "i", "original") in load_completed_keys(str(path))
