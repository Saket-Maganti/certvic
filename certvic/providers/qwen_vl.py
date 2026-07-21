"""Qwen2.5-VL adapter scaffold."""

from certvic.providers.open_vlm import OpenVLMProvider


class QwenVLProvider(OpenVLMProvider):
    def __init__(self, config: dict):
        super().__init__({"provider_name": "qwen2_5_vl_7b", **config})
