"""Fetch installed Ollama models."""

from __future__ import annotations

import logging

from ollama import Client

logger = logging.getLogger(__name__)


def list_installed_models(host: str = "http://localhost:11434") -> list[str]:
    try:
        client = Client(host=host)
        response = client.list()
    except Exception as exc:
        logger.warning("Could not list Ollama models at %s: %s", host, exc)
        return []
    return sorted(model.model for model in response.models if model.model)
