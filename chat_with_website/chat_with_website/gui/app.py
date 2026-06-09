"""GUI application entry point."""

from __future__ import annotations

import logging

from chat_with_website.config import Config
from chat_with_website.gui.main_window import MainWindow


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_app(initial_config: Config | None = None) -> None:
    setup_logging()
    app = MainWindow(initial_config=initial_config)
    app.mainloop()
