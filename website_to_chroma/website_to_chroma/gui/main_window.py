"""Main application window with project management and tabbed pipeline."""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from website_to_chroma.gui.tab_chunk import ChunkTab
from website_to_chroma.gui.tab_crawl import CrawlTab
from website_to_chroma.gui.tab_embed import EmbedTab
from website_to_chroma.project import Project

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Website Knowledge Base Indexer")
        self.geometry("920x720")
        self.minsize(800, 600)

        self.project: Project | None = None
        self._build_menu()
        self._build_header()
        self._build_tabs()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._prompt_initial_project)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project…", command=self._new_project)
        file_menu.add_command(label="Open Project…", command=self._open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Project:").pack(side=tk.LEFT)
        self.project_label = ttk.Label(header, text="(none)")
        self.project_label.pack(side=tk.LEFT, padx=(8, 0))

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.crawl_tab = CrawlTab(
            self.notebook,
            on_output_created=self._on_crawl_output,
        )
        self.chunk_tab = ChunkTab(
            self.notebook,
            on_output_created=self._on_chunk_output,
        )
        self.embed_tab = EmbedTab(self.notebook)

        self.notebook.add(self.crawl_tab, text="1. Crawl & HTML")
        self.notebook.add(self.chunk_tab, text="2. Chunking")
        self.notebook.add(self.embed_tab, text="3. Embed & Store")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _prompt_initial_project(self) -> None:
        if self.project:
            return
        if messagebox.askyesno(
            "Open Project",
            "No project is open. Create a new project now?\n\n"
            "Choose No to open an existing project directory.",
        ):
            self._new_project()
        else:
            self._open_project()

    def _new_project(self) -> None:
        directory = filedialog.askdirectory(
            title="Choose parent directory for the new project",
        )
        if not directory:
            return
        name = simpledialog.askstring(
            "Project Name",
            "Enter a project name.\nA subdirectory with this name will be created.",
            initialvalue="my_project",
        )
        if not name:
            return
        try:
            self.project = Project.create(Path(directory), name)
            self._apply_project()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not create project:\n{exc}")

    def _open_project(self) -> None:
        directory = filedialog.askdirectory(
            title="Open project directory (folder containing project.json)",
        )
        if not directory:
            return
        try:
            self.project = Project.open(Path(directory))
            self._apply_project()
        except FileNotFoundError:
            if messagebox.askyesno(
                "Initialize Project",
                f"No project manifest found in:\n{directory}\n\n"
                "Create a new project subdirectory here?",
            ):
                name = simpledialog.askstring(
                    "Project Name",
                    "Enter a project name.\nA subdirectory with this name will be created.",
                    initialvalue="my_project",
                )
                if name:
                    self.project = Project.create(Path(directory), name)
                    self._apply_project()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open project:\n{exc}")

    def _apply_project(self) -> None:
        if not self.project:
            return
        self.project_label.configure(text=f"{self.project.manifest.name} — {self.project.root}")
        self.crawl_tab.set_project(self.project)
        self.chunk_tab.set_project(self.project)
        self.embed_tab.set_project(self.project)

    def _on_crawl_output(self, path: Path) -> None:
        self.chunk_tab.set_default_input(path)

    def _on_chunk_output(self, path: Path) -> None:
        self.embed_tab.set_default_input(path)

    def _on_tab_changed(self, _event=None) -> None:
        selected = self.notebook.index(self.notebook.select())
        if selected == 1:
            self.chunk_tab.update_staleness_warning()
        elif selected == 2:
            self.embed_tab.update_staleness_warning()

    def _on_close(self) -> None:
        for tab in (self.crawl_tab, self.chunk_tab, self.embed_tab):
            if tab.task_runner.is_running:
                if not messagebox.askyesno(
                    "Task Running",
                    "A task is still running. Exit anyway?",
                ):
                    return
                tab.task_runner.cancel()
            tab.save_config()
        self.destroy()
