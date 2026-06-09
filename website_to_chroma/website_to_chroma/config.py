"""Configuration loading from defaults, YAML file, and CLI arguments."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

# Default constants (FR-1)
#DEFAULT_START_URL = "https://example.com"
DEFAULT_START_URL = "http://serveurscolaire.local:8080/content/wikipedia_en_all_mini_2026-03/Main_Page"
#DEFAULT_MAX_PAGES = 100
DEFAULT_MAX_PAGES = 10000
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_CHROMA_PATH = "./chroma_db"
DEFAULT_COLLECTION_NAME = "website"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BATCH_SIZE = 32
DEFAULT_USER_AGENT = "WebsiteToChromaIndexer/1.0"
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_CRAWL_DELAY = 0.0


@dataclass
class Config:
    start_url: str = DEFAULT_START_URL
    max_pages: int = DEFAULT_MAX_PAGES
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    chroma_path: str = DEFAULT_CHROMA_PATH
    collection_name: str = DEFAULT_COLLECTION_NAME
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    batch_size: int = DEFAULT_BATCH_SIZE
    rebuild: bool = False
    user_agent: str = DEFAULT_USER_AGENT
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    crawl_delay: float = DEFAULT_CRAWL_DELAY

    @property
    def base_domain(self) -> str:
        return urlparse(self.start_url).netloc

    def validate(self) -> None:
        if not self.start_url.startswith(("http://", "https://")):
            raise ValueError("start_url must begin with http:// or https://")
        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")


def _apply_overrides(config: Config, overrides: dict[str, Any]) -> Config:
    valid_fields = {f.name for f in fields(Config)}
    for key, value in overrides.items():
        if key in valid_fields and value is not None:
            setattr(config, key, value)
    return config


def load_config_from_file(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl a website, generate embeddings, and store them in ChromaDB.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to a YAML configuration file.",
    )
    parser.add_argument("--start-url", help="URL to begin crawling from.")
    parser.add_argument(
        "--max-pages",
        type=int,
        help=f"Maximum number of pages to crawl (default: {DEFAULT_MAX_PAGES}).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help=f"Characters per text chunk (default: {DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        help=f"Overlap between chunks in characters (default: {DEFAULT_CHUNK_OVERLAP}).",
    )
    parser.add_argument(
        "--chroma-path",
        help=f"ChromaDB storage directory (default: {DEFAULT_CHROMA_PATH}).",
    )
    parser.add_argument(
        "--collection-name",
        help=f"ChromaDB collection name (default: {DEFAULT_COLLECTION_NAME}).",
    )
    parser.add_argument(
        "--embedding-model",
        help=f"Sentence Transformer model name (default: {DEFAULT_EMBEDDING_MODEL}).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help=f"Embedding batch size (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete the existing collection before re-indexing.",
    )
    parser.add_argument(
        "--crawl-delay",
        type=float,
        help=f"Seconds to wait between page requests (default: {DEFAULT_CRAWL_DELAY}).",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        help=f"HTTP request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT}).",
    )
    return parser


def config_from_args(args: argparse.Namespace | None = None) -> Config:
    parser = build_parser()
    parsed = parser.parse_args(args)

    config = Config()

    if parsed.config:
        file_data = load_config_from_file(parsed.config)
        config = _apply_overrides(config, file_data)

    cli_overrides = {
        "start_url": parsed.start_url,
        "max_pages": parsed.max_pages,
        "chunk_size": parsed.chunk_size,
        "chunk_overlap": parsed.chunk_overlap,
        "chroma_path": parsed.chroma_path,
        "collection_name": parsed.collection_name,
        "embedding_model": parsed.embedding_model,
        "batch_size": parsed.batch_size,
        "rebuild": parsed.rebuild or None,
        "crawl_delay": parsed.crawl_delay,
        "request_timeout": parsed.request_timeout,
    }
    config = _apply_overrides(config, cli_overrides)
    config.validate()
    return config
