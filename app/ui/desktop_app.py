import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Any, cast

from app.core.engine import LunaEngine


class LunaDesktopApp:
    def __init__(self, engine: LunaEngine | None = None) -> None:
        self.engine = cast(Any, engine or LunaEngine())
        self.root = tk.Tk()
        self.root.title("LunaAI")
        self.root.geometry("1260x820")
        self.root.minsize(980, 680)
        self.root.configure(bg="#0a0d14")

        self.status_var = tk.StringVar(value="Ready")
        self.is_busy = False
        self.insights_text: tk.Label | None = None
        self.runtime_text: tk.Label | None = None

        self._build_ui()
        self._load_history()
        self._refresh_memory_insights()
        self._refresh_runtime_status()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#0a0d14")
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg="#090b11", width=290)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main = tk.Frame(shell, bg="#11131a")
        main.pack(side="left", fill="both", expand=True)

        brand = tk.Frame(sidebar, bg="#090b11")
        brand.pack(fill="x", padx=20, pady=(20, 14))

        logo_card = tk.Frame(
            brand,
            bg="#0b1018",
            highlightthickness=1,
            highlightbackground="#1b2230",
            padx=16,
            pady=16,
        )
        logo_card.pack(fill="x")

        logo_header = tk.Frame(logo_card, bg="#0b1018")
        logo_header.pack(fill="x")

        logo_mark = tk.Label(
            logo_header,
            text="∞",
            font=("Segoe UI Symbol", 28),
            fg="#f8fafc",
            bg="#0b1018",
        )
        logo_mark.pack(side="left")

        logo_glow = tk.Label(
            logo_header,
            text="/",
            font=("Segoe UI", 24),
            fg="#e5e7eb",
            bg="#0b1018",
        )
        logo_glow.pack(side="left", padx=(2, 0), pady=(0, 6))

        brand_name = tk.Label(
            logo_card,
            text="LunaAI",
            font=("Segoe UI Semibold", 18),
            fg="#f8fafc",
            bg="#0b1018",
        )
        brand_name.pack(anchor="w", pady=(8, 2))

        brand_subtitle = tk.Label(
            logo_card,
            text="Blackbox Interface",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#0b1018",
        )
        brand_subtitle.pack(anchor="w")

        brand_note = tk.Label(
            logo_card,
            text="Styled to match your dark infinity logo. Real image can be dropped in later.",
            wraplength=220,
            justify="left",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#0b1018",
        )
        brand_note.pack(anchor="w", pady=(10, 0))

        action_wrap = tk.Frame(sidebar, bg="#090b11")
        action_wrap.pack(fill="x", padx=20, pady=(6, 12))

        self.new_chat_button = tk.Button(
            action_wrap,
            text="+ New chat",
            command=self.clear_history,
            font=("Segoe UI Semibold", 10),
            bg="#111827",
            fg="#f8fafc",
            activebackground="#1f2937",
            activeforeground="#f8fafc",
            relief="flat",
            padx=14,
            pady=12,
            anchor="w",
        )
        self.new_chat_button.pack(fill="x")

        panel = tk.Frame(
            sidebar,
            bg="#0f1724",
            highlightthickness=1,
            highlightbackground="#1f2a3a",
        )
        panel.pack(fill="x", padx=20, pady=(0, 12))

        panel_title = tk.Label(
            panel,
            text="Workspace",
            font=("Segoe UI Semibold", 10),
            fg="#e2e8f0",
            bg="#0f1724",
        )
        panel_title.pack(anchor="w", padx=14, pady=(14, 6))

        panel_text = tk.Label(
            panel,
            text=(
                "Luna chooses workflow, internet, and reasoning style automatically. "
                "Replies stay on the left, your messages stay on the right."
            ),
            wraplength=220,
            justify="left",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f1724",
        )
        panel_text.pack(anchor="w", padx=14, pady=(0, 14))

        runtime_card = tk.Frame(
            sidebar,
            bg="#0f1724",
            highlightthickness=1,
            highlightbackground="#1f2a3a",
        )
        runtime_card.pack(fill="x", padx=20, pady=(0, 12))

        runtime_title = tk.Label(
            runtime_card,
            text="Runtime Status",
            font=("Segoe UI Semibold", 10),
            fg="#e2e8f0",
            bg="#0f1724",
        )
        runtime_title.pack(anchor="w", padx=14, pady=(14, 6))

        self.runtime_text = tk.Label(
            runtime_card,
            text="",
            wraplength=220,
            justify="left",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f1724",
        )
        self.runtime_text.pack(anchor="w", padx=14, pady=(0, 14))

        insights_card = tk.Frame(
            sidebar,
            bg="#0f1724",
            highlightthickness=1,
            highlightbackground="#1f2a3a",
        )
        insights_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        insights_title = tk.Label(
            insights_card,
            text="Memory Insights",
            font=("Segoe UI Semibold", 10),
            fg="#e2e8f0",
            bg="#0f1724",
        )
        insights_title.pack(anchor="w", padx=14, pady=(14, 6))

        self.insights_text = tk.Label(
            insights_card,
            text="",
            wraplength=220,
            justify="left",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f1724",
        )
        self.insights_text.pack(anchor="nw", fill="both", expand=True, padx=14, pady=(0, 14))

        side_footer = tk.Frame(sidebar, bg="#090b11")
        side_footer.pack(side="bottom", fill="x", padx=20, pady=20)

        side_status = tk.Label(
            side_footer,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#090b11",
            wraplength=240,
            justify="left",
        )
        side_status.pack(anchor="w")

        topbar = tk.Frame(main, bg="#11131a", height=72)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        topbar_inner = tk.Frame(topbar, bg="#11131a")
        topbar_inner.pack(fill="both", expand=True, padx=28)

        top_title = tk.Label(
            topbar_inner,
            text="Luna",
            font=("Segoe UI Semibold", 18),
            fg="#f8fafc",
            bg="#11131a",
        )
        top_title.pack(side="left", pady=18)

        top_hint = tk.Label(
            topbar_inner,
            text="Dark future-facing workspace inspired by modern AI products.",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#11131a",
        )
        top_hint.pack(side="left", padx=(18, 0), pady=20)

        transcript_shell = tk.Frame(main, bg="#11131a")
        transcript_shell.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        transcript_frame = tk.Frame(
            transcript_shell,
            bg="#0d1117",
            highlightthickness=1,
            highlightbackground="#1e2633",
        )
        transcript_frame.pack(fill="both", expand=True)

        self.chat_box = scrolledtext.ScrolledText(
            transcript_frame,
            wrap="word",
            font=("Segoe UI", 11),
            bg="#0d1117",
            fg="#e5e7eb",
            insertbackground="#f8fafc",
            relief="flat",
            padx=26,
            pady=24,
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )
        self.chat_box.pack(fill="both", expand=True)
        self.chat_box.tag_configure("assistant_name", foreground="#7dd3fc", font=("Segoe UI Semibold", 10), justify="left", spacing1=8)
        self.chat_box.tag_configure("assistant", foreground="#e2e8f0", lmargin1=18, lmargin2=18, rmargin=220, spacing3=18, justify="left")
        self.chat_box.tag_configure("user_name", foreground="#c4b5fd", font=("Segoe UI Semibold", 10), justify="right", spacing1=8)
        self.chat_box.tag_configure("user", foreground="#f8fafc", lmargin1=220, lmargin2=220, rmargin=18, spacing3=18, justify="right")
        self.chat_box.tag_configure("system_name", foreground="#fda4af", font=("Segoe UI Semibold", 10), justify="center", spacing1=8)
        self.chat_box.tag_configure("system", foreground="#fecdd3", lmargin1=120, lmargin2=120, rmargin=120, spacing3=18, justify="center")

        composer_shell = tk.Frame(main, bg="#11131a")
        composer_shell.pack(fill="x", padx=22, pady=(0, 22))

        composer = tk.Frame(
            composer_shell,
            bg="#111827",
            highlightthickness=1,
            highlightbackground="#273244",
        )
        composer.pack(fill="x")

        self.input_box = tk.Text(
            composer,
            height=5,
            wrap="word",
            font=("Segoe UI", 11),
            bg="#111827",
            fg="#f8fafc",
            insertbackground="#f8fafc",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=16,
            pady=16,
        )
        self.input_box.pack(fill="x")
        self.input_box.bind("<Return>", self._on_submit)
        self.input_box.bind("<Shift-Return>", self._insert_newline)
        self.input_box.focus_set()

        composer_footer = tk.Frame(composer, bg="#111827")
        composer_footer.pack(fill="x", padx=14, pady=(0, 14))

        helper = tk.Label(
            composer_footer,
            text="Enter to send, Shift+Enter for a new line",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#111827",
        )
        helper.pack(side="left")

        self.send_button = tk.Button(
            composer_footer,
            text="Send",
            command=self.send_message,
            font=("Segoe UI Semibold", 10),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=20,
            pady=9,
        )
        self.send_button.pack(side="right")

    def _load_history(self) -> None:
        history = self.engine.memory.load_history()
        if not history:
            self._append_message(
                "assistant",
                "Luna is ready. Write naturally and it will choose the right style automatically.",
            )
            return

        for item in history:
            role = item.get("role", "assistant")
            content = item.get("content", "")
            if content:
                self._append_message(role, content)

    def _refresh_memory_insights(self) -> None:
        if self.insights_text is None:
            return
        self.insights_text.configure(text=self.engine.get_memory_insights())

    def _refresh_runtime_status(self) -> None:
        if self.runtime_text is None:
            return
        self.runtime_text.configure(text=self.engine.get_runtime_status())

    def _append_message(self, role: str, message: str) -> None:
        tag = role if role in {"user", "assistant", "system"} else "assistant"
        name_tag = f"{tag}_name"
        prefix = {
            "user": "You",
            "assistant": "Luna",
            "system": "System",
        }.get(tag, "Luna")

        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{prefix}\n", name_tag)
        self.chat_box.insert("end", f"{message}\n\n", tag)
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.is_busy = busy
        self.status_var.set(status)
        button_state = "disabled" if busy else "normal"
        text_state = "disabled" if busy else "normal"
        self.input_box.configure(state=text_state)
        self.send_button.configure(state=button_state)
        self.new_chat_button.configure(state=button_state)
        if not busy:
            self.input_box.focus_set()

    def _on_submit(self, _event: tk.Event | None = None) -> str:
        self.send_message()
        return "break"

    def _insert_newline(self, _event: tk.Event | None = None) -> str:
        self.input_box.insert("insert", "\n")
        return "break"

    def send_message(self) -> None:
        if self.is_busy:
            return

        user_text = self.input_box.get("1.0", "end").strip()
        if not user_text:
            return

        self.input_box.delete("1.0", "end")
        self._append_message("user", user_text)
        self._set_busy(True, "Luna is thinking...")

        worker = threading.Thread(
            target=self._generate_response,
            args=(user_text,),
            daemon=True,
        )
        worker.start()

    def _generate_response(self, user_text: str) -> None:
        try:
            response = self.engine.process_message(user_text)
        except Exception as error:
            response = f"Luna: Desktop app error -> {error}"

        self.root.after(0, lambda: self._finish_response(user_text, response))

    def _finish_response(self, user_text: str, response: str) -> None:
        if response:
            tag = "system" if response.startswith("Luna: Mode changed") else "assistant"
            cleaned = response.removeprefix("Luna: ") if response.startswith("Luna: ") else response
            self._append_message(tag, cleaned)
            self._refresh_memory_insights()
            self._refresh_runtime_status()

        if user_text.lower() == "exit":
            self.root.after(250, self.root.destroy)
            return

        self._set_busy(False, "Ready")

    def clear_history(self) -> None:
        if self.is_busy:
            return

        confirmed = messagebox.askyesno(
            "New chat",
            "Start a fresh chat and clear the saved conversation history?",
            parent=self.root,
        )
        if not confirmed:
            return

        self.engine.clear_history()
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
        self._append_message("system", "Started a fresh chat.")
        self._refresh_memory_insights()
        self._refresh_runtime_status()
        self.status_var.set("Fresh chat started")

    def _on_close(self) -> None:
        if self.is_busy:
            if not messagebox.askyesno(
                "Close LunaAI",
                "Luna is still generating a response. Do you want to close the window anyway?",
                parent=self.root,
            ):
                return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
