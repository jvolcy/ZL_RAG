"""Ollama LLM integration."""

from __future__ import annotations

import logging

import ollama
from ollama import Client

logger = logging.getLogger(__name__)


def _resolve_model_name(requested: str, available: list[str]) -> str | None:
    if requested in available:
        return requested
    for name in available:
        if name.split(":", 1)[0] == requested:
            return name
    return None


class OllamaClient:
    def __init__(self, host: str, model: str) -> None:
        self.host = host
        self.requested_model = model
        self.model = model
        self.client = Client(host=host)

    def verify(self) -> None:
        try:
            models = self.client.list()
        except Exception as exc:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.host}. "
                "Ensure Ollama is running (e.g. `ollama serve`)."
            ) from exc

        available = [model.model for model in models.models if model.model]
        resolved = _resolve_model_name(self.requested_model, available)
        if resolved is None:
            names = ", ".join(sorted(available)) if available else "(none)"
            raise ValueError(
                f"Ollama model '{self.requested_model}' is not available. "
                f"Installed models: {names}. "
                f"Pull it with: ollama pull {self.requested_model}"
            )

        self.model = resolved
        logger.info("Ollama ready at %s using model '%s'", self.host, self.model)

    def generate(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self.client.chat(model=self.model, messages=messages)
        except ollama.ResponseError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(
                f"Ollama connection error at {self.host}: {exc}"
            ) from exc

        content = response.message.content
        if not content:
            raise RuntimeError("Ollama returned an empty response")
        return content.strip()
