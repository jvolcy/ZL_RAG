"""Embedding generation with Sentence Transformers (FR-6)."""

from __future__ import annotations

import logging
from typing import Sequence

from sentence_transformers import SentenceTransformer

from website_to_chroma.chunker import TextChunk

logger = logging.getLogger(__name__)


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
    ) -> list[list[float]]:
        texts = [chunk.text for chunk in chunks]
        logger.info("Generating embeddings for %d chunks (batch_size=%d)", len(texts), batch_size)
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > batch_size,
            convert_to_numpy=True,
        )
        return embeddings.tolist()
