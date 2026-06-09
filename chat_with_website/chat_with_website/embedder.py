"""Query embedding generation."""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QueryEmbedder:
    def __init__(self, model_name: str) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_query(self, question: str) -> list[float]:
        vector = self.model.encode(
            question,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vector.tolist()
