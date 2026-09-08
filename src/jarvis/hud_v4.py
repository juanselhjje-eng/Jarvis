from __future__ import annotations

import math
import tkinter as tk
from datetime import datetime
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


BG = "#03070a"
PANEL = "#071116"
PANEL_2 = "#0a1820"
LINE = "#12303a"
CYAN = "#22e6ff"
CYAN_DIM = "#0c7482"
AMBER = "#ffb84d"
GREEN = "#43f0a5"
RED = "#ff5d73"
WHITE = "#eaf8fb"
MUTED = "#71858d"


class JarvisHUDv4:
    """HUD nativo Tkinter: reactor hexagonal, consola, OODA y Mission Control."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.state = "STANDBY"
        self.phase = 0.0
        self.messages: list[tuple[str, str]] = []
        self._build_window()
        self._build_ui()
        self._tick()
        self._clock()
        self._telemetry()

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // COMPUTER USE MISSION CONTROL")
        self.root.configure(bg=BG)
        self.root.minsize(1250, 760)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<F2>", lambda _e: self.entry.focus_set())
        self.root.bind("<Control-Shift-J>", lambda _e: self.entry.focus_set())

    def _label(self, parent, text, size=9, fg=WHITE, bold=False, bg=None, anchor="w"):
        return tk.Label(parent, text=text, bg=bg or parent.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor=anchor)

    def _button(self, parent, text, command, width=None):
        return tk.Button(parent, text=text, command=command, width=width, bg=PANEL, fg=WHITE, activebackground="#12313a", activeforeground=CYAN, relief="flat", bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=7)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root, bg="#020507", height=48, highlightthickness=1, highlightbackground=LINE)
        top.pack(fill="x")
        top.pack_propagate(False)
        self._label(top, "J.A.R.V.I.S.", 13, CYAN, True, top["bg"]).pack(side="left", padx=18)
        self._label(top, "COMPUTER USE / OODA CONTROL", 8, MUTED, True, top["bg"]).pack(side="left", padx=8)
        self.clock_label = self._label(top, "--:--:--", 9, WHITE, True, top["bg"])
        self.clock_label.pack(side="right", padx=18)
        self.core_label = self._label(top, "● CORE ONLINE", 8, GREEN, True, top["bg"])
        self.core_label.pack(side="right", padx=10)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, minsize=235)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=285)
        body.grid_rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_center(body)
        self._build_right(body)
        self._build_composer()

    def _panel(self, parent, row=0, column=0, padx=0, pady=0, sticky="nsew"):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        frame.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
        return frame

    def _build_left(self, body) -> None:
        left = self._panel(body, padx=(0, 7))
        self._label(left, "SYSTEM MAP", 9, CYAN, True, left["bg"]).pack(anchor="w", padx=14, pady=(15, 8))
        items = [
            ("CORE AGENT", "Gemini / Ollama"),
            ("VISION", "Screenshot on demand"),
            ("INPUT", "Keyboard / voice"),
            ("OS CONTROL", "Windows visible UI"),
            ("BROWSER", "Navigation + search"),
            ("TEAMS", "Personal / educativo"),
            ("MEMORY", "Local persistent"),
        ]
        for name, detail in items:
            row = tk.Frame(left, bg=left["bg"])
            row.pack(fill="x", padx=12, pady=4)
            self._label(row, "◆", 8, CYAN_DIM, True, row["bg"]).pack(side="left")
            text = tk.Frame(row, bg=row["bg"])
            text.pack(side="left", padx=8)
            self._label(text, name, 8, WHITE, True, text["bg"]).pack(anchor="w")
            self._label(text, detail, 7, MUTED, False, text["bg"]).pack(anchor="w")
        self._label(left, "QUICK COMMANDS", 8, CYAN, True, left["bg"]).pack(anchor="w", padx=14, pady=(18, 6))
        for label, command in (("Revisar PC", "revisa mi pc"), ("Abrir Teams", "abre teams personal"), ("Ver pantalla", "mira la pantalla"), ("Buscar tecnología", "busca tecnología")):
            self._button(left, label, lambda c=command: self._quick(c)).pack(fill="x", padx=12, pady=3)

    def _build_center(self, body) -> None:
        center = self._panel(body, padx=7)
        center.grid_rowconfigure(1, weight=1)
        center.grid_columnconfigure(0, weight=1)
        header = tk.Frame(center, bg=center["bg"], height=46)
        header.grid(row=0, column=0, sticky="ew")
        self._label(header, "VISUAL PERCEPTION / CORE", 9, WHITE, True, header["bg"]).pack(side="left", padx=16, pady=12)
        self.state_label = self._label(header, self.state, 8, CYAN, True, header["bg"])
        self.state_label.pack(side="right", padx=16)

        canvas_frame = tk.Frame(center, bg="#020608")
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg="#020608", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self._label(center, "ACTIVITY STREAM", 8, CYAN, True, center["bg"]).grid(row=2, column=0, sticky="w", padx=16, pady=(4, 3))
        self.activity = tk.Text(center, height=8, bg="#020609", fg="#9eb8bf", insertbackground=CYAN, relief="flat", bd=0, font=("Consolas", 8), state="disabled")
        self.activity.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _build_right(self, body) -> None:
        right = self._panel(body, padx=(7, 0))
        self._label(right, "MISSION CONTROL", 10, WHITE, True, right["bg"]).pack(anchor="w", padx=14, pady=(15, 2))
        self._label(right, "Perceive → Orient → Decide → Act", 7, MUTED, False, right["bg"]).pack(anchor="w", padx=14, pady=(0, 12))
        self.ooda = []
        for name in ("PERCEIVE", "ORIENT", "DECIDE", "ACT"):
            label = self._label(right, f"○  {name}", 8, MUTED, True, right["bg"])
            label.pack(anchor="w", padx=16, pady=3)
            self.ooda.append(label)
        self._label(right, "AUTONOMY", 8, CYAN, True, right["bg"]).pack(anchor="w", padx=14, pady=(18, 5))
        self.autonomy = self._label(right, "READY / HUMAN GATE", 9, AMBER, True, right["bg"])
        self.autonomy.pack(anchor="w", padx=14)
        self._label(right, "TELEMETRY", 8, CYAN, True, right["bg"]).pack(anchor="w", padx=14, pady=(18, 5))
        self.telemetry_label = self._label(right, "CPU --\nRAM --\nDISK --", 8, MUTED, False, right["bg"])
        self.telemetry_label.pack(anchor="w", padx=14)
        self._label(right, "EVIDENCE", 8, CYAN, True, right["bg"]).pack(anchor="w", padx=14, pady=(18, 5))
        self.evidence_label = self._label(right, "No hay misión activa.", 8, MUTED, False, right["bg"])
        self.evidence_label.pack(anchor="w", padx=14)
        self._button(right, "NUEVA SESIÓN", self._new_chat).pack(fill="x", padx=12, pady=(22, 4))
        self._button(right, "CERRAR JARVIS", self._close).pack(fill="x", padx=12, pady=4)

    def _build_composer(self) -> None:
        bar = tk.Frame(self.root, bg="#020507", highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(bar, bg="#081117", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10, ipady=9)
        self.entry.bind("<Return>", lambda _e: self._send())
        self._button(bar, "MIC", self._voice, width=6).pack(side="left", padx=3)
        self._button(bar, "ENVIAR", self._send, width=8).pack(side="left", padx=(3, 10))

    def _draw_core(self) -> None:
        c = self.canvas
        w = max(c.winfo_width(), 600)
        h = max(c.winfo_height(), 420)
        c.delete("all")
        for x in range(0, w, 32):
            c.create_line(x, 0, x, h, fill="#061017")
        for y in range(0, h, 32):
            c.create_line(0, y, w, y, fill="#061017")
        cx, cy = w / 2, h / 2
        pulse = 4 * math.sin(self.phase * 1.7)
        for radius in (145, 118, 88):
            r = radius + pulse
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#0b3944", width=1)
        # Hexagonal reactor instead of the old flat circle.
        for scale, color, width in ((1.0, CYAN_DIM, 2), (0.68, CYAN, 2), (0.38, WHITE, 1)):
            r = 105 * scale + pulse
            pts = []
            for i in range(6):
                a = math.radians(60 * i - 30 + self.phase * (2 if scale < 1 else -1))
                pts.extend((cx + r * math.cos(a), cy + r * math.sin(a)))
            c.create_polygon(*pts, outline=color, fill="", width=width)
        for i in range(12):
            a = math.radians(i * 30 + self.phase * 4)
            x1, y1 = cx + 125 * math.cos(a), cy + 125 * math.sin(a)
            x2, y2 = cx + 165 * math.cos(a), cy + 165 * math.sin(a)
            c.create_line(x1, y1, x2, y2, fill="#0b5967", width=2)
        c.create_text(cx, cy - 12, text="CORE AGENT", fill=WHITE, font=("Segoe UI", 13, "bold"))
        c.create_text(cx, cy + 12, text=self.state, fill=CYAN, font=("Consolas", 9, "bold"))
        c.create_text(cx, cy + 170, text="VISION  •  OODA  •  DESKTOP CONTROL", fill=MUTED, font=("Consolas", 8))
        c.create_text(18, 18, text="SCREEN OBSERVATION: ON DEMAND", fill=CYAN_DIM, anchor="nw", font=("Consolas", 8))
        c.create_text(w - 18, 18, text="HUMAN APPROVAL: REQUIRED FOR EXTERNAL ACTIONS", fill=AMBER, anchor="ne", font=("Consolas", 8))

    def _tick(self) -> None:
        if not self.running:
            return
        self.phase += 0.07
        self._draw_core()
        self.root.after(45, self._tick)

    def _clock(self) -> None:
        if not self.running:
            return
        self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.root.after(500, self._clock)

    def _telemetry(self) -> None:
        if not self.running:
            return
        if psutil:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("C:\\").percent
            self.telemetry_label.config(text=f"CPU  {cpu:>5.1f}%\nRAM  {ram:>5.1f}%\nDISK {disk:>5.1f}%")
        self.root.after(1500, self._telemetry)

    def set_state(self, state: str) -> None:
        self.state = state.upper()
        if hasattr(self, "state_label"):
            self.state_label.config(text=self.state, fg=CYAN if self.state not in {"ERROR", "FALLO"} else RED)
        self._mark_ooda()

    def _mark_ooda(self) -> None:
        mapping = {"OBSERVANDO": 0, "ANALIZANDO": 1, "PENSANDO": 2, "PROCESANDO": 2, "EJECUTANDO": 3, "VERIFICANDO": 1, "ESCUCHANDO": 0}
        active = mapping.get(self.state)
        for index, label in enumerate(self.ooda):
            label.config(fg=CYAN if index == active else MUTED, text=("●" if index == active else "○") + "  " + label.cget("text").split("  ", 1)[-1])

    def add_message(self, role: str, text: str) -> None:
        self.messages.append((role, text))
        if hasattr(self, "activity"):
            self.activity.config(state="normal")
            self.activity.insert("end", f"[{role}] {text}\n")
            self.activity.see("end")
            self.activity.config(state="disabled")

    def set_response(self, text: str) -> None:
        self.add_message("JARVIS", text)
        self.set_state("LISTO")

    def update_provider(self) -> None:
        self.core_label.config(text=f"● CORE {self.brain.provider.upper()}")

    def show_alert(self, text: str, _color: str = AMBER) -> None:
        self.add_message("ALERT", text)

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.add_message("TÚ", text)
        self.set_state("ANALIZANDO")
        self.process_command(text)

    def _quick(self, command: str) -> None:
        self.add_message("QUICK", command)
        self.process_command(command)

    def _voice(self) -> None:
        self.add_message("VOICE", "Escuchando...")
        self.set_state("ESCUCHANDO")
        command = self.voice.listen_for_command(seconds=5)
        if command:
            self.add_message("TÚ", command)
            self.process_command(command)
        else:
            self.set_state("LISTO")

    def _new_chat(self) -> None:
        self.brain.reset_conversation()
        self.messages.clear()
        self.activity.config(state="normal")
        self.activity.delete("1.0", "end")
        self.activity.config(state="disabled")
        self.add_message("SYSTEM", "Sesión reiniciada.")

    def run(self) -> None:
        self.root.mainloop()

    def _close(self) -> None:
        self.running = False
        try:
            self.shutdown_callback()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
