"""InternVL adapter scaffold."""

from certvic.providers.open_vlm import OpenVLMProvider


class InternVLProvider(OpenVLMProvider):
    def __init__(self, config: dict):
        super().__init__({"provider_name": "internvl_8b", **config})
