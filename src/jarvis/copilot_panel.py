from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Callable


BG = "#06090c"
PANEL = "#0b1015"
LINE = "#1c2a31"
CYAN = "#13dbe7"
WHITE = "#edf3f5"
MUTED = "#71808a"
GREEN = "#3fe3a0"


class CopilotPanel:
    """Panel flotante local inspirado en el concepto de Copiloto.

    Es una sola interfaz para el mismo cerebro de JARVIS; no crea otro agente.
    """

    def __init__(self, parent, process_command: Callable[[str], None]):
        self.parent = parent
        self.process_command = process_command
        self.window: tk.Toplevel | None = None
        self.history: list[str] = []

    def toggle(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
            self.window = None
            return
        self.open()

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("JARVIS — Copilot")
        self.window.configure(bg=BG)
        self.window.geometry("390x520+40+120")
        self.window.minsize(340, 430)
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

        top = tk.Frame(self.window, bg="#080c10", height=52, highlightthickness=1, highlightbackground=LINE)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="◉  JARVIS COPILOT", bg=top["bg"], fg=WHITE, font=("Segoe UI", 10, "bold")).pack(side="left", padx=14)
        tk.Label(top, text="ONLINE", bg=top["bg"], fg=GREEN, font=("Segoe UI", 8, "bold")).pack(side="right", padx=14)

        context = tk.Frame(self.window, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        context.pack(fill="x", padx=10, pady=10)
        tk.Label(context, text="CONTEXTO", bg=PANEL, fg=CYAN, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(context, text="Mismo cerebro · memoria local · Mission Control", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(0, 9))

        self.feed = tk.Text(self.window, bg="#05080b", fg=MUTED, relief="flat", bd=0, font=("Consolas", 8), wrap="word", state="disabled")
        self.feed.pack(fill="both", expand=True, padx=10)

        bottom = tk.Frame(self.window, bg=BG)
        bottom.pack(fill="x", padx=10, pady=10)
        self.entry = tk.Entry(bottom, bg="#11171c", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 9))
        self.entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.entry.bind("<Return>", lambda _e: self.send())
        tk.Button(bottom, text="→", command=self.send, bg="#102329", fg=CYAN, activebackground="#15343b", activeforeground=WHITE, relief="flat", bd=0, font=("Segoe UI", 10, "bold"), width=4).pack(side="left", padx=(5, 0), ipady=5)

        self._write("JARVIS", "Copiloto activo. Puedes seguir trabajando en otra ventana.")
        self.entry.focus_set()

    def send(self) -> None:
        if not self.window or not self.window.winfo_exists():
            return
        command = self.entry.get().strip()
        if not command:
            return
        self.entry.delete(0, "end")
        self._write("TÚ", command)
        self.history.append(command)
        self.process_command(command)

    def show_result(self, text: str) -> None:
        if self.window and self.window.winfo_exists():
            self._write("JARVIS", text)

    def _write(self, speaker: str, text: str) -> None:
        if not self.feed or not self.feed.winfo_exists():
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.feed.configure(state="normal")
        self.feed.insert("end", f"[{timestamp}] {speaker}\n{text}\n\n")
        self.feed.see("end")
        self.feed.configure(state="disabled")
