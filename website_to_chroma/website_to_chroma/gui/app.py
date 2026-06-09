"""GUI application entry point."""

from __future__ import annotations

import logging

from website_to_chroma.gui.main_window import MainWindow


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_app() -> None:
    setup_logging()
    app = MainWindow()
    app.mainloop()
