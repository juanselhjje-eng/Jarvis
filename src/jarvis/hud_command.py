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

BG = "#02060b"
PANEL = "#061018"
PANEL2 = "#091923"
LINE = "#123541"
CYAN = "#73e8ff"
CYAN2 = "#1a8fa8"
WHITE = "#e8fbff"
MUTED = "#58747d"
GREEN = "#63f6b0"
AMBER = "#ffd166"
RED = "#ff5877"


class JarvisHUD:
    """Native Windows HUD with a denser, cinematic command-center layout."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.running = True
        self.state = "STANDBY"
        self.started = time.monotonic()
        self.activity: list[tuple[str, str]] = []
        self._phase = 0.0
        self._build_window()
        self._build()
        self._animate()
        self._clock()
        self._telemetry()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // MISSION CONTROL")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 720)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def panel(self, parent, bg=PANEL):
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def label(self, parent, text, size=9, fg=WHITE, bg=PANEL, bold=False):
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=("Segoe UI", size, "bold" if bold else "normal"))

    def section(self, parent, title, right=""):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(9, 6))
        self.label(row, title, 8, CYAN, PANEL, True).pack(side="left")
        if right:
            self.label(row, right, 7, MUTED, PANEL, True).pack(side="right")
        tk.Frame(parent, bg=LINE, height=1).pack(fill="x", padx=12)

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 8))
        self.label(header, "J.A.R.V.I.S.", 25, WHITE, BG, True).pack(side="left")
        self.label(header, "MISSION CONTROL / MK-VIII", 9, CYAN2, BG, True).pack(side="left", padx=16, pady=(9, 0))
        right = tk.Frame(header, bg=BG)
        right.pack(side="right")
        self.clock_label = self.label(right, "--:--:--", 12, WHITE, BG, True)
        self.clock_label.pack(side="left", padx=14)
        self.link = self.label(right, "● CORE ONLINE", 8, GREEN, BG, True)
        self.link.pack(side="left")
        tk.Frame(self.root, bg=LINE, height=1).pack(fill="x", padx=24)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=12)
        body.grid_columnconfigure(0, weight=2, minsize=235)
        body.grid_columnconfigure(1, weight=5, minsize=500)
        body.grid_columnconfigure(2, weight=2, minsize=250)
        body.grid_rowconfigure(0, weight=1)

        self._left(body)
        self._center(body)
        self._right(body)

    def _left(self, body):
        col = tk.Frame(body, bg=BG)
        col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        p = self.panel(col); p.pack(fill="x", pady=(0, 8))
        self.section(p, "CORE IDENTITY", "ONE AGENT")
        self.label(p, "J.A.R.V.I.S.", 18, WHITE, PANEL, True).pack(anchor="w", padx=13, pady=(9, 0))
        self.label(p, "JUST A RATHER VERY INTELLIGENT SYSTEM", 7, MUTED, PANEL).pack(anchor="w", padx=13, pady=(2, 12))

        p = self.panel(col); p.pack(fill="x", pady=(0, 8))
        self.section(p, "AI CORE", "ACTIVE")
        self.provider_label = self.label(p, self.brain.provider.upper(), 16, CYAN, PANEL, True)
        self.provider_label.pack(anchor="w", padx=13, pady=(8, 0))
        model = getattr(self.brain.config, "gemini_model", "gemini") if self.brain.provider == "gemini" else getattr(self.brain.config, "ollama_model", "ollama")
        self.model_label = self.label(p, str(model), 8, MUTED, PANEL, True)
        self.model_label.pack(anchor="w", padx=13, pady=(0, 7))
        self.state_label = self.label(p, "● STANDBY", 8, GREEN, PANEL, True)
        self.state_label.pack(anchor="w", padx=13, pady=(0, 13))

        p = self.panel(col); p.pack(fill="x", pady=(0, 8))
        self.section(p, "SYSTEM TELEMETRY", "LIVE")
        self.telemetry_labels = {}
        for key in ("CPU", "RAM", "DISK", "TEMP"):
            row = tk.Frame(p, bg=PANEL2); row.pack(fill="x", padx=10, pady=2)
            l = self.label(row, f"{key:<5} --", 8, WHITE, PANEL2, True); l.pack(fill="x", padx=8, pady=6)
            self.telemetry_labels[key] = l

        p = self.panel(col); p.pack(fill="x")
        self.section(p, "QUICK ACTIONS", "READY")
        for text, fn in (("LISTEN", self._voice), ("NEW SESSION", self._clear_chat), ("SHUT DOWN", self._close)):
            tk.Button(p, text=text, command=fn, bg=PANEL2, fg=CYAN, activebackground="#103845", activeforeground=WHITE, relief="flat", bd=0, font=("Consolas", 8, "bold"), pady=8, cursor="hand2").pack(fill="x", padx=10, pady=3)
        self.label(p, "MIC LOCAL  •  CAMERA OFF\nMEMORY LOCAL  •  TOOLS VERIFIED", 7, MUTED, PANEL).pack(anchor="w", padx=13, pady=10)

    def _center(self, body):
        col = tk.Frame(body, bg=BG)
        col.grid(row=0, column=1, sticky="nsew", padx=4)
        col.grid_rowconfigure(0, weight=5)
        col.grid_rowconfigure(1, weight=3)
        col.grid_columnconfigure(0, weight=1)

        p = self.panel(col); p.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.core_canvas = tk.Canvas(p, bg=PANEL, highlightthickness=0)
        self.core_canvas.pack(fill="both", expand=True)

        p = self.panel(col); p.grid(row=1, column=0, sticky="nsew")
        p.grid_rowconfigure(1, weight=1); p.grid_columnconfigure(0, weight=1)
        self.section(p, "NEURAL CONSOLE", "SECURE CHANNEL")
        self.log = scrolledtext.ScrolledText(p, bg=PANEL, fg=WHITE, insertbackground=CYAN, selectbackground="#123b47", relief="flat", bd=0, font=("Segoe UI", 9), wrap="word", padx=12, pady=8)
        self.log.grid(row=1, column=0, sticky="nsew", padx=8)
        for tag, color in (("system", MUTED), ("user", CYAN), ("jarvis", WHITE), ("voice", AMBER)):
            self.log.tag_configure(tag, foreground=color)
        self._log("SYSTEM", "MISSION CONTROL INITIALIZED // AWAITING OBJECTIVE")

        compose = tk.Frame(p, bg=PANEL); compose.grid(row=2, column=0, sticky="ew", padx=9, pady=9); compose.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(compose, bg=PANEL2, fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=10); self.entry.bind("<Return>", lambda _e: self._send())
        self.entry.insert(0, "Escribe una orden para JARVIS…"); self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self._placeholder)
        tk.Button(compose, text="EXECUTE", command=self._send, bg="#0b3540", fg=CYAN, activebackground="#125363", relief="flat", bd=0, font=("Consolas", 8, "bold"), padx=14, pady=9).grid(row=0, column=1, padx=(7, 0))
        tk.Button(compose, text="MIC", command=self._voice, bg=PANEL2, fg=WHITE, activebackground="#103845", relief="flat", bd=0, font=("Consolas", 8, "bold"), padx=12, pady=9).grid(row=0, column=2, padx=(5, 0))

    def _right(self, body):
        col = tk.Frame(body, bg=BG); col.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        p = self.panel(col); p.pack(fill="x", pady=(0, 8)); self.section(p, "MISSION", "REAL TIME")
        self.mission_label = self.label(p, "NO ACTIVE OBJECTIVE", 9, WHITE, PANEL, True); self.mission_label.pack(anchor="w", padx=13, pady=(9, 3))
        self.phase_label = self.label(p, "STANDBY / PHASE 00", 8, GREEN, PANEL, True); self.phase_label.pack(anchor="w", padx=13, pady=(0, 12))

        p = self.panel(col); p.pack(fill="x", pady=(0, 8)); self.section(p, "NEURAL ACTIVITY", "LIVE")
        self.activity_box = tk.Text(p, height=9, bg=PANEL, fg=MUTED, relief="flat", bd=0, font=("Consolas", 7), state="disabled", padx=10, pady=6)
        self.activity_box.pack(fill="both", padx=7, pady=7)

        p = self.panel(col); p.pack(fill="both", expand=True, pady=(0, 8)); self.section(p, "EVIDENCE", "INTELLIGENCE")
        self.evidence_title = self.label(p, "NO ACTIVE INVESTIGATION", 8, WHITE, PANEL, True); self.evidence_title.pack(anchor="w", padx=13, pady=(9, 3))
        self.evidence_status = self.label(p, "STATUS / IDLE", 7, MUTED, PANEL, True); self.evidence_status.pack(anchor="w", padx=13)
        self.evidence_findings = self.label(p, "FINDINGS 0   SOURCES 0", 8, CYAN, PANEL, True); self.evidence_findings.pack(anchor="w", padx=13, pady=5)
        self.label(p, "EXECUTION PIPELINE\nINTENT → PLAN → EXECUTE → VERIFY", 7, MUTED, PANEL).pack(anchor="w", padx=13, pady=12)

        p = self.panel(col); p.pack(fill="x"); self.section(p, "LINKS", "ENCRYPTED")
        self.link_label = self.label(p, "GEMINI  •  OLLAMA  •  WHISPER  •  LOCAL MEMORY", 7, CYAN2, PANEL, True); self.link_label.pack(anchor="w", padx=13, pady=(5, 12))

    def _placeholder(self, _event=None):
        if self.entry.get().startswith("Escribe una orden"):
            self.entry.delete(0, "end"); self.entry.config(fg=WHITE)

    def _send(self):
        text = self.entry.get().strip()
        if not text or text.startswith("Escribe una orden"):
            return
        self.entry.delete(0, "end"); self._log("USER", text); self.set_state("THINKING"); self._set_mission(text)
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _voice(self):
        self._log("VOICE", "LISTENING FOR COMMAND…"); self.set_state("LISTENING")
        threading.Thread(target=self._voice_worker, daemon=True, name="jarvis-manual-voice").start()

    def _voice_worker(self):
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.root.after(0, lambda: self._log("USER", command)); self.root.after(0, lambda: self._set_mission(command)); self.process_command(command)
            else:
                self.root.after(0, lambda: self.set_state("STANDBY"))
        except Exception as exc:
            self.root.after(0, lambda: self._log("VOICE", f"ERROR: {exc}")); self.root.after(0, lambda: self.set_state("STANDBY"))

    def _clear_chat(self):
        self.brain.reset_conversation(); self._clear_log(); self._log("SYSTEM", "SESSION RESET // MEMORY BUFFER CLEARED")

    def _clear_log(self):
        self.log.delete("1.0", "end")

    def _set_mission(self, text):
        self.mission_label.config(text=text[:90].upper()); self.phase_label.config(text="ACTIVE / PHASE 01", fg=CYAN)

    def _log(self, role, text):
        self.log.insert("end", f"[{role}]  {text}\n\n", role.lower() if role.lower() in {"system", "user", "jarvis", "voice"} else "system"); self.log.see("end")
        self.activity.append((role, text[:72])); self.activity = self.activity[-8:]
        self._refresh_activity()

    def add_message(self, role, text):
        self.root.after(0, lambda: self._log(role, text))

    def set_response(self, text):
        self.root.after(0, lambda: (self._log("JARVIS", text), self.set_state("SPEAKING")))

    def set_state(self, state):
        self.state = state.upper()
        if hasattr(self, "state_label"):
            color = GREEN if self.state in {"STANDBY", "CALMADO"} else AMBER if self.state in {"LISTENING", "ESCUCHANDO"} else CYAN
            self.state_label.config(text=f"● {self.state}", fg=color)

    def _refresh_activity(self):
        if not hasattr(self, "activity_box"): return
        self.activity_box.config(state="normal"); self.activity_box.delete("1.0", "end")
        for role, text in self.activity[-8:]: self.activity_box.insert("end", f"{role:<7} {text}\n")
        self.activity_box.config(state="disabled")

    def _animate(self):
        if not self.running: return
        self._phase += 0.035
        c = self.core_canvas; w = max(c.winfo_width(), 500); h = max(c.winfo_height(), 300); cx, cy = w / 2, h / 2; base = min(w, h) * 0.17
        c.delete("all")
        c.create_text(18, 16, text="NEURAL CORE / LIVE", anchor="nw", fill=MUTED, font=("Consolas", 7, "bold"))
        for i, scale in enumerate((1.9, 1.55, 1.25, 0.95, 0.68)):
            r = base * scale + math.sin(self._phase * (1 + i * .15)) * 3
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=CYAN2 if i % 2 else LINE, width=2 if i < 3 else 1)
        for i in range(12):
            a = self._phase * (1 if i % 2 else -0.7) + i * math.pi / 6
            rr = base * 1.9
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            c.create_oval(x-3, y-3, x+3, y+3, fill=CYAN, outline="")
        pulse = base * (0.48 + 0.06 * math.sin(self._phase * 3))
        c.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse, fill="#0a3440", outline=CYAN, width=2)
        c.create_oval(cx-pulse*.45, cy-pulse*.45, cx+pulse*.45, cy+pulse*.45, fill="#09222b", outline=WHITE, width=1)
        c.create_text(cx, cy-8, text="J.A.R.V.I.S.", fill=WHITE, font=("Segoe UI", 14, "bold"))
        c.create_text(cx, cy+15, text=self.state, fill=CYAN, font=("Consolas", 8, "bold"))
        c.create_text(cx, cy+base*2.25, text="VOICE  /  TEXT  /  TOOLS  /  MEMORY", fill=MUTED, font=("Consolas", 7, "bold"))
        self.root.after(35, self._animate)

    def _clock(self):
        if self.running:
            self.clock_label.config(text=time.strftime("%H:%M:%S")); self.root.after(500, self._clock)

    def _telemetry(self):
        if self.running:
            try:
                if psutil:
                    self.telemetry_labels["CPU"].config(text=f"CPU   {psutil.cpu_percent():5.1f}%")
                    self.telemetry_labels["RAM"].config(text=f"RAM   {psutil.virtual_memory().percent:5.1f}%")
                    self.telemetry_labels["DISK"].config(text=f"DISK  {psutil.disk_usage('C:/').percent:5.1f}%")
                    self.telemetry_labels["TEMP"].config(text="TEMP  --  °C")
            except Exception: pass
            self.root.after(1200, self._telemetry)

    def update_provider(self):
        self.provider_label.config(text=self.brain.provider.upper())
        model = getattr(self.brain.config, "gemini_model", "gemini") if self.brain.provider == "gemini" else getattr(self.brain.config, "ollama_model", "ollama")
        self.model_label.config(text=str(model))

    def run(self): self.root.mainloop()

    def _close(self):
        if not self.running: return
        self.running = False
        try: self.shutdown_callback()
        finally: self.root.after(0, self.root.destroy)
