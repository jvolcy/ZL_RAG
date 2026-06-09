"""Application configuration."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_COLLECTION_NAME = "website"
DEFAULT_TOP_K = 5
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_PROJECT_PATH = Path("/home/professeur/Documents/ZL_RAG_PROJECTS/my_project1")
DEFAULT_MAX_HISTORY_TURNS = 10

CLEAR_COMMANDS = frozenset({"clear", "/clear"})

EMBEDDING_MODEL_CHOICES: tuple[str, ...] = (
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "nomic-ai/nomic-embed-text-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
)

OLLAMA_MODEL_CHOICES: tuple[str, ...] = (
    "llama3.1:8b",
    "qwen3:14b",
    "qwen3:32b",
    "llama3",
    "mistral",
)

EXIT_COMMANDS = frozenset({"quit", "exit", "q"})


@dataclass
class Config:
    chroma_path: str
    collection_name: str = DEFAULT_COLLECTION_NAME
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    top_k: int = DEFAULT_TOP_K
    ollama_host: str = DEFAULT_OLLAMA_HOST
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    max_history_turns: int = DEFAULT_MAX_HISTORY_TURNS
    memory_enabled: bool = True

    def validate(self) -> None:
        if not self.chroma_path:
            raise ValueError("chroma_path is required")
        if not Path(self.chroma_path).exists():
            raise ValueError(f"ChromaDB path does not exist: {self.chroma_path}")
        if not self.collection_name:
            raise ValueError("collection_name is required")
        if not self.embedding_model:
            raise ValueError("embedding_model is required")
        if not self.ollama_model:
            raise ValueError("ollama_model is required")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")
        if self.max_history_turns < 1:
            raise ValueError("max_history_turns must be at least 1")


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def _load_project_tab3(project_path: Path) -> dict[str, Any]:
    tab3_path = project_path / "tab3_config.json"
    if not tab3_path.is_file():
        raise ValueError(f"No tab3_config.json found in project: {project_path}")
    with tab3_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_config(
    *,
    config_path: Path | None = None,
    project_path: Path | None = None,
    chroma_path: str | None = None,
    collection_name: str | None = None,
    embedding_model: str | None = None,
    top_k: int | None = None,
    ollama_host: str | None = None,
    ollama_model: str | None = None,
    max_history_turns: int | None = None,
    memory_enabled: bool | None = None,
) -> Config:
    values: dict[str, Any] = {}

    if config_path is not None:
        values.update(_load_yaml(config_path))

    if project_path is not None:
        tab3 = _load_project_tab3(project_path)
        values.setdefault("chroma_path", tab3.get("chroma_path"))
        values.setdefault("collection_name", tab3.get("collection_name"))
        values.setdefault("embedding_model", tab3.get("embedding_model"))

    overrides = {
        "chroma_path": chroma_path,
        "collection_name": collection_name,
        "embedding_model": embedding_model,
        "top_k": top_k,
        "ollama_host": ollama_host,
        "ollama_model": ollama_model,
        "max_history_turns": max_history_turns,
        "memory_enabled": memory_enabled,
    }
    for key, value in overrides.items():
        if value is not None:
            values[key] = value

    valid = {field.name for field in fields(Config)}
    config = Config(**{k: v for k, v in values.items() if k in valid})
    config.validate()
    return config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chat with website content indexed in ChromaDB using Ollama.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "-p",
        "--project",
        type=Path,
        help="Path to a website_to_chroma project folder (reads tab3_config.json)",
    )
    parser.add_argument(
        "--chroma-path",
        help="Path to ChromaDB persistent storage directory",
    )
    parser.add_argument(
        "--collection",
        dest="collection_name",
        help=f"ChromaDB collection name (default: {DEFAULT_COLLECTION_NAME})",
    )
    parser.add_argument(
        "--embedding-model",
        choices=list(EMBEDDING_MODEL_CHOICES),
        help=(
            "Sentence Transformers model (default: from project tab3_config.json "
            f"or {DEFAULT_EMBEDDING_MODEL})"
        ),
    )
    parser.add_argument(
        "-k",
        "--top-k",
        type=int,
        help=f"Number of chunks to retrieve (default: {DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        help=f"Ollama server URL (default: {DEFAULT_OLLAMA_HOST})",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="ollama_model",
        help=f"Ollama LLM model (default: {DEFAULT_OLLAMA_MODEL})",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in terminal mode instead of the GUI",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-history-turns",
        type=int,
        help=f"Max user/assistant exchanges to retain (default: {DEFAULT_MAX_HISTORY_TURNS})",
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable multi-turn conversation memory",
    )
    return parser
