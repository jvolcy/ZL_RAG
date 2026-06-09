#!/usr/bin/env python3
"""CLI entry point for the Website Knowledge Base Indexer."""

from __future__ import annotations

import logging
import sys

from website_to_chroma.config import config_from_args
from website_to_chroma.indexer import run_indexer


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    setup_logging()
    try:
        config = config_from_args()
    except ValueError as exc:
        logging.error("Configuration error: %s", exc)
        return 1

    logging.info("Starting indexer for %s", config.start_url)
    stats = run_indexer(config)
    logging.info(
        "Done — pages: %d, chunks: %d, embeddings: %d",
        stats["pages"],
        stats["chunks"],
        stats["embeddings"],
    )
    return 0 if stats["pages"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
