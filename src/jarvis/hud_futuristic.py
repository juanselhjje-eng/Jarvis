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

BG = "#020407"
PANEL = "#050a0f"
PANEL_2 = "#081119"
LINE = "#17303b"
CYAN = "#69eaff"
CYAN_2 = "#1f8395"
WHITE = "#e8f8fb"
MUTED = "#617781"
GREEN = "#5cf0aa"
AMBER = "#ffd166"


class JarvisHUD:
    """Mission Control original: consola cinematográfica, reactor y paneles de misión."""

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
        self.root.minsize(1360, 800)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1600x950")

    def _card(self, parent, bg=PANEL):
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def _section(self, parent, title: str, right: str = "") -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(14, 7))
        tk.Label(row, text=title, fg=CYAN, bg=PANEL, font=("Consolas", 8, "bold")).pack(side="left")
        if right:
            tk.Label(row, text=right, fg=MUTED, bg=PANEL, font=("Consolas", 7, "bold")).pack(side="right")
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x", padx=18)

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=BG, height=78)
        header.pack(fill="x", padx=30, pady=(17, 0))
        header.pack_propagate(False)
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left", fill="y")
        tk.Label(brand, text="JARVIS", fg=WHITE, bg=BG, font=("Segoe UI", 28, "bold")).pack(side="left", pady=2)
        tk.Label(brand, text="  //  MISSION CONTROL", fg=CYAN_2, bg=BG, font=("Consolas", 9, "bold")).pack(side="left", pady=(15, 0))
        status = tk.Frame(header, bg=BG)
        status.pack(side="right", fill="y")
        self.online = tk.Label(status, text="● ONLINE", fg=GREEN, bg=BG, font=("Consolas", 10, "bold"))
        self.online.pack(anchor="e", pady=(5, 0))
        self.status_text = tk.Label(status, text="NEURAL LINK  •  LOCAL CORE  •  VERIFIED TOOLS", fg=MUTED, bg=BG, font=("Consolas", 7))
        self.status_text.pack(anchor="e", pady=(3, 0))
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", padx=30)

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=30, pady=(14, 26))
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=5)
        main.grid_columnconfigure(2, weight=2)
        main.grid_rowconfigure(0, weight=1)
        self._build_left(main)
        self._build_center(main)
        self._build_right(main)

    def _build_left(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        identity = self._card(col)
        identity.pack(fill="x", pady=(0, 10))
        self._section(identity, "IDENTIDAD", "MARK 06 / LOCAL")
        tk.Label(identity, text="J.A.R.V.I.S.", fg=WHITE, bg=PANEL, font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(8, 0))
        tk.Label(identity, text="JUST A RATHER VERY INTELLIGENT SYSTEM", fg=MUTED, bg=PANEL, font=("Consolas", 7, "bold"), wraplength=280, justify="left").pack(anchor="w", padx=18, pady=(2, 16))

        core = self._card(col)
        core.pack(fill="x", pady=(0, 10))
        self._section(core, "NEURAL CORE", "ONE AGENT")
        model = getattr(self.brain.config, "ollama_model", "local") if self.brain.provider == "ollama" else getattr(self.brain.config, "claude_model", "claude")
        self.provider_label = tk.Label(core, text=self.brain.provider.upper(), fg=WHITE, bg=PANEL, font=("Segoe UI", 18, "bold"))
        self.provider_label.pack(anchor="w", padx=18, pady=(6, 0))
        tk.Label(core, text=str(model), fg=CYAN_2, bg=PANEL, font=("Consolas", 8, "bold")).pack(anchor="w", padx=18, pady=(1, 11))
        self.core_status = tk.Label(core, text="● READY", fg=GREEN, bg=PANEL, font=("Consolas", 8, "bold"))
        self.core_status.pack(anchor="w", padx=18, pady=(0, 16))

        controls = self._card(col)
        controls.pack(fill="x")
        self._section(controls, "SYSTEM CONTROLS")
        self._button(controls, "NUEVA CONVERSACIÓN", self._clear_chat).pack(fill="x", padx=16, pady=4)
        self._button(controls, "ESCUCHAR AHORA", self._voice).pack(fill="x", padx=16, pady=4)
        self._button(controls, "APAGAR JARVIS", self._close).pack(fill="x", padx=16, pady=4)
        tk.Label(controls, text="CAMERA  OFF\nMIC INPUT  READY\nMEMORY  LOCAL", fg=MUTED, bg=PANEL, font=("Consolas", 7), justify="left").pack(anchor="w", padx=18, pady=15)

    def _build_center(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=1, sticky="nsew")
        col.grid_rowconfigure(0, weight=1)
        col.grid_columnconfigure(0, weight=1)
        chat = self._card(col)
        chat.grid(row=0, column=0, sticky="nsew")
        chat.grid_rowconfigure(1, weight=1)
        chat.grid_columnconfigure(0, weight=1)
        self._section(chat, "NEURAL CONVERSATION", "PRIVATE CHANNEL")
        self.log = scrolledtext.ScrolledText(chat, bg=PANEL, fg=WHITE, insertbackground=CYAN, selectbackground="#12323d", relief="flat", bd=0, font=("Segoe UI", 10), wrap="word", padx=24, pady=18, spacing1=5, spacing3=10)
        self.log.grid(row=1, column=0, sticky="nsew", padx=7)
        self.log.tag_configure("system", foreground=MUTED, font=("Consolas", 8))
        self.log.tag_configure("user", foreground=CYAN, font=("Segoe UI", 10, "bold"))
        self.log.tag_configure("jarvis", foreground=WHITE, font=("Segoe UI", 10))
        self.log.tag_configure("voice", foreground=AMBER, font=("Consolas", 8))
        self._log("SYSTEM", "Neural interface initialized. Awaiting command.")

        compose = tk.Frame(chat, bg=PANEL)
        compose.grid(row=2, column=0, sticky="ew", padx=18, pady=(5, 16))
        compose.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(compose, bg=PANEL_2, fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 11))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=14)
        self.entry.insert(0, "Escriba una orden…")
        self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", lambda _: self._send())
        self._button(compose, "EXECUTE", self._send, True).grid(row=0, column=1, padx=(8, 0))
        self._button(compose, "◉", self._voice).grid(row=0, column=2, padx=(5, 0))

    def _build_right(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        col.grid_rowconfigure(3, weight=1)
        reactor = self._card(col)
        reactor.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._section(reactor, "ARC REACTOR", "LIVE")
        self.reactor_canvas = tk.Canvas(reactor, height=220, bg=PANEL, highlightthickness=0)
        self.reactor_canvas.pack(fill="x", padx=10, pady=(0, 12))

        mission = self._card(col)
        mission.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._section(mission, "MISSION STATUS", "EXECUTION")
        self.task_label = tk.Label(mission, text="STANDBY / AWAITING OBJECTIVE", fg=WHITE, bg=PANEL, font=("Segoe UI", 10, "bold"), wraplength=300, justify="left")
        self.task_label.pack(anchor="w", padx=18, pady=(7, 0))
        self.phase_label = tk.Label(mission, text="PHASE 01  /  READY", fg=GREEN, bg=PANEL, font=("Consolas", 8, "bold"))
        self.phase_label.pack(anchor="w", padx=18, pady=(5, 15))

        evidence = self._card(col)
        evidence.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self._section(evidence, "EVIDENCE BOARD", "RESEARCH")
        self.evidence_title = tk.Label(evidence, text="No active investigation.", fg=WHITE, bg=PANEL, font=("Segoe UI", 9, "bold"), wraplength=300, justify="left")
        self.evidence_title.pack(anchor="w", padx=18, pady=(7, 3))
        self.evidence_status = tk.Label(evidence, text="STATUS / IDLE", fg=MUTED, bg=PANEL, font=("Consolas", 7, "bold"))
        self.evidence_status.pack(anchor="w", padx=18)
        self.evidence_findings = tk.Label(evidence, text="FINDINGS  0     SOURCES  0", fg=WHITE, bg=PANEL, font=("Consolas", 8, "bold"))
        self.evidence_findings.pack(anchor="w", padx=18, pady=(4, 12))

        telemetry = self._card(col)
        telemetry.grid(row=3, column=0, sticky="nsew")
        self._section(telemetry, "SYSTEM TELEMETRY", "LOCAL")
        self.metrics = []
        for name in ("CPU LOAD", "MEMORY", "UPTIME"):
            row = tk.Frame(telemetry, bg=PANEL_2, highlightthickness=1, highlightbackground=LINE)
            row.pack(fill="x", padx=14, pady=3)
            label = tk.Label(row, text=f"{name:<12} --", fg=WHITE, bg=PANEL_2, font=("Consolas", 8, "bold"), anchor="w", padx=10, pady=7)
            label.pack(fill="x")
            self.metrics.append(label)
        tk.Label(telemetry, text="OLLAMA / CLAUDE  •  WHISPER LOCAL  •  CAMERA OFF", fg="#40535b", bg=PANEL, font=("Consolas", 7, "bold")).pack(anchor="w", padx=18, pady=14)

    def _button(self, parent, text: str, command, primary: bool = False):
        return tk.Button(parent, text=text, command=command, bg="#0b3039" if primary else PANEL_2, fg=CYAN if primary else WHITE, activebackground="#16434e", activeforeground=WHITE, relief="flat", bd=0, cursor="hand2", font=("Consolas", 8, "bold"), padx=14, pady=10)

    def _clear_placeholder(self, _event=None):
        if self.entry.get() == "Escriba una orden…":
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)

    def _send(self):
        text = self.entry.get().strip()
        if not text or text == "Escriba una orden…":
            return
        self.entry.delete(0, "end")
        self._log("USER", text)
        self.set_state("PROCESANDO")
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _voice(self):
        self._log("VOICE", "Listening…")
        self.set_state("ESCUCHANDO")
        threading.Thread(target=self._voice_worker, daemon=True, name="jarvis-manual-voice").start()

    def _voice_worker(self):
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

    def _clear_chat(self):
        def work():
            try:
                self.brain.reset_conversation()
            finally:
                self.root.after(0, self._clear_log)
        threading.Thread(target=work, daemon=True).start()

    def _clear_log(self):
        self.log.delete("1.0", "end")
        self._log("SYSTEM", "Conversation buffer cleared. Neural context reset.")

    def set_state(self, state: str):
        def update():
            if not self.running:
                return
            self.activity = state.upper()
            colors = {"CALMADO": GREEN, "ESCUCHANDO": AMBER, "HABLANDO": CYAN, "PROCESANDO": CYAN, "ANALYZING COMMAND": CYAN, "THINKING": CYAN}
            color = colors.get(self.activity, CYAN)
            self.core_status.config(text=f"● {self.activity}", fg=color)
            self.status_text.config(text=f"{self.brain.provider.upper()}  •  {self.activity}  •  VERIFIED TOOLS")
            self.phase_label.config(text="PHASE 01  /  READY" if self.activity == "CALMADO" else "PHASE 02  /  ACTIVE", fg=color)
        self.root.after(0, update)

    def set_response(self, text: str):
        self.root.after(0, lambda: self._log("JARVIS", text))
        self.set_state("HABLANDO")

    def add_message(self, sender: str, text: str):
        self.root.after(0, lambda: self._log(sender, text))

    def _log(self, sender: str, text: str):
        tag = {"SYSTEM": "system", "USER": "user", "JARVIS": "jarvis", "VOICE": "voice"}.get(sender, "system")
        self.log.insert("end", f"{sender}\n", tag)
        self.log.insert("end", f"{text}\n\n", tag)
        self.log.see("end")

    def _render(self):
        if not self.running:
            return
        c = self.reactor_canvas
        w = max(c.winfo_width(), 300)
        h = max(c.winfo_height(), 220)
        c.delete("all")
        cx, cy = w / 2, h / 2
        t = time.monotonic()
        maxr = min(w, h) * 0.39
        for r in range(int(maxr), 25, -19):
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#102832", width=1)
        for i in range(60):
            a = math.radians(i * 6 + t * 15)
            r1 = maxr - 3
            r2 = maxr + (5 if i % 5 == 0 else 0)
            c.create_line(cx + math.cos(a)*r1, cy + math.sin(a)*r1, cx + math.cos(a)*r2, cy + math.sin(a)*r2, fill=CYAN_2 if i % 5 == 0 else LINE, width=2 if i % 5 == 0 else 1)
        pulse = 31 + math.sin(t * 3.1) * 5
        c.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse, fill="#071a21", outline=CYAN_2, width=2)
        inner = 18 + math.sin(t * 4.5) * 3
        c.create_oval(cx-inner, cy-inner, cx+inner, cy+inner, fill="#0a2c35", outline=CYAN, width=2)
        c.create_oval(cx-5, cy-5, cx+5, cy+5, fill=CYAN, outline=CYAN)
        scan = math.radians(t * 52)
        c.create_line(cx, cy, cx + math.cos(scan)*maxr, cy + math.sin(scan)*maxr, fill=CYAN_2, width=1)
        c.create_text(cx, cy + maxr + 17, text=self.activity, fill=CYAN, font=("Consolas", 8, "bold"))
        self.root.after(45, self._render)

    def _tick(self):
        if not self.running:
            return
        cpu = psutil.cpu_percent(interval=None) if psutil else 0
        ram = psutil.virtual_memory().percent if psutil else 0
        uptime = int(time.monotonic() - self.started)
        hours, rem = divmod(uptime, 3600)
        mins, secs = divmod(rem, 60)
        values = (f"CPU LOAD     {cpu:>3.0f}%", f"MEMORY       {ram:>3.0f}%", f"UPTIME       {hours:02d}:{mins:02d}:{secs:02d}")
        for label, value in zip(self.metrics, values):
            label.config(text=value)
        self.root.after(1000, self._tick)

    def _close(self):
        if not self.running:
            return
        self.running = False
        try:
            self.shutdown_callback()
        finally:
            self.root.after(50, self.root.destroy)

    def run(self):
        self.root.mainloop()
