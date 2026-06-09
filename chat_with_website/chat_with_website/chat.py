"""Interactive terminal chat session."""

from __future__ import annotations

import sys

from chat_with_website.config import CLEAR_COMMANDS, EXIT_COMMANDS
from chat_with_website.conversation import ConversationMemory
from chat_with_website.handler import process_question
from chat_with_website.startup import AppContext


def _print_banner(ctx: AppContext) -> None:
    print()
    print("Website Knowledge Assistant")
    print("=" * 40)
    print(f"ChromaDB:  {ctx.config.chroma_path}")
    print(f"Collection: {ctx.config.collection_name} ({ctx.retriever.document_count} chunks)")
    print(f"Embeddings: {ctx.config.embedding_model}")
    print(f"Ollama:    {ctx.config.ollama_model} @ {ctx.config.ollama_host}")
    print(f"Top K:     {ctx.config.top_k}")
    if ctx.config.memory_enabled:
        print(f"Memory:    last {ctx.config.max_history_turns} exchanges")
    else:
        print("Memory:    off")
    print()
    print("Ask questions about the indexed website content.")
    print("Follow-up questions use prior turns for context.")
    print("Type clear to reset the conversation.")
    print("Type quit, exit, or q to leave.")
    print()


def _print_response(answer: str, source_urls: list[str]) -> None:
    print()
    print(answer)
    if source_urls:
        print()
        print("Sources:")
        for url in source_urls:
            print(f"  - {url}")
    print()


def run_chat(ctx: AppContext) -> None:
    memory = ConversationMemory(
        max_turns=ctx.config.max_history_turns,
        enabled=ctx.config.memory_enabled,
    )
    _print_banner(ctx)

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue

        lowered = question.lower()
        if lowered in EXIT_COMMANDS:
            break
        if lowered in CLEAR_COMMANDS:
            memory.clear()
            print("Conversation cleared.\n")
            continue

        result = process_question(ctx, question, memory)
        if result.error:
            print(f"\nError: {result.error}", file=sys.stderr)
            continue
        _print_response(result.answer, result.source_urls)

    print("Goodbye.")
