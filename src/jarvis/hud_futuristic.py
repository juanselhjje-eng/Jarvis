from __future__ import annotations

import math
import random
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

BG = "#01050a"
PANEL = "#030b12"
PANEL_2 = "#06131b"
CYAN = "#7cecff"
CYAN_2 = "#1c9eb5"
CYAN_DIM = "#0d4654"
WHITE = "#e8fbff"
MUTED = "#58747d"
GREEN = "#63f6b0"
AMBER = "#ffd166"
RED = "#ff5c7a"
GRID = "#08232d"


class JarvisHUD:
    """Cinematic JARVIS command bridge.

    The interface is intentionally original: a central reactive core, tactical
    telemetry, mission state, activity feed and animated HUD layers. Python
    remains the runtime/backend; this class is only the visual control surface.
    """

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.running = True
        self.started = time.monotonic()
        self.activity = "STANDBY"
        self._particles = []
        self._stars = [(random.random(), random.random(), random.random() * 0.7 + 0.3) for _ in range(90)]
        self._build_window()
        self._build()
        self._render()
        self._tick()
        self._clock()

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // COMMAND BRIDGE")
        self.root.configure(bg=BG)
        self.root.minsize(1280, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1600x950")

    def _panel(self, parent, bg=PANEL):
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=CYAN_DIM)

    def _title(self, parent, title: str, right: str = "") -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=13, pady=(10, 5))
        tk.Label(row, text=title, fg=CYAN, bg=PANEL, font=("Consolas", 8, "bold")).pack(side="left")
        if right:
            tk.Label(row, text=right, fg=MUTED, bg=PANEL, font=("Consolas", 7, "bold")).pack(side="right")
        tk.Frame(parent, bg=CYAN_DIM, height=1).pack(fill="x", padx=13)

    def _build(self) -> None:
        self.bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=28, pady=(18, 0))
        top.columnconfigure(1, weight=1)
        tk.Label(top, text="J.A.R.V.I.S.", fg=WHITE, bg=BG, font=("Segoe UI", 26, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(top, text="// COMMAND BRIDGE  •  MARK VII", fg=CYAN_2, bg=BG, font=("Consolas", 9, "bold")).grid(row=0, column=1, sticky="w", padx=14, pady=(8, 0))
        self.clock_label = tk.Label(top, text="--:--:--", fg=WHITE, bg=BG, font=("Consolas", 13, "bold"))
        self.clock_label.grid(row=0, column=2, sticky="e")
        self.online = tk.Label(top, text="● ONLINE", fg=GREEN, bg=BG, font=("Consolas", 9, "bold"))
        self.online.grid(row=1, column=2, sticky="e", pady=(2, 0))
        tk.Frame(self.root, bg=CYAN_DIM, height=1).pack(fill="x", padx=28, pady=(10, 10))

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=(0, 22))
        main.grid_columnconfigure(0, weight=2)
        main.grid_columnconfigure(1, weight=5)
        main.grid_columnconfigure(2, weight=2)
        main.grid_rowconfigure(0, weight=1)
        self._left(main)
        self._center(main)
        self._right(main)

    def _left(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        identity = self._panel(col)
        identity.pack(fill="x", pady=(0, 9))
        self._title(identity, "IDENTITY MATRIX", "LOCAL CORE")
        tk.Label(identity, text="J.A.R.V.I.S.", fg=WHITE, bg=PANEL, font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=14, pady=(8, 0))
        tk.Label(identity, text="JUST A RATHER VERY INTELLIGENT SYSTEM", fg=MUTED, bg=PANEL, font=("Consolas", 7), wraplength=260, justify="left").pack(anchor="w", padx=14, pady=(1, 13))

        core = self._panel(col)
        core.pack(fill="x", pady=(0, 9))
        self._title(core, "NEURAL CORE", "ONE AGENT")
        self.provider_label = tk.Label(core, text=self.brain.provider.upper(), fg=CYAN, bg=PANEL, font=("Segoe UI", 17, "bold"))
        self.provider_label.pack(anchor="w", padx=14, pady=(7, 0))
        model = getattr(self.brain.config, "ollama_model", "local") if self.brain.provider == "ollama" else getattr(self.brain.config, "claude_model", "claude")
        self.model_label = tk.Label(core, text=str(model), fg=MUTED, bg=PANEL, font=("Consolas", 8, "bold"))
        self.model_label.pack(anchor="w", padx=14, pady=(0, 8))
        self.core_status = tk.Label(core, text="● STANDBY", fg=GREEN, bg=PANEL, font=("Consolas", 8, "bold"))
        self.core_status.pack(anchor="w", padx=14, pady=(0, 13))

        sensors = self._panel(col)
        sensors.pack(fill="x", pady=(0, 9))
        self._title(sensors, "SYSTEM SENSORS", "LIVE")
        self.sensor_labels = {}
        for name in ("CPU", "RAM", "GPU", "TEMP", "DISK"):
            row = tk.Frame(sensors, bg=PANEL_2)
            row.pack(fill="x", padx=11, pady=2)
            label = tk.Label(row, text=f"{name:<6} --", fg=WHITE, bg=PANEL_2, font=("Consolas", 8, "bold"), anchor="w")
            label.pack(fill="x", padx=8, pady=6)
            self.sensor_labels[name] = label

        controls = self._panel(col)
        controls.pack(fill="x")
        self._title(controls, "COMMAND DECK", "READY")
        self._button(controls, "NEW SESSION", self._clear_chat).pack(fill="x", padx=11, pady=3)
        self._button(controls, "LISTEN NOW", self._voice, True).pack(fill="x", padx=11, pady=3)
        self._button(controls, "SHUT DOWN", self._close).pack(fill="x", padx=11, pady=3)
        tk.Label(controls, text="MIC  READY   •   CAMERA  OFF\nMEMORY  LOCAL   •   TOOLS  VERIFIED", fg=MUTED, bg=PANEL, font=("Consolas", 7), justify="left").pack(anchor="w", padx=13, pady=11)

    def _center(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=1, sticky="nsew")
        col.grid_rowconfigure(0, weight=4)
        col.grid_rowconfigure(1, weight=2)
        col.grid_columnconfigure(0, weight=1)

        core = self._panel(col)
        core.grid(row=0, column=0, sticky="nsew", pady=(0, 9))
        self.core_canvas = tk.Canvas(core, bg=PANEL, highlightthickness=0)
        self.core_canvas.pack(fill="both", expand=True)

        console = self._panel(col)
        console.grid(row=1, column=0, sticky="nsew")
        console.grid_rowconfigure(1, weight=1)
        console.grid_columnconfigure(0, weight=1)
        self._title(console, "NEURAL CONSOLE", "SECURE CHANNEL")
        self.log = scrolledtext.ScrolledText(console, bg=PANEL, fg=WHITE, insertbackground=CYAN, selectbackground="#0d3946", relief="flat", bd=0, font=("Segoe UI", 9), wrap="word", padx=14, pady=8)
        self.log.grid(row=1, column=0, sticky="nsew", padx=8)
        self.log.tag_configure("system", foreground=MUTED, font=("Consolas", 8))
        self.log.tag_configure("user", foreground=CYAN, font=("Segoe UI", 9, "bold"))
        self.log.tag_configure("jarvis", foreground=WHITE, font=("Segoe UI", 9))
        self.log.tag_configure("voice", foreground=AMBER, font=("Consolas", 8))
        self._log("SYSTEM", "COMMAND BRIDGE INITIALIZED // AWAITING OBJECTIVE")

        compose = tk.Frame(console, bg=PANEL)
        compose.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        compose.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(compose, bg=PANEL_2, fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=11)
        self.entry.insert(0, "Enter command…")
        self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", lambda _: self._send())
        self._button(compose, "EXECUTE", self._send, True).grid(row=0, column=1, padx=(7, 0))
        self._button(compose, "MIC", self._voice).grid(row=0, column=2, padx=(5, 0))

    def _right(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=2, sticky="nsew", padx=(9, 0))

        mission = self._panel(col)
        mission.pack(fill="x", pady=(0, 9))
        self._title(mission, "MISSION STATUS", "REAL TIME")
        self.task_label = tk.Label(mission, text="NO ACTIVE OBJECTIVE", fg=WHITE, bg=PANEL, font=("Segoe UI", 10, "bold"), wraplength=260, justify="left")
        self.task_label.pack(anchor="w", padx=14, pady=(8, 2))
        self.phase_label = tk.Label(mission, text="STANDBY  /  PHASE 00", fg=GREEN, bg=PANEL, font=("Consolas", 8, "bold"))
        self.phase_label.pack(anchor="w", padx=14, pady=(0, 11))

        evidence = self._panel(col)
        evidence.pack(fill="x", pady=(0, 9))
        self._title(evidence, "EVIDENCE BOARD", "INTELLIGENCE")
        self.evidence_title = tk.Label(evidence, text="No active investigation.", fg=WHITE, bg=PANEL, font=("Segoe UI", 8, "bold"), wraplength=260, justify="left")
        self.evidence_title.pack(anchor="w", padx=14, pady=(7, 2))
        self.evidence_status = tk.Label(evidence, text="STATUS / IDLE", fg=MUTED, bg=PANEL, font=("Consolas", 7, "bold"))
        self.evidence_status.pack(anchor="w", padx=14)
        self.evidence_findings = tk.Label(evidence, text="FINDINGS  0   SOURCES  0", fg=WHITE, bg=PANEL, font=("Consolas", 8, "bold"))
        self.evidence_findings.pack(anchor="w", padx=14, pady=(4, 11))

        activity = self._panel(col)
        activity.pack(fill="both", expand=True, pady=(0, 9))
        self._title(activity, "ACTIVITY STREAM", "LIVE FEED")
        self.activity_canvas = tk.Canvas(activity, bg=PANEL, highlightthickness=0, height=210)
        self.activity_canvas.pack(fill="both", expand=True, padx=8, pady=8)

        footer = self._panel(col)
        footer.pack(fill="x")
        self._title(footer, "LINK STATUS", "ENCRYPTED")
        self.link_label = tk.Label(footer, text="OLLAMA  •  LOCAL MEMORY  •  WHISPER", fg=CYAN_2, bg=PANEL, font=("Consolas", 7, "bold"))
        self.link_label.pack(anchor="w", padx=14, pady=(5, 12))

    def _button(self, parent, text: str, command, primary: bool = False):
        return tk.Button(parent, text=text, command=command, bg="#0a303b" if primary else PANEL_2, fg=CYAN if primary else WHITE, activebackground="#125261", activeforeground=WHITE, relief="flat", bd=0, cursor="hand2", font=("Consolas", 8, "bold"), padx=12, pady=8)

    def _clear_placeholder(self, _event=None):
        if self.entry.get() == "Enter command…":
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)

    def _send(self):
        text = self.entry.get().strip()
        if not text or text == "Enter command…":
            return
        self.entry.delete(0, "end")
        self._log("USER", text)
        self.set_state("THINKING")
        self._set_mission(text)
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _voice(self):
        self._log("VOICE", "LISTENING FOR COMMAND…")
        self.set_state("LISTENING")
        threading.Thread(target=self._voice_worker, daemon=True, name="jarvis-manual-voice").start()

    def _voice_worker(self):
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.root.after(0, lambda: self._log("USER", command))
                self.root.after(0, lambda: self._set_mission(command))
                self.process_command(command)
            else:
                self.root.after(0, lambda: self.set_state("STANDBY"))
        except Exception as exc:
            self.root.after(0, lambda: self._log("VOICE", f"ERROR: {exc}"))
            self.root.after(0, lambda: self.set_state("STANDBY"))

    def _clear_chat(self):
        def work():
            try:
                self.brain.reset_conversation()
            finally:
                self.root.after(0, self._clear_log)
        threading.Thread(target=work, daemon=True).start()

    def _clear_log(self):
        self.log.delete("1.0", "end")
        self._log("SYSTEM", "NEURAL CONTEXT RESET // NEW SESSION READY")

    def _set_mission(self, text: str):
        self.task_label.config(text=text[:150])
        self.phase_label.config(text="ACTIVE  /  PHASE 01", fg=CYAN)

    def set_state(self, state: str):
        def update():
            if not self.running:
                return
            aliases = {"CALMADO": "STANDBY", "ESCUCHANDO": "LISTENING", "HABLANDO": "SPEAKING", "PROCESANDO": "THINKING", "ANALYZING COMMAND": "ANALYZING"}
            self.activity = aliases.get(state.upper(), state.upper())
            colors = {"STANDBY": GREEN, "LISTENING": AMBER, "SPEAKING": CYAN, "THINKING": CYAN, "ANALYZING": CYAN, "EXECUTING": CYAN}
            color = colors.get(self.activity, CYAN)
            self.core_status.config(text=f"● {self.activity}", fg=color)
            self.online.config(text=f"● ONLINE  /  {self.activity}", fg=color)
            self.phase_label.config(text="STANDBY  /  PHASE 00" if self.activity == "STANDBY" else "ACTIVE  /  PHASE 02", fg=color)
        self.root.after(0, update)

    def set_response(self, text: str):
        self.root.after(0, lambda: self._log("JARVIS", text))
        self.set_state("SPEAKING")

    def add_message(self, sender: str, text: str):
        self.root.after(0, lambda: self._log(sender, text))

    def _log(self, sender: str, text: str):
        tag = {"SYSTEM": "system", "USER": "user", "JARVIS": "jarvis", "VOICE": "voice"}.get(sender, "system")
        self.log.insert("end", f"{sender}\n", tag)
        self.log.insert("end", f"{text}\n\n", tag)
        self.log.see("end")

    def _draw_background(self):
        c = self.bg_canvas
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10:
            return
        c.delete("all")
        step = 45
        offset = int((time.monotonic() * 8) % step)
        for x in range(-step, w + step, step):
            c.create_line(x + offset, 0, x + offset, h, fill=GRID)
        for y in range(-step, h + step, step):
            c.create_line(0, y + offset, w, y + offset, fill=GRID)
        for sx, sy, brightness in self._stars:
            x, y = sx * w, sy * h
            c.create_oval(x, y, x + 1.4, y + 1.4, fill=CYAN_DIM if brightness > 0.5 else GRID, outline="")

    def _render(self):
        if not self.running:
            return
        self._draw_background()
        self._draw_core()
        self._draw_activity()
        self.root.after(33, self._render)

    def _draw_core(self):
        c = self.core_canvas
        w, h = max(c.winfo_width(), 400), max(c.winfo_height(), 300)
        c.delete("all")
        cx, cy = w / 2, h / 2
        t = time.monotonic()
        state_speed = {"STANDBY": 0.7, "LISTENING": 1.6, "THINKING": 2.7, "SPEAKING": 2.0, "ANALYZING": 2.4}.get(self.activity, 1.5)
        base = min(w, h) * 0.19

        # Tactical rings.
        for i in range(7):
            r = base + i * min(w, h) * 0.055
            a = t * state_speed * (1 if i % 2 else -1) + i * 0.45
            start = math.degrees(a) % 360
            extent = 245 if i % 2 else 190
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start, extent=extent, outline=CYAN_DIM if i > 2 else CYAN_2, width=1 + (i % 2))
            c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start + 180, extent=35, outline=CYAN, width=2)

        # Radial ticks and targeting marks.
        outer = base + min(w, h) * 0.35
        for i in range(72):
            a = math.radians(i * 5 + t * 12)
            r1 = outer - (10 if i % 6 == 0 else 4)
            r2 = outer + (8 if i % 6 == 0 else 1)
            c.create_line(cx + math.cos(a) * r1, cy + math.sin(a) * r1, cx + math.cos(a) * r2, cy + math.sin(a) * r2, fill=CYAN_2 if i % 6 == 0 else CYAN_DIM, width=2 if i % 6 == 0 else 1)

        # Orbiting nodes.
        for i in range(8):
            a = t * (0.5 + i * 0.03) + i * math.pi / 4
            r = base + min(w, h) * 0.22
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
            c.create_oval(x-3, y-3, x+3, y+3, fill=CYAN, outline="")

        pulse = 1 + math.sin(t * 4.2) * 0.08
        core_r = base * 0.42 * pulse
        c.create_oval(cx-core_r*1.6, cy-core_r*1.6, cx+core_r*1.6, cy+core_r*1.6, outline=CYAN_DIM, width=2)
        c.create_oval(cx-core_r, cy-core_r, cx+core_r, cy+core_r, fill="#06212b", outline=CYAN_2, width=3)
        c.create_oval(cx-core_r*0.55, cy-core_r*0.55, cx+core_r*0.55, cy+core_r*0.55, fill="#0b4351", outline=CYAN, width=2)
        c.create_oval(cx-7, cy-7, cx+7, cy+7, fill=WHITE, outline=CYAN)

        scan = math.radians(t * 70)
        c.create_line(cx, cy, cx + math.cos(scan) * outer, cy + math.sin(scan) * outer, fill=CYAN_2, width=1)
        c.create_text(cx, cy - outer - 16, text="NEURAL CORE // LIVE", fill=CYAN, font=("Consolas", 8, "bold"))
        c.create_text(cx, cy + outer + 14, text=self.activity, fill=WHITE, font=("Consolas", 9, "bold"))

    def _draw_activity(self):
        c = self.activity_canvas
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 180)
        c.delete("all")
        t = time.monotonic()
        for i in range(28):
            x = 10 + i * max(4, (w - 20) / 28)
            amp = 4 + 13 * (0.5 + 0.5 * math.sin(t * 3 + i * 0.8))
            y = h / 2 + math.sin(t * 5 + i * 0.7) * amp
            c.create_line(x, h/2, x, y, fill=CYAN_2 if i % 3 else CYAN, width=2)
        c.create_text(12, 12, text="SIGNAL ACTIVITY", anchor="nw", fill=MUTED, font=("Consolas", 7, "bold"))
        c.create_text(w-12, 12, text=f"{self.activity}", anchor="ne", fill=CYAN, font=("Consolas", 7, "bold"))

    def _tick(self):
        if not self.running:
            return
        cpu = psutil.cpu_percent(interval=None) if psutil else 0
        ram = psutil.virtual_memory().percent if psutil else 0
        disk = psutil.disk_usage("C:\\").percent if psutil else 0
        self.sensor_labels["CPU"].config(text=f"CPU    {cpu:>3.0f}%   {'█' * int(cpu/10):<10}")
        self.sensor_labels["RAM"].config(text=f"RAM    {ram:>3.0f}%   {'█' * int(ram/10):<10}")
        self.sensor_labels["DISK"].config(text=f"DISK   {disk:>3.0f}%   {'█' * int(disk/10):<10}")
        self.sensor_labels["GPU"].config(text="GPU    ONLINE")
        self.sensor_labels["TEMP"].config(text="TEMP   SENSOR")
        if self.evidence and self.evidence.latest():
            item = self.evidence.latest()
            self.evidence_title.config(text=getattr(item, "title", "Investigation")[:90])
            self.evidence_status.config(text=f"STATUS / {getattr(item, 'status', 'ACTIVE')}")
        self.root.after(1000, self._tick)

    def _clock(self):
        if not self.running:
            return
        self.clock_label.config(text=time.strftime("%H:%M:%S"))
        self.root.after(500, self._clock)

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
