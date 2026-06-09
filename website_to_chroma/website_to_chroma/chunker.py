"""Text chunking with configurable size and overlap (FR-5)."""

from __future__ import annotations

from dataclasses import dataclass

from website_to_chroma.html_processor import PageContent


@dataclass
class TextChunk:
    text: str
    source_url: str
    chunk_index: int


def chunk_text(
    text: str,
    source_url: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    """Split text into overlapping character-based chunks."""
    if not text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    text_length = len(text)
    step = chunk_size - chunk_overlap

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text_value = text[start:end].strip()
        if chunk_text_value:
            chunks.append(
                TextChunk(
                    text=chunk_text_value,
                    source_url=source_url,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
        if end >= text_length:
            break
        start += step

    return chunks


def chunk_pages(
    pages: list[PageContent],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    """Chunk text from multiple crawled pages."""
    all_chunks: list[TextChunk] = []
    for page in pages:
        all_chunks.extend(
            chunk_text(
                page.text,
                page.url,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return all_chunks
