"""Tab 1: Web crawling and HTML processing."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from website_to_chroma.crawler import crawl_website
from website_to_chroma.gui.widgets import (
    FilePickerRow,
    LabeledEntry,
    PipelineTab,
    versioned_output_path,
)
from website_to_chroma.io_formats import save_pages
from website_to_chroma.tab_configs import Tab1Config, tab1_defaults

logger = logging.getLogger(__name__)


class CrawlTab(PipelineTab):
    def __init__(self, master: tk.Misc, *, on_output_created) -> None:
        self.on_output_created = on_output_created
        self.start_url = tk.StringVar()
        self.max_pages = tk.IntVar()
        self.crawl_delay = tk.DoubleVar()
        self.request_timeout = tk.IntVar()
        self.user_agent = tk.StringVar()
        self.all_internal_links = tk.BooleanVar()
        self.include_start_descendants = tk.BooleanVar()
        self.include_siblings = tk.BooleanVar()
        self.output_path = tk.StringVar()
        super().__init__(master)
        self._build_config_fields()

    def _build_config_fields(self) -> None:
        fields = [
            LabeledEntry(self.config_frame, "Start URL", textvariable=self.start_url, on_change=self._schedule_save),
            LabeledEntry(self.config_frame, "Max pages", textvariable=self.max_pages, on_change=self._schedule_save),
            LabeledEntry(self.config_frame, "Crawl delay (s)", textvariable=self.crawl_delay, on_change=self._schedule_save),
            LabeledEntry(self.config_frame, "Request timeout (s)", textvariable=self.request_timeout, on_change=self._schedule_save),
            LabeledEntry(self.config_frame, "User agent", textvariable=self.user_agent, on_change=self._schedule_save),
        ]
        for field in fields:
            field.pack(fill=tk.X, pady=2)

        scope_frame = ttk.Frame(self.config_frame)
        scope_frame.pack(fill=tk.X, pady=2)
        ttk.Label(scope_frame, text="Crawl scope", width=22).pack(
            side=tk.LEFT, padx=(0, 8), anchor=tk.N
        )
        scope_checks = ttk.Frame(scope_frame)
        scope_checks.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Checkbutton(
            scope_checks,
            text="All internal links",
            variable=self.all_internal_links,
            command=self._on_all_internal_links_changed,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            scope_checks,
            text="Start URL and descendants",
            variable=self.include_start_descendants,
            command=self._on_scope_changed,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            scope_checks,
            text="Siblings of start path and their descendants",
            variable=self.include_siblings,
            command=self._on_scope_changed,
        ).pack(anchor=tk.W)

        FilePickerRow(
            self.config_frame,
            "Output directory",
            textvariable=self.output_path,
            pick_type="directory",
            on_change=self._schedule_save,
        ).pack(fill=tk.X, pady=2)

    def load_config(self) -> None:
        if not self.project:
            return
        data = self.project.load_tab_config(1, tab1_defaults(str(self.project.root)))
        latest = self.project.latest_crawl_path()
        if latest and not data.get("output_path"):
            data["output_path"] = str(latest.parent)

        self.start_url.set(data.get("start_url", ""))
        self.max_pages.set(int(data.get("max_pages", 100)))
        self.crawl_delay.set(float(data.get("crawl_delay", 0.0)))
        self.request_timeout.set(int(data.get("request_timeout", 30)))
        self.user_agent.set(data.get("user_agent", "WebsiteToChromaIndexer/1.0"))
        config = Tab1Config.from_dict(data)
        self.all_internal_links.set(config.all_internal_links)
        self.include_start_descendants.set(config.include_start_descendants)
        self.include_siblings.set(config.include_siblings)
        self.output_path.set(data.get("output_path", str(self.project.root / "outputs" / "crawl")))

    def _on_all_internal_links_changed(self) -> None:
        if self.all_internal_links.get():
            self.include_start_descendants.set(False)
            self.include_siblings.set(False)
        self._schedule_save()

    def _on_scope_changed(self) -> None:
        if self.include_start_descendants.get() or self.include_siblings.get():
            self.all_internal_links.set(False)
        self._schedule_save()

    def save_config(self) -> None:
        if not self.project:
            return
        self.project.save_tab_config(1, self._current_config().to_dict())

    def _current_config(self) -> Tab1Config:
        return Tab1Config(
            start_url=self.start_url.get().strip(),
            max_pages=self.max_pages.get(),
            crawl_delay=self.crawl_delay.get(),
            request_timeout=self.request_timeout.get(),
            user_agent=self.user_agent.get().strip(),
            all_internal_links=self.all_internal_links.get(),
            include_start_descendants=self.include_start_descendants.get(),
            include_siblings=self.include_siblings.get(),
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
            _run_crawl,
            kwargs={
                "config": config,
                "output_dir": Path(config.output_path),
                "_log_queue": self.log_queue,
                "_progress_callback": self._on_progress,
            },
            on_success=self._on_success,
            on_error=self._on_error,
            on_finished=self._task_finished,
        )

    def _on_progress(self, done: int, total: int, _url: str) -> None:
        if total > 0:
            pct = min(100.0, (done / total) * 100.0)
            self.after(0, lambda: self.progress_var.set(pct))

    def _on_success(self, result: dict) -> None:
        if not self.project:
            return
        output_path = Path(result["output_path"])
        self.project.record_crawl_run(output_path)
        self.after(0, lambda: self.status_var.set(f"Done — {result['pages']} pages saved"))
        self.after(0, lambda: self.progress_var.set(100.0))
        self.after(0, lambda: self.on_output_created(output_path))

    def _on_error(self, exc: Exception) -> None:
        logger.exception("Crawl failed")
        self.after(0, lambda: self.status_var.set("Failed"))
        self.after(0, lambda: self.log_panel.append(f"Error: {exc}"))


def _run_crawl(
    *,
    config: Tab1Config,
    output_dir: Path,
    cancel_event,
    _progress_callback,
) -> dict:
    def on_progress(done: int, total: int, url: str) -> None:
        _progress_callback(done, total, url)

    pages = crawl_website(config, on_progress=on_progress, cancel_event=cancel_event)
    output_path = versioned_output_path(output_dir, "crawl")
    save_pages(output_path, pages)
    return {"pages": len(pages), "output_path": str(output_path)}
