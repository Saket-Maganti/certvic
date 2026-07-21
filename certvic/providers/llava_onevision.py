"""LLaVA-OneVision adapter scaffold."""

from certvic.providers.open_vlm import OpenVLMProvider


class LlavaOneVisionProvider(OpenVLMProvider):
    def __init__(self, config: dict):
        super().__init__({"provider_name": "llava_onevision_7b", **config})
