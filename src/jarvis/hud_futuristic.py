from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None


# Visual language inspired by premium sci-fi control rooms without copying proprietary assets.
BG = "#030509"
SURFACE = "#070c12"
SURFACE_2 = "#0b121a"
LINE = "#14232d"
CYAN = "#64e9ff"
CYAN_DIM = "#1b7183"
WHITE = "#eaf9fc"
MUTED = "#71838b"
GREEN = "#67f5b1"
AMBER = "#ffd166"
RED = "#ff6b7a"


class JarvisHUD:
    """HUD de Mission Control: elegante, oscuro, modular y centrado en conversación/evidencias."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.running = True
        self.started = time.monotonic()
        self.activity = "CALMADO"
        self._build_window()
        self._build()
        self._render()
        self._tick()

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("JARVIS // MISSION CONTROL")
        self.root.configure(bg=BG)
        self.root.minsize(1280, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")

    def _build(self) -> None:
        # Header
        header = tk.Frame(self.root, bg=BG, height=74)
        header.pack(fill="x", padx=28, pady=(18, 0))
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left", fill="y")
        tk.Label(brand, text="JARVIS", fg=WHITE, bg=BG, font=("Segoe UI", 25, "bold")).pack(side="left", pady=5)
        tk.Label(brand, text="  MARK // LOCAL", fg=CYAN_DIM, bg=BG, font=("Consolas", 9, "bold")).pack(side="left", pady=(13, 0))

        status = tk.Frame(header, bg=BG)
        status.pack(side="right", fill="y")
        self.online = tk.Label(status, text="●  OPERATIVO", fg=GREEN, bg=BG, font=("Consolas", 9, "bold"))
        self.online.pack(anchor="e", pady=(6, 0))
        self.status_text = tk.Label(status, text="CEREBRO LOCAL  •  ACCIONES VERIFICADAS", fg=MUTED, bg=BG, font=("Consolas", 7))
        self.status_text.pack(anchor="e", pady=(3, 0))

        # Main grid
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=(2, 24))
        main.grid_columnconfigure(0, weight=7)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        self._build_chat(main)
        self._build_control(main)

    def _card(self, parent, **kwargs):
        return tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, **kwargs)

    def _section_title(self, parent, title: str, right: str = "") -> tk.Frame:
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(row, text=title, fg=CYAN, bg=SURFACE, font=("Consolas", 8, "bold")).pack(side="left")
        if right:
            tk.Label(row, text=right, fg=MUTED, bg=SURFACE, font=("Consolas", 7)).pack(side="right")
        return row

    def _build_chat(self, parent) -> None:
        left = self._card(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        self._section_title(left, "JARVIS", "CONVERSACIÓN PRIVADA")

        self.log = scrolledtext.ScrolledText(
            left,
            bg=SURFACE,
            fg=WHITE,
            insertbackground=CYAN,
            selectbackground="#16313a",
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            wrap="word",
            padx=22,
            pady=14,
            spacing1=4,
            spacing3=9,
        )
        self.log.grid(row=1, column=0, sticky="nsew", padx=8)
        self.log.tag_configure("system", foreground=MUTED, font=("Consolas", 8))
        self.log.tag_configure("user", foreground=CYAN, font=("Segoe UI", 10, "bold"))
        self.log.tag_configure("jarvis", foreground=WHITE, font=("Segoe UI", 10))
        self.log.tag_configure("voice", foreground=AMBER, font=("Consolas", 8))
        self._log("SYSTEM", "Mission Control iniciado. Sistemas listos.")

        compose = tk.Frame(left, bg=SURFACE)
        compose.grid(row=2, column=0, sticky="ew", padx=18, pady=(4, 18))
        compose.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(
            compose,
            bg=SURFACE_2,
            fg=WHITE,
            insertbackground=CYAN,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.entry.grid(row=0, column=0, sticky="ew", ipady=13)
        self.entry.insert(0, "Escríbame aquí, señor…")
        self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", lambda _: self._send())

        self._button(compose, "ENVIAR", self._send, primary=True).grid(row=0, column=1, padx=(8, 0))
        self.mic = self._button(compose, "◉", self._voice)
        self.mic.grid(row=0, column=2, padx=(6, 0))

        footer = tk.Frame(left, bg=SURFACE)
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        tk.Label(footer, text="DOCUMENTO", fg=MUTED, bg=SURFACE, font=("Consolas", 7)).pack(side="left")
        tk.Label(footer, text="INFORME", fg=MUTED, bg=SURFACE, font=("Consolas", 7)).pack(side="left", padx=24)
        self.state_badge = tk.Label(footer, text="● CALMADO", fg=GREEN, bg=SURFACE, font=("Consolas", 8, "bold"))
        self.state_badge.pack(side="right")

    def _build_control(self, parent) -> None:
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        core = self._card(right)
        core.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._section_title(core, "NÚCLEO DE INTELIGENCIA", "NEURAL CORE")
        self.provider_label = tk.Label(core, text=self.brain.provider.upper(), fg=WHITE, bg=SURFACE, font=("Segoe UI", 18, "bold"))
        self.provider_label.pack(anchor="w", padx=18)
        self.model_label = tk.Label(core, text="", fg=CYAN_DIM, bg=SURFACE, font=("Consolas", 7))
        self.model_label.pack(anchor="w", padx=18, pady=(2, 14))

        # Small reactor gives the HUD a polished centerpiece without becoming a toy dashboard.
        reactor = tk.Frame(core, bg=SURFACE, height=190)
        reactor.pack(fill="x", padx=10, pady=(0, 10))
        reactor.pack_propagate(False)
        self.core_canvas = tk.Canvas(reactor, bg=SURFACE, highlightthickness=0)
        self.core_canvas.pack(fill="both", expand=True)

        mission = self._card(right)
        mission.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._section_title(mission, "ESTADO DE MISIÓN")
        self.task_label = tk.Label(mission, text="CALMADO / ESPERANDO OBJETIVO", fg=WHITE, bg=SURFACE, font=("Segoe UI", 10, "bold"), wraplength=330, justify="left")
        self.task_label.pack(anchor="w", padx=18)
        self.phase_label = tk.Label(mission, text="FASE 01  /  LISTO", fg=GREEN, bg=SURFACE, font=("Consolas", 8, "bold"))
        self.phase_label.pack(anchor="w", padx=18, pady=(5, 14))

        evidence = self._card(right)
        evidence.grid(row=2, column=0, sticky="nsew")
        self._section_title(evidence, "TABLERO DE EVIDENCIAS", "RESEARCH / FILES")
        self.evidence_title = tk.Label(evidence, text="Tablero en espera.", fg=WHITE, bg=SURFACE, font=("Segoe UI", 10, "bold"), wraplength=330, justify="left")
        self.evidence_title.pack(anchor="w", padx=18)
        self.evidence_status = tk.Label(evidence, text="STATUS  /  IDLE", fg=MUTED, bg=SURFACE, font=("Consolas", 8))
        self.evidence_status.pack(anchor="w", padx=18, pady=(5, 4))
        self.evidence_findings = tk.Label(evidence, text="Findings: 0    Sources: 0", fg=WHITE, bg=SURFACE, font=("Consolas", 8))
        self.evidence_findings.pack(anchor="w", padx=18, pady=(0, 16))

        telemetry = tk.Frame(evidence, bg=SURFACE)
        telemetry.pack(fill="x", padx=14, pady=(0, 14))
        for i in range(3):
            telemetry.grid_columnconfigure(i, weight=1)
        self.metrics: list[tk.Label] = []
        for i, name in enumerate(("CPU", "RAM", "UPTIME")):
            box = tk.Frame(telemetry, bg=SURFACE_2, highlightthickness=1, highlightbackground=LINE)
            box.grid(row=0, column=i, sticky="ew", padx=2)
            label = tk.Label(box, text=f"{name}\n--", fg=WHITE, bg=SURFACE_2, font=("Consolas", 8, "bold"), pady=8)
            label.pack(fill="both")
            self.metrics.append(label)

        tk.Label(
            evidence,
            text="CÁMARA  ·  APAGADA    •    WHISPER LOCAL    •    OLLAMA / CLAUDE",
            fg="#42545c",
            bg=SURFACE,
            font=("Consolas", 7),
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def _button(self, parent, text: str, command, primary: bool = False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#0d2c35" if primary else SURFACE_2,
            fg=CYAN if primary else WHITE,
            activebackground="#16424d",
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Consolas", 8, "bold"),
            padx=15,
            pady=9,
        )

    def _clear_placeholder(self, _event=None) -> None:
        if self.entry.get() == "Escríbame aquí, señor…":
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text or text == "Escríbame aquí, señor…":
            return
        self.entry.delete(0, "end")
        self.entry.config(fg=WHITE)
        self._log("USER", text)
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _voice(self) -> None:
        self._log("VOICE", "Escuchando…")
        self.set_state("ESCUCHANDO")
        threading.Thread(target=self._voice_worker, daemon=True, name="jarvis-manual-voice").start()

    def _voice_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.root.after(0, lambda: self._log("USER", command))
                self.process_command(command)
            else:
                self.root.after(0, lambda: self.set_state("CALMADO"))
        except Exception as exc:
            self.root.after(0, lambda: self._log("VOICE", f"Error: {exc}"))
            self.root.after(0, lambda: self.set_state("CALMADO"))

    def set_state(self, state: str) -> None:
        def update() -> None:
            if not self.running:
                return
            self.activity = state.upper()
            colors = {"CALMADO": GREEN, "ESCUCHANDO": AMBER, "HABLANDO": CYAN, "PROCESANDO": CYAN, "PROCESSING COMMAND": CYAN, "THINKING": CYAN}
            color = colors.get(self.activity, CYAN)
            self.state_badge.config(text=f"● {self.activity}", fg=color)
            self.status_text.config(text=f"{self.brain.provider.upper()}  •  {self.activity}  •  ACCIONES VERIFICADAS")
        self.root.after(0, update)

    def set_response(self, text: str) -> None:
        self.root.after(0, lambda: self._log("JARVIS", text))
        self.set_state("HABLANDO")

    def add_message(self, sender: str, text: str) -> None:
        self.root.after(0, lambda: self._log(sender, text))

    def _log(self, sender: str, text: str) -> None:
        tag = {"SYSTEM": "system", "USER": "user", "JARVIS": "jarvis", "VOICE": "voice"}.get(sender, "system")
        self.log.insert("end", f"{sender}\n", tag)
        self.log.insert("end", f"{text}\n\n", tag if sender != "USER" else "jarvis")
        self.log.see("end")

    def _render(self) -> None:
        if not self.running:
            return
        c = self.core_canvas
        w = max(c.winfo_width(), 260)
        h = max(c.winfo_height(), 170)
        c.delete("all")
        cx, cy = w / 2, h / 2
        t = time.monotonic()
        # Subtle radial-grid effect.
        for r in range(28, int(min(w, h) * .44), 18):
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#10242d", width=1)
        for i in range(36):
            a = math.radians(i * 10 + t * 9)
            r1 = min(w, h) * .25
            r2 = r1 + (13 if i % 6 == 0 else 5)
            c.create_line(cx + math.cos(a) * r1, cy + math.sin(a) * r1, cx + math.cos(a) * r2, cy + math.sin(a) * r2, fill=CYAN if i % 6 == 0 else CYAN_DIM, width=2 if i % 6 == 0 else 1)
        pulse = 1 + .045 * math.sin(t * 3.2)
        core = min(w, h) * .105 * pulse
        for factor, color, width in ((2.2, "#12343e", 1), (1.7, CYAN_DIM, 1), (1.28, CYAN, 2)):
            r = core * factor
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=color, width=width)
        c.create_oval(cx-core*.75, cy-core*.75, cx+core*.75, cy+core*.75, fill="#0c2630", outline=CYAN, width=2)
        c.create_oval(cx-core*.28, cy-core*.28, cx+core*.28, cy+core*.28, fill=CYAN, outline=WHITE, width=1)
        c.create_text(cx, cy-7, text="JARVIS", fill=WHITE, font=("Segoe UI", 13, "bold"))
        c.create_text(cx, cy+14, text=self.activity, fill=CYAN, font=("Consolas", 7, "bold"))
        self.root.after(45, self._render)

    def _tick(self) -> None:
        if not self.running:
            return
        try:
            if psutil:
                self.metrics[0].config(text=f"CPU\n{psutil.cpu_percent(None):.0f}%")
                self.metrics[1].config(text=f"RAM\n{psutil.virtual_memory().percent:.0f}%")
            elapsed = int(time.monotonic() - self.started)
            self.metrics[2].config(text=f"UPTIME\n{elapsed // 3600:02d}:{(elapsed % 3600) // 60:02d}:{elapsed % 60:02d}")
            provider = self.brain.provider.upper()
            self.provider_label.config(text=provider)
            self.model_label.config(text=self.brain.config.claude_model if provider == "CLAUDE" else self.brain.config.ollama_model)

            if self.execution:
                snap = self.execution.snapshot()
                objective = str(snap.get("command") or "CALMADO / ESPERANDO OBJETIVO")
                self.task_label.config(text=objective[:180])
                state = str(snap.get("state", "IDLE")).upper()
                self.phase_label.config(text=f"FASE  /  {state}")

            if self.evidence:
                item = self.evidence.snapshot()
                self.evidence_title.config(text=str(item.get("title", "Tablero en espera."))[:140])
                self.evidence_status.config(text=f"STATUS  /  {str(item.get('status', 'IDLE')).upper()}")
                self.evidence_findings.config(text=f"Findings: {len(item.get('findings', []))}    Sources: {len(item.get('sources', []))}")
        except Exception:
            pass
        self.root.after(1000, self._tick)

    def run(self) -> None:
        self.root.mainloop()

    def _close(self) -> None:
        if not self.running:
            return
        self.running = False
        try:
            self.shutdown_callback()
        finally:
            self.root.after(50, self.root.destroy)
