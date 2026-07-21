"""Disabled-by-default free-tier reference stub."""

from __future__ import annotations

import os

from certvic.exceptions import MissingOptionalDependencyError


class FreeTierReferenceStub:
    provider_name = "free_tier_reference_stub"
    provider_type = "free_tier_reference"
    model_name = "disabled-free-tier-reference"
    model_version = "reference-only-v1"
    local_only = False
    cost_policy = "disabled_by_default_reference_only"

    def __init__(self, config: dict):
        if not config.get("enable_free_tier_reference", False):
            raise MissingOptionalDependencyError("Free-tier reference is disabled by default.")
        if not os.environ.get("CERTVIC_FREE_TIER_API_KEY"):
            raise MissingOptionalDependencyError("CERTVIC_FREE_TIER_API_KEY must be set for reference-only use.")

    def answer(self, image_path: str, prompt: str) -> str:
        raise MissingOptionalDependencyError("Network reference calls are not implemented in V1.")
