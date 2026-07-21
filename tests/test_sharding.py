from certvic.eval.sharding import item_in_shard


def test_sharding_complete_no_overlap():
    items = [f"i{x}" for x in range(100)]
    shards = [{i for i in items if item_in_shard(i, s, 4)} for s in range(4)]
    assert set.union(*shards) == set(items)
    assert not any(shards[i] & shards[j] for i in range(4) for j in range(i + 1, 4))
