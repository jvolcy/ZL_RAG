"""Embedding generation with Sentence Transformers (FR-6)."""

from __future__ import annotations

import logging
from threading import Event
from typing import Callable, Sequence

from sentence_transformers import SentenceTransformer

from website_to_chroma.chunker import TextChunk

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


class Embedder:
    def __init__(self, model_name: str) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed_chunks(
        self,
        chunks: Sequence[TextChunk],
        *,
        batch_size: int,
        on_progress: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> list[list[float]]:
        texts = [chunk.text for chunk in chunks]
        total = len(texts)
        logger.info("Generating embeddings for %d chunks (batch_size=%d)", total, batch_size)

        if total == 0:
            return []

        all_embeddings: list[list[float]] = []
        for start in range(0, total, batch_size):
            if cancel_event and cancel_event.is_set():
                logger.info("Embedding cancelled after %d / %d chunks", start, total)
                break
            end = min(start + batch_size, total)
            batch = texts[start:end]
            batch_embeddings = self.model.encode(
                batch,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            all_embeddings.extend(batch_embeddings.tolist())
            if on_progress:
                on_progress(end, total)

        return all_embeddings
