"""RAG prompt construction."""

from __future__ import annotations

from chat_with_website.retriever import RetrievedChunk

SYSTEM_INSTRUCTIONS = """You are a helpful assistant that answers questions using only the website content provided below.

Rules:
- Base your answer strictly on the supplied context.
- Do not invent facts, URLs, or details that are not supported by the context.
- If the context does not contain enough information to answer the question, say so clearly.
- When relevant, mention which source pages support your answer.
- Be concise and direct.
- Use prior conversation turns only to interpret follow-up questions; do not treat earlier assistant replies as new facts unless they are supported by the current context."""


def _current_turn_content(question: str, chunks: list[RetrievedChunk]) -> str:
    if chunks:
        context_blocks = []
        for index, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                f"[Source {index}] {chunk.source_url}\n{chunk.text}"
            )
        context_text = "\n\n".join(context_blocks)
        return (
            "Use the following retrieved website excerpts as your only source of information.\n\n"
            f"{context_text}\n\n"
            f"Question: {question}"
        )

    return (
        "No relevant website content was retrieved for this question.\n\n"
        f"Question: {question}\n\n"
        "Tell the user you could not find relevant information in the indexed website content."
    )


def build_messages(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
    ]
    if history:
        messages.extend(history)
    messages.append(
        {"role": "user", "content": _current_turn_content(question, chunks)},
    )
    return messages


def deduplicate_source_urls(chunks: list[RetrievedChunk]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for chunk in chunks:
        if chunk.source_url not in seen:
            seen.add(chunk.source_url)
            ordered.append(chunk.source_url)
    return ordered
