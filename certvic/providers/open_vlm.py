"""Import-safe base classes for open local VLMs."""

from __future__ import annotations

from certvic.exceptions import MissingOptionalDependencyError


class OpenVLMProvider:
    provider_type = "open_local"
    local_only = True
    cost_policy = "zero_cost_open_local"

    def __init__(self, config: dict):
        self.config = config
        self.provider_name = config.get("provider_name", self.__class__.__name__.lower())
        self.model_name = config.get("model_id", self.provider_name)
        self.model_version = config.get("model_version", "unloaded")
        self._model = None
        self._processor = None

    def _load_transformers(self):
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception as exc:
            raise MissingOptionalDependencyError(
                "Open VLM providers require optional vision dependencies. Install certvic[vision]."
            ) from exc

    def load(self) -> None:
        self._load_transformers()
        raise MissingOptionalDependencyError(
            "This V1 adapter is import-safe scaffolding; fill in model-specific loading before real runs."
        )

    def answer(self, image_path: str, prompt: str) -> str:
        if self._model is None:
            self.load()
        raise RuntimeError("Open VLM generation is not implemented in the V1 scaffold.")
