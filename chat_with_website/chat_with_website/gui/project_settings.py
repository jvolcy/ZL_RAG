"""Project settings helpers for the GUI."""

from __future__ import annotations

from pathlib import Path

from chat_with_website.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_MODEL,
    EMBEDDING_MODEL_CHOICES,
    _load_project_tab3,
)
from chat_with_website.ollama_models import list_installed_models


def embedding_choices(selected: str) -> list[str]:
    values = list(EMBEDDING_MODEL_CHOICES)
    if selected and selected not in values:
        values.insert(0, selected)
    return values


def ollama_choices(host: str, selected: str) -> list[str]:
    installed = list_installed_models(host)
    values = installed.copy()
    for candidate in (selected, DEFAULT_OLLAMA_MODEL):
        if candidate and candidate not in values:
            values.insert(0, candidate)
    return values or [DEFAULT_OLLAMA_MODEL]


def read_project_settings(project_path: str) -> dict[str, str]:
    project = Path(project_path.strip())
    if not project.is_dir() or not (project / "tab3_config.json").is_file():
        return {}

    try:
        tab3 = _load_project_tab3(project)
    except (ValueError, OSError):
        return {}

    return {
        "embedding_model": tab3.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
        "collection_name": tab3.get("collection_name", "website"),
        "chroma_path": tab3.get("chroma_path", ""),
    }
