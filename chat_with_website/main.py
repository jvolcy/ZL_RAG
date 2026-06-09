#!/usr/bin/env python3
"""Entry point for the Website Knowledge Assistant."""

from __future__ import annotations

import logging
import sys

from chat_with_website.config import (
    DEFAULT_OLLAMA_MODEL,
    build_arg_parser,
    load_config,
)
from chat_with_website.gui.app import run_app


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if getattr(args, "no_gui", False):
        args.cli = True

    if args.cli:
        from chat_with_website.chat import run_chat
        from chat_with_website.startup import initialize

        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
        )

        if not args.config and not args.project and not args.chroma_path:
            parser.error(
                "CLI mode requires --chroma-path, --project, or --config with chroma_path set."
            )

        try:
            config = load_config(
                config_path=args.config,
                project_path=args.project,
                chroma_path=args.chroma_path,
                collection_name=args.collection_name,
                embedding_model=args.embedding_model,
                top_k=args.top_k,
                ollama_host=args.ollama_host,
                ollama_model=args.ollama_model or DEFAULT_OLLAMA_MODEL,
                max_history_turns=args.max_history_turns,
                memory_enabled=False if args.no_memory else None,
            )
            ctx = initialize(config)
        except (ValueError, RuntimeError) as exc:
            print(f"Startup failed: {exc}", file=sys.stderr)
            return 1

        run_chat(ctx)
        return 0

    initial_config = None
    if args.config or args.project or args.chroma_path:
        try:
            initial_config = load_config(
                config_path=args.config,
                project_path=args.project,
                chroma_path=args.chroma_path,
                collection_name=args.collection_name,
                embedding_model=args.embedding_model,
                top_k=args.top_k,
                ollama_host=args.ollama_host,
                ollama_model=args.ollama_model or DEFAULT_OLLAMA_MODEL,
                max_history_turns=args.max_history_turns,
                memory_enabled=False if args.no_memory else None,
            )
        except ValueError as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 1

    run_app(initial_config=initial_config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
