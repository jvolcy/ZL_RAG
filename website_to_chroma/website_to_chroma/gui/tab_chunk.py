"""Tab 2: Text chunking."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path

from website_to_chroma.chunker import chunk_pages
from website_to_chroma.gui.widgets import (
    FilePickerRow,
    LabeledEntry,
    PipelineTab,
    versioned_output_path,
)
from website_to_chroma.io_formats import load_pages, save_chunks
from website_to_chroma.tab_configs import Tab2Config, tab2_defaults

logger = logging.getLogger(__name__)


class ChunkTab(PipelineTab):
    def __init__(self, master: tk.Misc, *, on_output_created) -> None:
        self.on_output_created = on_output_created
        self.input_path = tk.StringVar()
        self.chunk_size = tk.IntVar()
        self.chunk_overlap = tk.IntVar()
        self.output_path = tk.StringVar()
        super().__init__(master)
        self._build_config_fields()

    def _build_config_fields(self) -> None:
        FilePickerRow(
            self.config_frame,
            "Input (crawl JSONL)",
            textvariable=self.input_path,
            pick_type="file",
            on_change=self._on_input_changed,
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame, "Chunk size", textvariable=self.chunk_size, on_change=self._schedule_save
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame,
            "Chunk overlap",
            textvariable=self.chunk_overlap,
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)
        FilePickerRow(
            self.config_frame,
            "Output directory",
            textvariable=self.output_path,
            pick_type="directory",
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)

    def _on_input_changed(self) -> None:
        self._schedule_save()
        self.update_staleness_warning()

    def load_config(self) -> None:
        if not self.project:
            return
        latest_crawl = self.project.latest_crawl_path()
        default_input = str(latest_crawl) if latest_crawl else ""
        data = self.project.load_tab_config(
            2, tab2_defaults(str(self.project.root), default_input)
        )
        if default_input and not data.get("input_path"):
            data["input_path"] = default_input

        self.input_path.set(data.get("input_path", default_input))
        self.chunk_size.set(int(data.get("chunk_size", 1000)))
        self.chunk_overlap.set(int(data.get("chunk_overlap", 200)))
        self.output_path.set(
            data.get("output_path", str(self.project.root / "outputs" / "chunks"))
        )
        self.update_staleness_warning()

    def save_config(self) -> None:
        if not self.project:
            return
        self.project.save_tab_config(2, self._current_config().to_dict())

    def update_staleness_warning(self) -> None:
        if not self.project:
            return
        selected = Path(self.input_path.get()) if self.input_path.get() else None
        warning = self.project.staleness_warning(2, selected)
        self.warning_var.set(warning or "")

    def set_default_input(self, path: Path) -> None:
        self.input_path.set(str(path))
        self._schedule_save()
        self.update_staleness_warning()

    def _current_config(self) -> Tab2Config:
        return Tab2Config(
            input_path=self.input_path.get().strip(),
            chunk_size=self.chunk_size.get(),
            chunk_overlap=self.chunk_overlap.get(),
            output_path=self.output_path.get().strip(),
        )

    def start_task(self) -> None:
        try:
            config = self._current_config()
            config.validate()
        except ValueError as exc:
            self.status_var.set("Configuration error")
            self.log_panel.append(str(exc))
            self._task_finished()
            return

        self.task_runner.run(
            _run_chunk,
            kwargs={
                "config": config,
                "_log_queue": self.log_queue,
            },
            on_success=self._on_success,
            on_error=self._on_error,
            on_finished=self._task_finished,
        )

    def _on_success(self, result: dict) -> None:
        if not self.project:
            return
        output_path = Path(result["output_path"])
        input_path = Path(result["input_path"])
        self.project.record_chunks_run(output_path, input_path=input_path)
        self.after(0, lambda: self.status_var.set(f"Done — {result['chunks']} chunks saved"))
        self.after(0, lambda: self.progress_var.set(100.0))
        self.after(0, lambda: self.on_output_created(output_path))
        self.after(0, self.update_staleness_warning)

    def _on_error(self, exc: Exception) -> None:
        logger.exception("Chunking failed")
        self.after(0, lambda: self.status_var.set("Failed"))
        self.after(0, lambda: self.log_panel.append(f"Error: {exc}"))


def _run_chunk(*, config: Tab2Config, cancel_event) -> dict:
    if cancel_event.is_set():
        return {"chunks": 0, "output_path": "", "input_path": config.input_path}

    pages = load_pages(Path(config.input_path))
    chunks = chunk_pages(
        pages,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    output_path = versioned_output_path(Path(config.output_path), "chunks")
    save_chunks(output_path, chunks)
    return {
        "chunks": len(chunks),
        "output_path": str(output_path),
        "input_path": config.input_path,
    }
