"""Background task execution with cancellation support."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_queue.put(self.format(record))
        except Exception:
            self.handleError(record)


class TaskRunner:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def cancel(self) -> None:
        self._cancel_event.set()

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

        self._cancel_event.clear()
        self._running = True
        kwargs = kwargs or {}

        def worker() -> None:
            handler: QueueLogHandler | None = None
            try:
                log_queue: queue.Queue[str] = kwargs.pop("_log_queue", queue.Queue())
                handler = QueueLogHandler(log_queue)
                handler.setFormatter(
                    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
                )
                root_logger = logging.getLogger()
                root_logger.addHandler(handler)
                kwargs["cancel_event"] = self._cancel_event
                result = target(**kwargs)
                if on_success:
                    on_success(result)
            except Exception as exc:
                if on_error:
                    on_error(exc)
            finally:
                if handler is not None:
                    logging.getLogger().removeHandler(handler)
                self._running = False
                if on_finished:
                    on_finished()

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
