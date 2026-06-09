"""ChromaDB vector retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source_url: str
    chunk_index: int
    distance: float | None


class Retriever:
    def __init__(self, chroma_path: str, collection_name: str) -> None:
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_collection(name=collection_name)
        count = self.collection.count()
        logger.info(
            "Connected to collection '%s' at %s (%d documents)",
            collection_name,
            chroma_path,
            count,
        )

    @property
    def document_count(self) -> int:
        return self.collection.count()

    def retrieve(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for index, text in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source_url=str(metadata.get("source_url", "unknown")),
                    chunk_index=int(metadata.get("chunk_index", -1)),
                    distance=distance,
                )
            )
        return chunks
