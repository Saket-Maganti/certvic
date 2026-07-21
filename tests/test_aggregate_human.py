from certvic.validation.aggregate_human import aggregate_ratings


def test_aggregate_drops_invalid_item(tmp_path):
    ratings = tmp_path / "ratings.csv"
    ratings.write_text(
        "item_id,photorealistic,single_factor,required_change_unambiguous\n"
        "i,no,yes,yes\n"
        "i,no,yes,yes\n",
        encoding="utf-8",
    )
    summary = aggregate_ratings(str(ratings), str(tmp_path / "out.json"), str(tmp_path / "drop.txt"))
    assert summary["drop_items"] == ["i"]
