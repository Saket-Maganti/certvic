"""Deterministic sharding."""

from __future__ import annotations

from certvic.hashing import stable_int_hash


def shard_for_item(item_id: str, num_shards: int) -> int:
    if num_shards <= 0:
        raise ValueError("num_shards must be positive")
    return stable_int_hash(item_id) % num_shards


def item_in_shard(item_id: str, shard_index: int, num_shards: int) -> bool:
    if shard_index < 0 or shard_index >= num_shards:
        raise ValueError("shard_index must be in [0, num_shards)")
    return shard_for_item(item_id, num_shards) == shard_index
