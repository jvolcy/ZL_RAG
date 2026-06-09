"""Background task execution for the GUI."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class TaskRunner:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def run(
        self,
        target: Callable[..., Any],
        *,
        kwargs: dict[str, Any] | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        if self._running:
            raise RuntimeError("A task is already running")

        self._running = True
        kwargs = kwargs or {}

        def worker() -> None:
            try:
                result = target(**kwargs)
                if on_success:
                    on_success(result)
            except Exception as exc:
                if on_error:
                    on_error(exc)
            finally:
                self._running = False
                if on_finished:
                    on_finished()

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
