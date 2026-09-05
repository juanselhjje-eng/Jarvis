from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable


BG = "#05080d"
PANEL = "#0a1119"
PANEL_2 = "#0d1721"
CYAN = "#59e8ff"
CYAN_DIM = "#1a7180"
WHITE = "#dffaff"
MUTED = "#6c8a96"
RED = "#ff5f67"
GREEN = "#72ffb0"


class JarvisHUD:
    """HUD futurista y funcional para el runtime de JARVIS.

    No contiene otro agente: solo presenta el estado del JarvisBrain y expone
    entrada de texto/voz mediante callbacks del runtime principal.
    """

    def __init__(
        self,
        brain,
        voice,
        process_command: Callable[[str], None],
        shutdown: Callable[[], None],
    ) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.running = True
        self.listening = False
        self._last_status = 0.0

        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. — BETA 0.2")
        self.root.geometry("1400x850")
        self.root.minsize(1050, 700)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self._build()
        self._animate()
        self._refresh_status()

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=BG, height=64)
        top.pack(fill="x", padx=28, pady=(20, 0))
        top.pack_propagate(False)

        tk.Label(top, text="J.A.R.V.I.S.", fg=WHITE, bg=BG,
                 font=("Segoe UI", 25, "bold")).pack(side="left")
        tk.Label(top, text="  //  PERSONAL AI SYSTEM", fg=CYAN_DIM, bg=BG,
                 font=("Consolas", 10, "bold")).pack(side="left", pady=(9, 0))

        self.status_label = tk.Label(top, text="● ONLINE", fg=GREEN, bg=BG,
                                     font=("Consolas", 10, "bold"))
        self.status_label.pack(side="right", pady=(9, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=14)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground="#102936")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.canvas = tk.Canvas(left, bg=PANEL, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda _: self._draw_hud())

        self.core_text = self.canvas.create_text(0, 0, text="J.A.R.V.I.S.", fill=WHITE,
                                                 font=("Segoe UI", 19, "bold"))
        self.core_sub = self.canvas.create_text(0, 0, text="SYSTEM READY", fill=CYAN,
                                                font=("Consolas", 9, "bold"))

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)

        header = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground="#102936")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.provider_value = tk.Label(header, text="OLLAMA", fg=CYAN, bg=PANEL,
                                       font=("Consolas", 16, "bold"))
        self.provider_value.pack(side="left", padx=18, pady=14)
        self.model_value = tk.Label(header, text="", fg=MUTED, bg=PANEL,
                                    font=("Consolas", 9))
        self.model_value.pack(side="left", pady=14)

        self.log = scrolledtext.ScrolledText(
            right, bg=PANEL, fg=WHITE, insertbackground=CYAN,
            selectbackground="#173847", relief="flat", borderwidth=0,
            font=("Consolas", 10), wrap="word", padx=14, pady=14,
        )
        self.log.grid(row=1, column=0, sticky="nsew")
        self._log("SYSTEM", "HUD inicializado. Esperando órdenes.")

        bottom = tk.Frame(right, bg=BG)
        bottom.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        bottom.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(bottom, bg=PANEL_2, fg=WHITE, insertbackground=CYAN,
                              relief="flat", font=("Segoe UI", 12))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=12)
        self.entry.bind("<Return>", lambda _: self._send_text())

        self.send_btn = tk.Button(bottom, text="ENVIAR", command=self._send_text,
                                  bg="#102b36", fg=CYAN, activebackground="#173f4d",
                                  activeforeground=WHITE, relief="flat", cursor="hand2",
                                  font=("Consolas", 10, "bold"), padx=18, pady=9)
        self.send_btn.grid(row=0, column=1, padx=(8, 0))

        self.mic_btn = tk.Button(bottom, text="MIC", command=self._toggle_voice,
                                 bg="#102b36", fg=CYAN, activebackground="#173f4d",
                                 activeforeground=WHITE, relief="flat", cursor="hand2",
                                 font=("Consolas", 10, "bold"), padx=18, pady=9)
        self.mic_btn.grid(row=0, column=2, padx=(8, 0))

        self._make_footer(right)

    def _make_footer(self, parent: tk.Frame) -> None:
        footer = tk.Frame(parent, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.grid_columnconfigure((0, 1, 2), weight=1)
        self.cpu = self._metric(footer, "CPU")
        self.cpu.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.ram = self._metric(footer, "RAM")
        self.ram.grid(row=0, column=1, sticky="ew", padx=5)
        self.provider_card = self._metric(footer, "BRAIN")
        self.provider_card.grid(row=0, column=2, sticky="ew", padx=(5, 0))

    def _metric(self, parent: tk.Frame, name: str) -> tk.Label:
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground="#102936")
        label = tk.Label(frame, text=f"{name}\n--", fg=WHITE, bg=PANEL,
                         font=("Consolas", 9), justify="center", pady=9)
        label.pack(fill="both", expand=True)
        frame._metric_label = label  # type: ignore[attr-defined]
        return frame

    def _draw_hud(self) -> None:
        w = max(self.canvas.winfo_width(), 300)
        h = max(self.canvas.winfo_height(), 300)
        cx, cy = w * 0.5, h * 0.48
        self.canvas.coords(self.core_text, cx, cy - 10)
        self.canvas.coords(self.core_sub, cx, cy + 20)

    def _animate(self) -> None:
        if not self.running:
            return
        self._draw_hud()
        self.canvas.delete("ring")
        w = max(self.canvas.winfo_width(), 300)
        h = max(self.canvas.winfo_height(), 300)
        cx, cy = w * 0.5, h * 0.48
        t = time.monotonic()
        pulse = 5 * math.sin(t * 2.4)
        for i, radius in enumerate((115, 155, 195)):
            r = radius + pulse + i * 2
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=CYAN_DIM,
                                    width=1 if i else 2, tags="ring")
        for angle in range(0, 360, 30):
            a = math.radians(angle + t * (18 if angle % 60 == 0 else -10))
            r1, r2 = 202, 214
            self.canvas.create_line(cx + math.cos(a)*r1, cy + math.sin(a)*r1,
                                    cx + math.cos(a)*r2, cy + math.sin(a)*r2,
                                    fill=CYAN, width=2, tags="ring")
        self.root.after(50, self._animate)

    def _refresh_status(self) -> None:
        if not self.running:
            return
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            self.cpu._metric_label.config(text=f"CPU\n{cpu:.0f}%")  # type: ignore[attr-defined]
            self.ram._metric_label.config(text=f"RAM\n{ram:.0f}%")  # type: ignore[attr-defined]
            provider = self.brain.provider.upper()
            model = (self.brain.config.claude_model if provider == "CLAUDE"
                     else self.brain.config.ollama_model)
            self.provider_value.config(text=provider)
            self.model_value.config(text=model)
            self.provider_card._metric_label.config(text=f"BRAIN\n{provider}")  # type: ignore[attr-defined]
        except Exception:
            pass
        self.root.after(1200, self._refresh_status)

    def _log(self, who: str, text: str) -> None:
        self.log.insert("end", f"[{who}] {text}\n\n")
        self.log.see("end")

    def add_message(self, who: str, text: str) -> None:
        self.root.after(0, self._log, who, text)

    def _send_text(self) -> None:
        command = self.entry.get().strip()
        if not command:
            return
        self.entry.delete(0, "end")
        self._log("YOU", command)
        threading.Thread(target=self.process_command, args=(command,), daemon=True).start()

    def _toggle_voice(self) -> None:
        if self.listening:
            return
        self.listening = True
        self.mic_btn.config(text="LISTENING...", fg=WHITE)
        self._log("VOICE", "Escuchando durante 7 segundos...")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.add_message("YOU", command)
                self.process_command(command)
            else:
                self.add_message("VOICE", "No detecté una orden con la palabra de activación.")
        except Exception as exc:
            self.add_message("VOICE", f"Error: {exc}")
        finally:
            self.root.after(0, self._voice_idle)

    def _voice_idle(self) -> None:
        self.listening = False
        self.mic_btn.config(text="MIC", fg=CYAN)

    def set_response(self, text: str) -> None:
        self.add_message("JARVIS", text)

    def _close(self) -> None:
        self.running = False
        self.shutdown_callback()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()
