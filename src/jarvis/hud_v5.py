from __future__ import annotations

import math
import tkinter as tk
from datetime import datetime
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


BG = "#020509"
PANEL = "#071018"
PANEL_ALT = "#09141d"
LINE = "#18303c"
CYAN = "#25d9ff"
CYAN_DARK = "#0b6475"
ORANGE = "#ffad4a"
GREEN = "#3ee5a1"
RED = "#ff5f73"
WHITE = "#e8f6fa"
MUTED = "#6d8791"


class JarvisHUDv5:
    """Mission Control nativo: interactivo, técnico y orientado a operaciones."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], neural=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.neural = neural
        self.root = tk.Tk()
        self.state = "STANDBY"
        self.phase = 0.0
        self.history: list[str] = []
        self._build_window()
        self._build_ui()
        self._pulse()
        self._clock()
        self._telemetry()

    def _build_window(self) -> None:
        self.root.title("J.A.R.V.I.S. // AUTONOMOUS COMPUTER OPERATIONS")
        self.root.configure(bg=BG)
        self.root.minsize(1320, 800)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1600x950")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<F2>", lambda _e: self.entry.focus_set())
        self.root.bind("<Control-Shift-J>", lambda _e: self.entry.focus_set())

    def label(self, parent, text, size=9, fg=WHITE, bold=False, anchor="w"):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor=anchor)

    def button(self, parent, text, command, width=None, accent=False):
        return tk.Button(parent, text=text, command=command, width=width, bg="#0a1a23" if not accent else "#102934", fg=CYAN if accent else WHITE, activebackground="#173844", activeforeground=WHITE, relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=8, pady=7)

    def panel(self, parent, row, column, padx=0, pady=0, sticky="nsew"):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        frame.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
        return frame

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#010307", height=58, highlightthickness=1, highlightbackground=LINE)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.label(header, "J.A.R.V.I.S.", 15, CYAN, True).pack(side="left", padx=20)
        self.label(header, "AUTONOMOUS COMPUTER OPERATIONS / MISSION CONTROL", 8, MUTED, True).pack(side="left", padx=10)
        self.provider_label = self.label(header, "CORE: --", 8, GREEN, True)
        self.provider_label.pack(side="right", padx=16)
        self.clock_label = self.label(header, "--:--:--", 9, WHITE, True)
        self.clock_label.pack(side="right", padx=12)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, minsize=250)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=320)
        body.grid_rowconfigure(0, weight=1)
        self._left(body)
        self._center(body)
        self._right(body)
        self._composer()

    def _left(self, body) -> None:
        left = self.panel(body, 0, 0, padx=(0, 6))
        self.label(left, "ARCHITECTURE", 9, CYAN, True).pack(anchor="w", padx=14, pady=(15, 9))
        modules = [
            ("01", "CORE AGENT", "Gemini / Ollama"),
            ("02", "PERCEPTION", "Vision on demand"),
            ("03", "PLANNER", "Task decomposition"),
            ("04", "ACTION LOOP", "Observe / decide / act"),
            ("05", "OS CONTROL", "Visible Windows UI"),
            ("06", "MEMORY", "Persistent local state"),
            ("07", "NEURAL LAB", "Trainable local models"),
        ]
        for num, name, detail in modules:
            row = tk.Frame(left, bg=left["bg"])
            row.pack(fill="x", padx=12, pady=4)
            self.label(row, num, 7, CYAN_DARK, True).pack(side="left", padx=(0, 8))
            text = tk.Frame(row, bg=row["bg"])
            text.pack(side="left", fill="x")
            self.label(text, name, 8, WHITE, True).pack(anchor="w")
            self.label(text, detail, 7, MUTED).pack(anchor="w")

        self.label(left, "OPERATIONS", 9, CYAN, True).pack(anchor="w", padx=14, pady=(20, 7))
        for text, command in (("SYSTEM DIAGNOSTIC", "revisa mi pc"), ("SCREEN OBSERVE", "mira la pantalla"), ("OPEN TEAMS", "abre teams personal"), ("NEURAL TEST", "crea una red neuronal")):
            self.button(left, text, lambda c=command: self._quick(c)).pack(fill="x", padx=12, pady=3)

        self.label(left, "STATUS", 9, CYAN, True).pack(anchor="w", padx=14, pady=(20, 6))
        self.status_text = self.label(left, "CORE READY\nHUMAN GATE: ON\nSCREEN CAPTURE: ON DEMAND", 8, MUTED)
        self.status_text.pack(anchor="w", padx=14)

    def _center(self, body) -> None:
        center = self.panel(body, 0, 1, padx=6)
        center.grid_rowconfigure(1, weight=1)
        center.grid_rowconfigure(2, minsize=160)
        center.grid_columnconfigure(0, weight=1)
        top = tk.Frame(center, bg=center["bg"], height=42)
        top.grid(row=0, column=0, sticky="ew")
        self.label(top, "PERCEPTION FIELD / AGENT CORE", 9, WHITE, True).pack(side="left", padx=15, pady=12)
        self.state_label = self.label(top, self.state, 8, CYAN, True)
        self.state_label.pack(side="right", padx=15)

        field = tk.Frame(center, bg="#010509")
        field.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        field.grid_rowconfigure(0, weight=1)
        field.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(field, bg="#010509", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        stream_box = tk.Frame(center, bg=center["bg"])
        stream_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.label(stream_box, "LIVE EVENT BUS", 8, CYAN, True).pack(anchor="w", padx=5, pady=(3, 4))
        self.stream = tk.Text(stream_box, bg="#02070b", fg="#9ab2ba", insertbackground=CYAN, relief="flat", bd=0, font=("Consolas", 8), state="disabled")
        self.stream.pack(fill="both", expand=True)

    def _right(self, body) -> None:
        right = self.panel(body, 0, 2, padx=(6, 0))
        self.label(right, "MISSION CONTROL", 10, WHITE, True).pack(anchor="w", padx=14, pady=(15, 2))
        self.label(right, "GOAL → REASON → PLAN → ACT → VERIFY", 7, MUTED, True).pack(anchor="w", padx=14, pady=(0, 12))
        self.mission = self.label(right, "No active mission.", 8, MUTED)
        self.mission.pack(anchor="w", padx=14, pady=(0, 8))
        self.ooda = []
        for name in ("PERCEIVE", "ORIENT", "DECIDE", "ACT", "VERIFY"):
            item = self.label(right, "○  " + name, 8, MUTED, True)
            item.pack(anchor="w", padx=16, pady=3)
            self.ooda.append(item)
        self.label(right, "TELEMETRY", 8, CYAN, True).pack(anchor="w", padx=14, pady=(17, 5))
        self.telemetry = self.label(right, "CPU --\nRAM --\nDISK --", 8, MUTED)
        self.telemetry.pack(anchor="w", padx=14)
        self.label(right, "LEARNING", 8, CYAN, True).pack(anchor="w", padx=14, pady=(17, 5))
        self.learning = self.label(right, "NEURAL LAB: idle", 8, MUTED)
        self.learning.pack(anchor="w", padx=14)
        if self.neural:
            self.learning.config(text=self.neural.status())
        self.label(right, "HUMAN GATE", 8, CYAN, True).pack(anchor="w", padx=14, pady=(17, 5))
        self.gate = self.label(right, "ARMED / EXTERNAL ACTIONS REQUIRE CONFIRMATION", 8, ORANGE, True, anchor="w")
        self.gate.pack(anchor="w", padx=14)
        self.button(right, "NEW MISSION", self._new_session, accent=True).pack(fill="x", padx=12, pady=(18, 4))
        self.button(right, "STOP JARVIS", self._close).pack(fill="x", padx=12, pady=4)

    def _composer(self) -> None:
        bar = tk.Frame(self.root, bg="#010307", highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(bar, bg="#08131b", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10, ipady=10)
        self.entry.bind("<Return>", lambda _e: self._send())
        self.button(bar, "MIC", self._voice, width=6).pack(side="left", padx=3)
        self.button(bar, "EXECUTE", self._send, width=10, accent=True).pack(side="left", padx=(3, 10))

    def _draw(self) -> None:
        c = self.canvas
        w, h = max(c.winfo_width(), 600), max(c.winfo_height(), 450)
        c.delete("all")
        for x in range(0, w, 28):
            c.create_line(x, 0, x, h, fill="#07131a")
        for y in range(0, h, 28):
            c.create_line(0, y, w, y, fill="#07131a")
        cx, cy = w / 2, h / 2
        pulse = math.sin(self.phase * 1.8) * 5
        for r in (170, 142, 112):
            c.create_oval(cx-r-pulse, cy-r-pulse, cx+r+pulse, cy+r+pulse, outline="#0b2933", width=1)
        for i, radius in enumerate((122, 82, 45)):
            points = []
            for j in range(6):
                angle = math.radians(j * 60 - 30 + self.phase * (1 if i else -0.5))
                points += [cx + (radius + pulse) * math.cos(angle), cy + (radius + pulse) * math.sin(angle)]
            c.create_polygon(*points, outline=(CYAN_DARK, CYAN, WHITE)[i], fill="", width=2 if i < 2 else 1)
        for i in range(16):
            a = math.radians(i * 22.5 + self.phase * 5)
            x1, y1 = cx + 145 * math.cos(a), cy + 145 * math.sin(a)
            x2, y2 = cx + 184 * math.cos(a), cy + 184 * math.sin(a)
            c.create_line(x1, y1, x2, y2, fill="#0c5360", width=2)
        c.create_text(cx, cy - 14, text="CORE AGENT", fill=WHITE, font=("Segoe UI", 14, "bold"))
        c.create_text(cx, cy + 12, text=self.state, fill=CYAN, font=("Consolas", 9, "bold"))
        c.create_text(18, 18, text="OBSERVATION: EXPLICIT / USER-DIRECTED", fill=CYAN_DARK, anchor="nw", font=("Consolas", 8))
        c.create_text(w - 18, 18, text="APPROVAL GATE: ACTIVE", fill=ORANGE, anchor="ne", font=("Consolas", 8))
        nodes = [(80, h - 60, "GOAL"), (w/2 - 45, h - 60, "PLAN"), (w - 80, h - 60, "VERIFY")]
        for x, y, text in nodes:
            c.create_rectangle(x-36, y-14, x+36, y+14, outline=CYAN_DARK)
            c.create_text(x, y, text=text, fill=MUTED, font=("Consolas", 8, "bold"))

    def _pulse(self):
        if self.root.winfo_exists():
            self.phase += 0.06
            self._draw()
            self.root.after(45, self._pulse)

    def _clock(self):
        if self.root.winfo_exists():
            self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
            self.root.after(500, self._clock)

    def _telemetry(self):
        if self.root.winfo_exists() and psutil:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\").percent
            self.telemetry.config(text=f"CPU  {cpu:>5.1f}%\nRAM  {ram:>5.1f}%\nDISK {disk:>5.1f}%")
            self.root.after(1200, self._telemetry)

    def run(self) -> None:
        self.root.mainloop()

    def set_state(self, state: str) -> None:
        self.state = state.upper()
        self.state_label.config(text=self.state, fg=RED if self.state in {"ERROR", "FALLO"} else CYAN)
        mapping = {"OBSERVANDO": 0, "ANALIZANDO": 1, "PENSANDO": 2, "PROCESANDO": 2, "OODA": 3, "EJECUTANDO": 3, "VERIFICANDO": 4}
        active = mapping.get(self.state)
        for i, item in enumerate(self.ooda):
            item.config(fg=CYAN if i == active else MUTED, text=("●" if i == active else "○") + "  " + item.cget("text").split("  ", 1)[-1])

    def update_provider(self) -> None:
        self.provider_label.config(text=f"CORE: {self.brain.provider.upper()}")

    def add_message(self, role: str, text: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {role:<8} {text}"
        self.history.append(line)
        self.stream.config(state="normal")
        self.stream.insert("end", line + "\n")
        self.stream.see("end")
        self.stream.config(state="disabled")

    def set_response(self, text: str) -> None:
        self.mission.config(text=text[:420])
        self.add_message("JARVIS", text)

    def set_mission(self, text: str) -> None:
        self.mission.config(text=text[:420])
        self.add_message("MISSION", text)

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.add_message("USER", text)
        self.set_state("ANALIZANDO")
        self.process_command(text)

    def _voice(self) -> None:
        self.set_state("ESCUCHANDO")
        try:
            text = self.voice.listen_for_command(seconds=7)
            if text:
                self.entry.delete(0, "end")
                self.entry.insert(0, text)
                self._send()
        except Exception as exc:
            self.add_message("VOICE", f"Error: {exc}")
            self.set_state("ERROR")

    def _quick(self, command: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, command)
        self._send()

    def _new_session(self) -> None:
        self.brain.reset_conversation()
        self.history.clear()
        self.stream.config(state="normal")
        self.stream.delete("1.0", "end")
        self.stream.config(state="disabled")
        self.mission.config(text="New mission context initialized.")
        self.set_state("STANDBY")

    def _close(self) -> None:
        try:
            self.shutdown_callback()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
