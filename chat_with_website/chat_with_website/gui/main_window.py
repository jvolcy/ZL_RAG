"""Main chat application window."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from chat_with_website.config import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_PROJECT_PATH,
    DEFAULT_TOP_K,
    EMBEDDING_MODEL_CHOICES,
    Config,
)
from chat_with_website.conversation import ConversationMemory
from chat_with_website.gui.project_settings import (
    embedding_choices,
    ollama_choices,
    read_project_settings,
)
from chat_with_website.gui.task_runner import TaskRunner
from chat_with_website.gui.widgets import LabeledCombobox, ProjectPicker
from chat_with_website.handler import ChatResponse, process_question
from chat_with_website.startup import AppContext, initialize

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    def __init__(self, initial_config: Config | None = None) -> None:
        super().__init__()
        self.title("Website Knowledge Assistant")
        self.minsize(760, 620)
        self.geometry("900x720")

        self._initial_config = initial_config
        self._ctx: AppContext | None = None
        self._memory = ConversationMemory()
        self._init_runner = TaskRunner()
        self._query_runner = TaskRunner()
        self._session_active = False

        self.project_path = tk.StringVar(value=str(DEFAULT_PROJECT_PATH))
        self.embedding_model = tk.StringVar(value=EMBEDDING_MODEL_CHOICES[0])
        self.ollama_model = tk.StringVar(value=DEFAULT_OLLAMA_MODEL)
        self.top_k = tk.IntVar(value=DEFAULT_TOP_K)
        self.collection_name = tk.StringVar(value="website")
        self.chroma_path = tk.StringVar()
        self.ollama_host = tk.StringVar(value=DEFAULT_OLLAMA_HOST)
        self.status_text = tk.StringVar(value="Configure settings and start a session.")

        self._embedding_combo: LabeledCombobox | None = None
        self._ollama_combo: LabeledCombobox | None = None
        self._chat_log: scrolledtext.ScrolledText | None = None
        self._input_text: tk.Text | None = None
        self._start_button: ttk.Button | None = None
        self._send_button: ttk.Button | None = None
        self._clear_button: ttk.Button | None = None
        self._top_k_spinbox: ttk.Spinbox | None = None
        self._project_picker: ProjectPicker | None = None

        self._build_menu()
        self._build_ui()
        self._configure_chat_tags()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if initial_config is not None:
            self._apply_config(initial_config)
            self.after(100, self._start_session)
        else:
            self._load_project_defaults()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New Session", command=self._end_session)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        settings = ttk.LabelFrame(outer, text="Settings", padding=10)
        settings.pack(fill=tk.X, pady=(0, 10))

        self._project_picker = ProjectPicker(
            settings,
            textvariable=self.project_path,
            on_change=self._load_project_defaults,
        )
        self._project_picker.pack(fill=tk.X, pady=3)

        row = ttk.Frame(settings)
        row.pack(fill=tk.X, pady=3)
        row.columnconfigure(1, weight=1)
        row.columnconfigure(3, weight=1)

        self._embedding_combo = LabeledCombobox(
            row,
            "Embedding model",
            textvariable=self.embedding_model,
            values=EMBEDDING_MODEL_CHOICES,
        )
        self._embedding_combo.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=(0, 12))

        self._ollama_combo = LabeledCombobox(
            row,
            "Ollama model",
            textvariable=self.ollama_model,
            values=[DEFAULT_OLLAMA_MODEL],
        )
        self._ollama_combo.grid(row=0, column=2, columnspan=2, sticky=tk.EW)

        controls = ttk.Frame(settings)
        controls.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(controls, text="Top K", width=16).pack(side=tk.LEFT, padx=(0, 8))
        self._top_k_spinbox = ttk.Spinbox(
            controls,
            from_=1,
            to=50,
            textvariable=self.top_k,
            width=6,
        )
        self._top_k_spinbox.pack(side=tk.LEFT)
        self._start_button = ttk.Button(
            controls,
            text="Start Session",
            command=self._start_session,
        )
        self._start_button.pack(side=tk.RIGHT)

        chat_frame = ttk.LabelFrame(outer, text="Conversation", padding=8)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self._chat_log = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=20,
            font=("", 10),
        )
        self._chat_log.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.Frame(outer)
        input_frame.pack(fill=tk.X, pady=(10, 0))

        self._input_text = tk.Text(input_frame, height=3, wrap=tk.WORD, font=("", 10))
        self._input_text.pack(fill=tk.X, expand=True)
        self._input_text.bind("<Return>", self._on_input_return)
        self._input_text.bind("<Shift-Return>", lambda _event: None)

        button_row = ttk.Frame(outer)
        button_row.pack(fill=tk.X, pady=(8, 0))

        self._send_button = ttk.Button(
            button_row,
            text="Send",
            command=self._send_message,
            state=tk.DISABLED,
        )
        self._send_button.pack(side=tk.RIGHT)

        self._clear_button = ttk.Button(
            button_row,
            text="Clear Conversation",
            command=self._clear_conversation,
            state=tk.DISABLED,
        )
        self._clear_button.pack(side=tk.RIGHT, padx=(0, 8))

        ttk.Label(button_row, textvariable=self.status_text).pack(side=tk.LEFT)

        self._append_system(
            "Welcome. Choose your project and models, then click Start Session."
        )

    def _configure_chat_tags(self) -> None:
        if not self._chat_log:
            return
        self._chat_log.tag_configure("user", foreground="#1a5276", spacing1=8)
        self._chat_log.tag_configure("assistant", foreground="#1e1e1e", spacing1=8)
        self._chat_log.tag_configure("sources", foreground="#555555", lmargin1=16, lmargin2=16)
        self._chat_log.tag_configure("error", foreground="#b00020", spacing1=8)
        self._chat_log.tag_configure("system", foreground="#666666", spacing1=6)

    def _apply_config(self, config: Config) -> None:
        self.chroma_path.set(config.chroma_path)
        self.collection_name.set(config.collection_name)
        self.embedding_model.set(config.embedding_model)
        self.ollama_model.set(config.ollama_model)
        self.top_k.set(config.top_k)
        self.ollama_host.set(config.ollama_host)
        if self._embedding_combo:
            self._embedding_combo.set_values(embedding_choices(config.embedding_model))
        if self._ollama_combo:
            self._ollama_combo.set_values(
                ollama_choices(config.ollama_host, config.ollama_model)
            )

    def _load_project_defaults(self) -> None:
        settings = read_project_settings(self.project_path.get())
        if settings.get("embedding_model"):
            self.embedding_model.set(settings["embedding_model"])
        if settings.get("collection_name"):
            self.collection_name.set(settings["collection_name"])
        if settings.get("chroma_path"):
            self.chroma_path.set(settings["chroma_path"])

        if self._embedding_combo:
            self._embedding_combo.set_values(
                embedding_choices(self.embedding_model.get())
            )
        if self._ollama_combo:
            values = ollama_choices(self.ollama_host.get(), self.ollama_model.get())
            self._ollama_combo.set_values(values)
            if self.ollama_model.get() not in values and values:
                preferred = DEFAULT_OLLAMA_MODEL
                self.ollama_model.set(
                    preferred if preferred in values else values[0]
                )

    def _build_config(self) -> Config:
        return Config(
            chroma_path=self.chroma_path.get().strip(),
            collection_name=self.collection_name.get().strip(),
            embedding_model=self.embedding_model.get().strip(),
            top_k=self.top_k.get(),
            ollama_host=self.ollama_host.get().strip(),
            ollama_model=self.ollama_model.get().strip(),
        )

    def _set_settings_enabled(self, enabled: bool) -> None:
        combo_state = "readonly" if enabled else tk.DISABLED
        entry_state = tk.NORMAL if enabled else tk.DISABLED

        if self._project_picker:
            for child in self._project_picker.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Button)):
                    child.configure(state=entry_state)
        if self._embedding_combo:
            self._embedding_combo.combobox.configure(state=combo_state)
        if self._ollama_combo:
            self._ollama_combo.combobox.configure(state=combo_state)
        if self._top_k_spinbox:
            self._top_k_spinbox.configure(state=entry_state)
        if self._start_button:
            self._start_button.configure(state=entry_state)

    def _set_chat_enabled(self, enabled: bool) -> None:
        send_state = tk.NORMAL if enabled else tk.DISABLED
        if self._send_button:
            self._send_button.configure(state=send_state)
        if self._clear_button:
            self._clear_button.configure(state=send_state)
        if self._input_text:
            self._input_text.configure(state=send_state)

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self._set_settings_enabled(False)
            self._set_chat_enabled(False)
        elif self._session_active:
            self._set_settings_enabled(False)
            if self._start_button:
                self._start_button.configure(state=tk.NORMAL)
            self._set_chat_enabled(True)
        else:
            self._set_settings_enabled(True)
            self._set_chat_enabled(False)

    def _clear_chat_log(self) -> None:
        if not self._chat_log:
            return
        self._chat_log.configure(state=tk.NORMAL)
        self._chat_log.delete("1.0", tk.END)
        self._chat_log.configure(state=tk.DISABLED)

    def _append_chat(self, text: str, tag: str) -> None:
        if not self._chat_log:
            return
        self._chat_log.configure(state=tk.NORMAL)
        self._chat_log.insert(tk.END, text, tag)
        self._chat_log.configure(state=tk.DISABLED)
        self._chat_log.see(tk.END)

    def _append_system(self, text: str) -> None:
        self._append_chat(f"{text}\n\n", "system")

    def _start_session(self) -> None:
        if self._init_runner.is_running or self._query_runner.is_running:
            return

        if self._session_active:
            self._ctx = None
            self._session_active = False
            self._memory.clear()
            self._clear_chat_log()
            if self._start_button:
                self._start_button.configure(text="Start Session")

        try:
            config = self._build_config()
            config.validate()
        except ValueError as exc:
            messagebox.showerror("Configuration error", str(exc))
            return

        self.status_text.set("Starting session… loading models and verifying connections.")
        self._set_busy(True)

        def on_success(ctx: AppContext) -> None:
            self._ctx = ctx
            self._memory = ConversationMemory(
                max_turns=ctx.config.max_history_turns,
                enabled=ctx.config.memory_enabled,
            )
            self._session_active = True
            self._append_system(
                f"Session started — {ctx.retriever.document_count} indexed chunks, "
                f"model {ctx.config.ollama_model}."
            )
            self.status_text.set("Ready. Ask a question about the indexed website.")
            if self._start_button:
                self._start_button.configure(text="Restart Session")

        def on_error(exc: Exception) -> None:
            messagebox.showerror("Startup failed", str(exc))
            self.status_text.set("Startup failed. Adjust settings and try again.")

        def on_finished() -> None:
            self._set_busy(False)

        self._init_runner.run(
            target=initialize,
            kwargs={"config": config},
            on_success=on_success,
            on_error=on_error,
            on_finished=on_finished,
        )

    def _end_session(self) -> None:
        if self._init_runner.is_running or self._query_runner.is_running:
            messagebox.showwarning("Busy", "Wait for the current operation to finish.")
            return
        self._ctx = None
        self._session_active = False
        self._memory.clear()
        self._clear_chat_log()
        if self._start_button:
            self._start_button.configure(text="Start Session")
        self._set_settings_enabled(True)
        self._set_chat_enabled(False)
        self.status_text.set("Session ended. Update settings and start again.")
        self._append_system("Session ended.")

    def _clear_conversation(self) -> None:
        self._memory.clear()
        self._append_system("Conversation cleared.")

    def _on_input_return(self, event: tk.Event) -> str:
        if event.state & 0x1:
            return ""
        self._send_message()
        return "break"

    def _send_message(self) -> None:
        if not self._ctx or not self._input_text or self._query_runner.is_running:
            return

        question = self._input_text.get("1.0", tk.END).strip()
        if not question:
            return

        self._input_text.delete("1.0", tk.END)
        self._append_chat(f"You: {question}\n\n", "user")
        self.status_text.set("Retrieving context and generating answer…")
        self._set_busy(True)

        ctx = self._ctx
        memory = self._memory

        def on_success(result: ChatResponse) -> None:
            if result.error:
                self._append_chat(f"Error: {result.error}\n\n", "error")
                self.status_text.set("An error occurred. You can try again.")
                return

            self._append_chat(f"Assistant: {result.answer}\n", "assistant")
            if result.source_urls:
                sources = "\n".join(f"  • {url}" for url in result.source_urls)
                self._append_chat(f"Sources:\n{sources}\n\n", "sources")
            else:
                self._append_chat("\n", "assistant")
            self.status_text.set("Ready.")

        def on_error(exc: Exception) -> None:
            logger.exception("Question handling failed")
            self._append_chat(f"Error: {exc}\n\n", "error")
            self.status_text.set("An error occurred. You can try again.")

        def on_finished() -> None:
            self._set_busy(False)

        self._query_runner.run(
            target=process_question,
            kwargs={"ctx": ctx, "question": question, "memory": memory},
            on_success=on_success,
            on_error=on_error,
            on_finished=on_finished,
        )

    def _on_close(self) -> None:
        if self._init_runner.is_running or self._query_runner.is_running:
            if not messagebox.askyesno(
                "Exit",
                "A request is still running. Exit anyway?",
            ):
                return
        self.destroy()
