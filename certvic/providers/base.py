"""Provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class VLMProvider(Protocol):
    provider_name: str
    provider_type: str
    model_name: str
    model_version: str
    local_only: bool
    cost_policy: str

    def answer(self, image_path: str, prompt: str) -> str:
        ...


@dataclass
class ProviderMetadata:
    provider_name: str
    provider_type: str
    model_name: str
    model_version: str
    local_only: bool = True
    cost_policy: str = "zero_cost"
