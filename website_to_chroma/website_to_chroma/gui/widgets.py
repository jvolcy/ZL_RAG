"""Reusable Tkinter widgets for pipeline tabs."""

from __future__ import annotations

import queue
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, ttk

from website_to_chroma.gui.task_runner import TaskRunner
from website_to_chroma.project import utc_now


class LabeledEntry(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        label: str,
        *,
        textvariable: tk.StringVar | tk.IntVar | tk.DoubleVar | tk.BooleanVar,
        width: int = 50,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        ttk.Label(self, text=label, width=22).pack(side=tk.LEFT, padx=(0, 8))
        if isinstance(textvariable, tk.BooleanVar):
            ttk.Checkbutton(self, variable=textvariable, command=on_change).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )
        else:
            entry = ttk.Entry(self, textvariable=textvariable, width=width)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if on_change:
                textvariable.trace_add("write", lambda *_: on_change())


class LabeledCombobox(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        label: str,
        *,
        textvariable: tk.StringVar,
        values: list[str] | tuple[str, ...],
        width: int = 47,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        ttk.Label(self, text=label, width=22).pack(side=tk.LEFT, padx=(0, 8))
        self.combobox = ttk.Combobox(
            self,
            textvariable=textvariable,
            values=list(values),
            width=width,
            state="readonly",
        )
        self.combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if on_change:
            self.combobox.bind("<<ComboboxSelected>>", lambda _event: on_change())

    def set_values(self, values: list[str]) -> None:
        self.combobox.configure(values=values)


class FilePickerRow(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        label: str,
        *,
        textvariable: tk.StringVar,
        pick_type: str = "file",
        filetypes: list[tuple[str, str]] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.textvariable = textvariable
        self.pick_type = pick_type
        self.filetypes = filetypes or [("JSON Lines", "*.jsonl"), ("All files", "*.*")]
        self.on_change = on_change

        ttk.Label(self, text=label, width=22).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(self, textvariable=textvariable, width=50).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(self, text="Browse…", command=self._browse).pack(side=tk.LEFT, padx=(8, 0))
        if on_change:
            textvariable.trace_add("write", lambda *_: on_change())

    def _browse(self) -> None:
        path: str | None
        if self.pick_type == "directory":
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=self.filetypes)
        if path:
            self.textvariable.set(path)
            if self.on_change:
                self.on_change()


class ScrollableLog(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.text = tk.Text(self, height=12, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def append(self, message: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, message + "\n")
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def clear(self) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)


class PipelineTab(ttk.Frame):
    """Base class for a pipeline stage tab."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.project = None
        self.task_runner = TaskRunner()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self._poll_id: str | None = None
        self._save_after_id: str | None = None

        self.warning_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_common_ui()

    def _build_common_ui(self) -> None:
        ttk.Label(self, textvariable=self.warning_var, foreground="#a66a00").pack(
            fill=tk.X, padx=8, pady=(8, 0)
        )

        self.config_frame = ttk.LabelFrame(self, text="Configuration", padding=8)
        self.config_frame.pack(fill=tk.X, padx=8, pady=8)

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=8)
        self.run_button = ttk.Button(controls, text="Run", command=self._on_run)
        self.run_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            controls, text="Cancel", command=self._on_cancel, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(controls, textvariable=self.status_var).pack(side=tk.LEFT, padx=(16, 0))

        self.progress = ttk.Progressbar(
            self, variable=self.progress_var, maximum=100, mode="determinate"
        )
        self.progress.pack(fill=tk.X, padx=8, pady=(8, 0))

        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.log_panel = ScrollableLog(log_frame)
        self.log_panel.pack(fill=tk.BOTH, expand=True)

    def set_project(self, project) -> None:
        self.project = project
        self.load_config()
        self.update_staleness_warning()

    def load_config(self) -> None:
        raise NotImplementedError

    def save_config(self) -> None:
        raise NotImplementedError

    def update_staleness_warning(self) -> None:
        self.warning_var.set("")

    def _on_run(self) -> None:
        if self.task_runner.is_running:
            return
        self.log_panel.clear()
        self.progress_var.set(0.0)
        self.status_var.set("Running…")
        self.run_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self._start_polling()
        self.start_task()

    def _on_cancel(self) -> None:
        self.task_runner.cancel()
        self.status_var.set("Cancelling…")

    def _start_polling(self) -> None:
        self._poll_logs_and_progress()

    def _poll_logs_and_progress(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_panel.append(message)
            except queue.Empty:
                break
        if self.task_runner.is_running:
            self._poll_id = self.after(200, self._poll_logs_and_progress)

    def _task_finished(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_panel.append(message)
            except queue.Empty:
                break
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None

    def start_task(self) -> None:
        raise NotImplementedError

    def _schedule_save(self) -> None:
        if self._save_after_id:
            self.after_cancel(self._save_after_id)
        self._save_after_id = self.after(400, self._do_save)

    def _do_save(self) -> None:
        if self.project:
            self.save_config()


def versioned_output_path(directory: Path, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%S")
    return directory / f"{prefix}_{stamp}.jsonl"
