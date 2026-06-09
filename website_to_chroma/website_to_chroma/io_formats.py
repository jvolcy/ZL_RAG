"""JSONL serialization for pipeline stage outputs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from website_to_chroma.chunker import TextChunk
from website_to_chroma.html_processor import PageContent


def _dt_to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _dt_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def save_pages(path: Path, pages: list[PageContent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for page in pages:
            record = {
                "url": page.url,
                "text": page.text,
                "crawled_at": _dt_to_iso(page.crawled_at),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_pages(path: Path) -> list[PageContent]:
    pages: list[PageContent] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            pages.append(
                PageContent(
                    url=record["url"],
                    text=record["text"],
                    crawled_at=_dt_from_iso(record["crawled_at"]),
                )
            )
    return pages


def save_chunks(path: Path, chunks: list[TextChunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            record = {
                "text": chunk.text,
                "source_url": chunk.source_url,
                "chunk_index": chunk.chunk_index,
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_chunks(path: Path) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            chunks.append(
                TextChunk(
                    text=record["text"],
                    source_url=record["source_url"],
                    chunk_index=record["chunk_index"],
                )
            )
    return chunks
