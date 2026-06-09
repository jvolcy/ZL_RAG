"""Tab 3: Embedding and vector storage."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from website_to_chroma.embedder import Embedder
from website_to_chroma.gui.widgets import FilePickerRow, LabeledCombobox, LabeledEntry, PipelineTab
from website_to_chroma.io_formats import load_chunks
from website_to_chroma.storage import ChromaStorage, wipe_chroma_database
from website_to_chroma.tab_configs import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_MODEL_CHOICES,
    Tab3Config,
    tab3_defaults,
)

logger = logging.getLogger(__name__)


class EmbedTab(PipelineTab):
    def __init__(self, master: tk.Misc) -> None:
        self.input_path = tk.StringVar()
        self.embedding_model = tk.StringVar()
        self.batch_size = tk.IntVar()
        self.chroma_path = tk.StringVar()
        self.collection_name = tk.StringVar()
        self.rebuild = tk.BooleanVar()
        self.wipe_database = tk.BooleanVar()
        self.store_batch_size = tk.IntVar()
        self.embedding_model_combo: LabeledCombobox | None = None
        super().__init__(master)
        self._build_config_fields()

    def _build_config_fields(self) -> None:
        FilePickerRow(
            self.config_frame,
            "Input (chunks JSONL)",
            textvariable=self.input_path,
            pick_type="file",
            on_change=self._on_input_changed,
        ).pack(fill=tk.X, pady=2)
        self.embedding_model_combo = LabeledCombobox(
            self.config_frame,
            "Embedding model",
            textvariable=self.embedding_model,
            values=EMBEDDING_MODEL_CHOICES,
            on_change=self._schedule_save,
        )
        self.embedding_model_combo.pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame, "Embed batch size", textvariable=self.batch_size, on_change=self._schedule_save
        ).pack(fill=tk.X, pady=2)
        FilePickerRow(
            self.config_frame,
            "ChromaDB path",
            textvariable=self.chroma_path,
            pick_type="directory",
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame,
            "Collection name",
            textvariable=self.collection_name,
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame,
            "Store batch size",
            textvariable=self.store_batch_size,
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame,
            "Rebuild collection",
            textvariable=self.rebuild,
            on_change=self._on_rebuild_changed,
        ).pack(fill=tk.X, pady=2)
        LabeledEntry(
            self.config_frame,
            "Wipe entire ChromaDB folder",
            textvariable=self.wipe_database,
            on_change=self._on_wipe_database_changed,
        ).pack(fill=tk.X, pady=2)

    def _set_embedding_model_choices(self, selected: str) -> None:
        if not self.embedding_model_combo:
            return
        values = list(EMBEDDING_MODEL_CHOICES)
        if selected and selected not in values:
            values.insert(0, selected)
        self.embedding_model_combo.set_values(values)

    def _on_rebuild_changed(self) -> None:
        if self.rebuild.get():
            self.wipe_database.set(False)
        self._schedule_save()

    def _on_wipe_database_changed(self) -> None:
        if self.wipe_database.get():
            self.rebuild.set(False)
        self._schedule_save()

    def _on_input_changed(self) -> None:
        self._schedule_save()
        self.update_staleness_warning()

    def load_config(self) -> None:
        if not self.project:
            return
        latest_chunks = self.project.latest_chunks_path()
        default_input = str(latest_chunks) if latest_chunks else ""
        data = self.project.load_tab_config(
            3, tab3_defaults(str(self.project.root), default_input)
        )
        if default_input and not data.get("input_path"):
            data["input_path"] = default_input

        self.input_path.set(data.get("input_path", default_input))
        model = data.get("embedding_model", DEFAULT_EMBEDDING_MODEL)
        self._set_embedding_model_choices(model)
        self.embedding_model.set(model)
        self.batch_size.set(int(data.get("batch_size", 32)))
        self.chroma_path.set(data.get("chroma_path", str(self.project.root / "chroma_db")))
        self.collection_name.set(data.get("collection_name", "website"))
        self.rebuild.set(bool(data.get("rebuild", False)))
        self.wipe_database.set(bool(data.get("wipe_database", False)))
        self.store_batch_size.set(int(data.get("store_batch_size", 100)))
        self.update_staleness_warning()

    def save_config(self) -> None:
        if not self.project:
            return
        self.project.save_tab_config(3, self._current_config().to_dict())

    def update_staleness_warning(self) -> None:
        if not self.project:
            return
        selected = Path(self.input_path.get()) if self.input_path.get() else None
        warning = self.project.staleness_warning(3, selected)
        self.warning_var.set(warning or "")

    def set_default_input(self, path: Path) -> None:
        self.input_path.set(str(path))
        self._schedule_save()
        self.update_staleness_warning()

    def _current_config(self) -> Tab3Config:
        return Tab3Config(
            input_path=self.input_path.get().strip(),
            embedding_model=self.embedding_model.get().strip(),
            batch_size=self.batch_size.get(),
            chroma_path=self.chroma_path.get().strip(),
            collection_name=self.collection_name.get().strip(),
            rebuild=self.rebuild.get(),
            wipe_database=self.wipe_database.get(),
            store_batch_size=self.store_batch_size.get(),
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

        if config.wipe_database and not messagebox.askyesno(
            "Wipe ChromaDB",
            "This will permanently delete ALL collections and data in:\n\n"
            f"{config.chroma_path}\n\n"
            "Continue?",
            icon="warning",
            parent=self.winfo_toplevel(),
        ):
            return

        self.task_runner.run(
            _run_embed,
            kwargs={
                "config": config,
                "_log_queue": self.log_queue,
                "_progress_callback": self._on_progress,
            },
            on_success=self._on_success,
            on_error=self._on_error,
            on_finished=self._task_finished,
        )

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            pct = min(100.0, (done / total) * 100.0)
            self.after(0, lambda p=pct: self.progress_var.set(p))

    def _on_success(self, result: dict) -> None:
        self.after(
            0,
            lambda: self.status_var.set(
                f"Done — {result['embeddings']} embeddings in '{result['collection']}' "
                f"({result['collection_count']} total documents)"
            ),
        )
        self.after(0, lambda: self.progress_var.set(100.0))
        self.after(0, self.update_staleness_warning)
        if self.wipe_database.get():
            self.after(0, self._clear_wipe_flag)

    def _clear_wipe_flag(self) -> None:
        self.wipe_database.set(False)
        self._schedule_save()

    def _on_error(self, exc: Exception) -> None:
        logger.exception("Embedding failed")
        self.after(0, lambda: self.status_var.set("Failed"))
        self.after(0, lambda: self.log_panel.append(f"Error: {exc}"))


def _run_embed(
    *,
    config: Tab3Config,
    cancel_event,
    _progress_callback,
) -> dict:
    chunks = load_chunks(Path(config.input_path))
    if not chunks:
        return {
            "embeddings": 0,
            "collection": config.collection_name,
            "collection_count": 0,
        }

    if config.wipe_database:
        wipe_chroma_database(config.chroma_path)
        storage = ChromaStorage(config.chroma_path, config.collection_name)
    else:
        storage = ChromaStorage(config.chroma_path, config.collection_name)
        if config.rebuild:
            storage.rebuild_collection()

    embedder = Embedder(config.embedding_model)

    def on_progress(done: int, total: int) -> None:
        _progress_callback(done, total)

    embeddings = embedder.embed_chunks(
        chunks,
        batch_size=config.batch_size,
        on_progress=on_progress,
        cancel_event=cancel_event,
    )

    if len(embeddings) != len(chunks):
        chunks = chunks[: len(embeddings)]

    stored = storage.store_chunks(
        chunks,
        embeddings,
        batch_size=config.store_batch_size,
    )
    return {
        "embeddings": stored,
        "collection": config.collection_name,
        "collection_count": storage.collection.count(),
    }
