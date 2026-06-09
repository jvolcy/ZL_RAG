"""ChromaDB vector storage (FR-7, FR-8)."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Sequence

import chromadb

from website_to_chroma.chunker import TextChunk

logger = logging.getLogger(__name__)


def wipe_chroma_database(chroma_path: str) -> None:
    """Delete the entire ChromaDB directory and recreate it empty."""
    path = Path(chroma_path).resolve()
    if path.exists():
        shutil.rmtree(path)
        logger.info("Wiped ChromaDB directory at %s", path)
    path.mkdir(parents=True, exist_ok=True)


def _chunk_id(chunk: TextChunk) -> str:
    digest = hashlib.sha256(
        f"{chunk.source_url}:{chunk.chunk_index}:{chunk.text[:64]}".encode()
    ).hexdigest()[:16]
    return f"{chunk.source_url}#chunk-{chunk.chunk_index}-{digest}"


class ChromaStorage:
    def __init__(self, chroma_path: str, collection_name: str) -> None:
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info(
            "ChromaDB collection '%s' ready at %s (%d existing documents)",
            collection_name,
            chroma_path,
            self.collection.count(),
        )

    def rebuild_collection(self) -> None:
        """Delete and recreate the collection (FR-8)."""
        logger.info("Rebuilding collection '%s'", self.collection_name)
        try:
            self.client.delete_collection(self.collection_name)
        except (ValueError, chromadb.errors.NotFoundError):
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def store_chunks(
        self,
        chunks: Sequence[TextChunk],
        embeddings: Sequence[Sequence[float]],
        *,
        batch_size: int = 100,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        stored = 0
        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start : start + batch_size]
            batch_embeddings = embeddings[start : start + batch_size]

            ids = [_chunk_id(c) for c in batch_chunks]
            documents = [c.text for c in batch_chunks]
            metadatas = [
                {
                    "source_url": c.source_url,
                    "chunk_index": c.chunk_index,
                }
                for c in batch_chunks
            ]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=list(batch_embeddings),
                metadatas=metadatas,
            )
            stored += len(batch_chunks)
            logger.info("Stored %d / %d embeddings", stored, len(chunks))

        return stored
