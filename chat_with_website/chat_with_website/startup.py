"""Startup initialization and health checks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from chat_with_website.config import Config
from chat_with_website.embedder import QueryEmbedder
from chat_with_website.ollama_client import OllamaClient
from chat_with_website.retriever import Retriever

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    config: Config
    embedder: QueryEmbedder
    retriever: Retriever
    ollama: OllamaClient


def _verify_collection(chroma_path: str, collection_name: str) -> None:
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(name=collection_name)
    except (ValueError, chromadb.errors.NotFoundError) as exc:
        raise ValueError(
            f"ChromaDB collection '{collection_name}' was not found at {chroma_path}. "
            "Run the website_to_chroma indexer (Tab 3) first."
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Failed to connect to ChromaDB at {chroma_path}: {exc}"
        ) from exc

    count = collection.count()
    if count == 0:
        raise ValueError(
            f"ChromaDB collection '{collection_name}' exists but contains no documents. "
            "Embed and store website chunks before chatting."
        )
    logger.info("Collection '%s' verified (%d documents)", collection_name, count)


def initialize(config: Config) -> AppContext:
    logger.info("Starting Website Knowledge Assistant")

    _verify_collection(config.chroma_path, config.collection_name)

    try:
        embedder = QueryEmbedder(config.embedding_model)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load embedding model '{config.embedding_model}': {exc}"
        ) from exc

    try:
        retriever = Retriever(config.chroma_path, config.collection_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize retriever: {exc}") from exc

    ollama = OllamaClient(config.ollama_host, config.ollama_model)
    try:
        ollama.verify()
    except (ConnectionError, ValueError) as exc:
        raise RuntimeError(str(exc)) from exc

    return AppContext(
        config=config,
        embedder=embedder,
        retriever=retriever,
        ollama=ollama,
    )
