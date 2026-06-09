"""Reusable Tkinter widgets."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk


class LabeledCombobox(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        label: str,
        *,
        textvariable: tk.StringVar,
        values: list[str] | tuple[str, ...],
        label_width: int = 16,
    ) -> None:
        super().__init__(master)
        ttk.Label(self, text=label, width=label_width).pack(side=tk.LEFT, padx=(0, 8))
        self.combobox = ttk.Combobox(
            self,
            textvariable=textvariable,
            values=list(values),
            state="readonly",
        )
        self.combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set_values(self, values: list[str]) -> None:
        self.combobox.configure(values=values)


class ProjectPicker(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        textvariable: tk.StringVar,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        ttk.Label(self, text="Project folder", width=16).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(self, textvariable=textvariable).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(self, text="Browse…", command=self._browse).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.textvariable = textvariable
        if on_change:
            textvariable.trace_add("write", lambda *_: on_change())

    def _browse(self) -> None:
        from pathlib import Path

        initial = Path(self.textvariable.get() or ".").expanduser()
        parent = str(initial.parent if initial.exists() else initial)
        selected = filedialog.askdirectory(
            title="Select website_to_chroma project folder",
            initialdir=parent,
        )
        if selected:
            self.textvariable.set(selected)
