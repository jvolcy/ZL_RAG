"""Multi-turn conversation memory for chat sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Turn:
    role: Literal["user", "assistant"]
    content: str


class ConversationMemory:
    def __init__(self, *, max_turns: int = 10, enabled: bool = True) -> None:
        self.max_turns = max_turns
        self.enabled = enabled
        self._turns: list[Turn] = []

    @property
    def turn_count(self) -> int:
        return len(self._turns) // 2

    def clear(self) -> None:
        self._turns.clear()

    def add_exchange(self, user_message: str, assistant_message: str) -> None:
        if not self.enabled:
            return
        self._turns.append(Turn("user", user_message))
        self._turns.append(Turn("assistant", assistant_message))
        self._trim()

    def history_for_llm(self) -> list[dict[str, str]]:
        if not self.enabled:
            return []
        return [{"role": turn.role, "content": turn.content} for turn in self._turns]

    def build_retrieval_query(
        self,
        question: str,
        *,
        max_prior_user_turns: int = 3,
    ) -> str:
        if not self.enabled or not self._turns:
            return question

        prior_questions = [
            turn.content for turn in self._turns if turn.role == "user"
        ][-max_prior_user_turns:]
        if not prior_questions:
            return question

        return "\n".join([*prior_questions, question])

    def _trim(self) -> None:
        max_messages = self.max_turns * 2
        if len(self._turns) > max_messages:
            self._turns = self._turns[-max_messages:]
