"""Core question-answering logic shared by CLI and GUI."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from chat_with_website.conversation import ConversationMemory
from chat_with_website.prompt import build_messages, deduplicate_source_urls
from chat_with_website.startup import AppContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    source_urls: list[str]
    error: str | None = None


def process_question(
    ctx: AppContext,
    question: str,
    memory: ConversationMemory,
) -> ChatResponse:
    retrieval_query = memory.build_retrieval_query(question)

    try:
        query_embedding = ctx.embedder.embed_query(retrieval_query)
    except Exception as exc:
        logger.exception("Query embedding failed")
        return ChatResponse(answer="", source_urls=[], error=f"Embedding error: {exc}")

    try:
        chunks = ctx.retriever.retrieve(query_embedding, ctx.config.top_k)
    except Exception as exc:
        logger.exception("Retrieval failed")
        return ChatResponse(answer="", source_urls=[], error=f"Retrieval error: {exc}")

    messages = build_messages(
        question,
        chunks,
        history=memory.history_for_llm(),
    )

    try:
        answer = ctx.ollama.generate(messages)
    except RuntimeError as exc:
        logger.exception("Ollama generation failed")
        return ChatResponse(answer="", source_urls=[], error=str(exc))

    memory.add_exchange(question, answer)
    return ChatResponse(
        answer=answer,
        source_urls=deduplicate_source_urls(chunks),
    )
