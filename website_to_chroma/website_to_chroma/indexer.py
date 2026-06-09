"""Main indexing orchestration."""

from __future__ import annotations

import logging

from website_to_chroma.chunker import chunk_pages
from website_to_chroma.config import Config
from website_to_chroma.crawler import crawl_website
from website_to_chroma.embedder import Embedder
from website_to_chroma.storage import ChromaStorage

logger = logging.getLogger(__name__)


def run_indexer(config: Config) -> dict[str, int]:
    """Crawl, chunk, embed, and store website content in ChromaDB."""
    pages = list(crawl_website(config))
    logger.info("Crawled %d pages", len(pages))

    if not pages:
        logger.warning("No pages successfully crawled; skipping chunking and embedding.")
        return {"pages": 0, "chunks": 0, "embeddings": 0}

    chunks = chunk_pages(
        pages,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    logger.info("Generated %d chunks", len(chunks))

    if not chunks:
        logger.warning("No chunks generated; nothing to store.")
        return {"pages": len(pages), "chunks": 0, "embeddings": 0}

    storage = ChromaStorage(config.chroma_path, config.collection_name)
    if config.rebuild:
        storage.rebuild_collection()

    embedder = Embedder(config.embedding_model)
    embeddings = embedder.embed_chunks(chunks, batch_size=config.batch_size)
    stored = storage.store_chunks(chunks, embeddings)

    logger.info(
        "Indexing complete: %d pages, %d chunks, %d embeddings stored",
        len(pages),
        len(chunks),
        stored,
    )
    return {"pages": len(pages), "chunks": len(chunks), "embeddings": stored}
