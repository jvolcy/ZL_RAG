"""Per-tab configuration defaults and serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any
from urllib.parse import urlparse


@dataclass
class Tab1Config:
    start_url: str = "https://example.com"
    max_pages: int = 100
    crawl_delay: float = 0.0
    request_timeout: int = 30
    user_agent: str = "WebsiteToChromaIndexer/1.0"
    all_internal_links: bool = False
    include_start_descendants: bool = True
    include_siblings: bool = True
    output_path: str = ""

    @property
    def base_domain(self) -> str:
        return urlparse(self.start_url).netloc

    def validate(self) -> None:
        if not self.start_url.startswith(("http://", "https://")):
            raise ValueError("start_url must begin with http:// or https://")
        if self.max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        if self.crawl_delay < 0:
            raise ValueError("crawl_delay must be non-negative")
        if self.request_timeout < 1:
            raise ValueError("request_timeout must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tab1Config:
        migrated = dict(data)
        if "crawl_scope" in migrated and "all_internal_links" not in migrated:
            scope = migrated.pop("crawl_scope")
            migrated["all_internal_links"] = scope == "internal"
            migrated["include_siblings"] = scope == "restricted"
        if "descendants_only" in migrated and "include_start_descendants" not in migrated:
            descendants_only = migrated.pop("descendants_only")
            migrated["include_start_descendants"] = True
            if descendants_only:
                migrated["include_siblings"] = False
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in migrated.items() if k in valid})


@dataclass
class Tab2Config:
    input_path: str = ""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    output_path: str = ""

    def validate(self) -> None:
        if not self.input_path:
            raise ValueError("input_path is required")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be at least 1")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tab2Config:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid})


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

EMBEDDING_MODEL_CHOICES: tuple[str, ...] = (
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "nomic-ai/nomic-embed-text-v1.5",
    "sentence-transformers/all-MiniLM-L6-v2",
)


@dataclass
class Tab3Config:
    input_path: str = ""
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    batch_size: int = 32
    chroma_path: str = ""
    collection_name: str = "website"
    rebuild: bool = False
    wipe_database: bool = False
    store_batch_size: int = 100

    def validate(self) -> None:
        if not self.input_path:
            raise ValueError("input_path is required")
        if not self.chroma_path:
            raise ValueError("chroma_path is required")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if self.store_batch_size < 1:
            raise ValueError("store_batch_size must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tab3Config:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid})


def tab1_defaults(project_root: str) -> dict[str, Any]:
    return Tab1Config(output_path=f"{project_root}/outputs/crawl").to_dict()


def tab2_defaults(project_root: str, input_path: str = "") -> dict[str, Any]:
    return Tab2Config(
        input_path=input_path,
        output_path=f"{project_root}/outputs/chunks",
    ).to_dict()


def tab3_defaults(project_root: str, input_path: str = "") -> dict[str, Any]:
    return Tab3Config(
        input_path=input_path,
        chroma_path=f"{project_root}/chroma_db",
    ).to_dict()
