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

try:
    import ctypes
    if hasattr(ctypes, "windll"):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

BG = "#010409"
PANEL = "#040b12"
PANEL2 = "#07141d"
CYAN = "#54efff"
CYAN2 = "#159bb4"
DIM = "#0c4857"
GRID = "#061923"
WHITE = "#e8fbff"
MUTED = "#557581"
GREEN = "#62ffb0"
AMBER = "#ffc857"


class JarvisHUD:
    """HUD visual de JARVIS; un único loop de render y todas las actualizaciones Tk en el hilo principal."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None]) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.running = True
        self.listening = False
        self.activity = "SYSTEM READY"
        self.started = time.monotonic()
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // PERSONAL INTELLIGENCE SYSTEM")
        self.root.configure(bg=BG)
        self.root.minsize(1100, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self._build()
        self._render()
        self._status_tick()

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=BG, height=82)
        top.pack(fill="x", padx=28, pady=(16, 0))
        top.pack_propagate(False)
        tk.Label(top, text="J.A.R.V.I.S.", fg=WHITE, bg=BG, font=("Segoe UI", 29, "bold")).pack(side="left", pady=9)
        tk.Label(top, text=" // PERSONAL INTELLIGENCE SYSTEM", fg=DIM, bg=BG, font=("Consolas", 9, "bold")).pack(side="left", pady=20)
        status = tk.Frame(top, bg=BG)
        status.pack(side="right", pady=12)
        self.status_label = tk.Label(status, text="● ONLINE", fg=GREEN, bg=BG, font=("Consolas", 10, "bold"))
        self.status_label.pack(anchor="e")
        self.activity_label = tk.Label(status, text=self.activity, fg=MUTED, bg=BG, font=("Consolas", 8))
        self.activity_label.pack(anchor="e", pady=(3, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 22))
        body.grid_columnconfigure(0, weight=7)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)
        self._build_reactor(body)
        self._build_console(body)

    def _build_reactor(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=DIM)
        shell.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

    def _build_console(self, parent: tk.Frame) -> None:
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        brain = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=DIM)
        brain.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.provider = tk.Label(brain, text=self.brain.provider.upper(), fg=CYAN, bg=PANEL, font=("Consolas", 17, "bold"))
        self.provider.pack(side="left", padx=16, pady=14)
        self.model = tk.Label(brain, text="", fg=WHITE, bg=PANEL, font=("Consolas", 8))
        self.model.pack(side="right", padx=16, pady=19)

        self.activity_line = tk.Label(right, text="◈  NEURAL LINK  /  READY", fg=CYAN2, bg=BG, font=("Consolas", 8, "bold"))
        self.activity_line.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self.log = scrolledtext.ScrolledText(right, bg=PANEL, fg=WHITE, insertbackground=CYAN, selectbackground="#10323e", relief="flat", bd=0, font=("Consolas", 10), wrap="word", padx=16, pady=14, spacing1=2, spacing3=7)
        self.log.grid(row=2, column=0, sticky="nsew")
        for tag, color in (("system", MUTED), ("user", CYAN), ("jarvis", WHITE), ("voice", AMBER)):
            self.log.tag_configure(tag, foreground=color)
        self._log("SYSTEM", "NEURAL CORE ONLINE. AWAITING COMMAND.")

        bar = tk.Frame(right, bg=BG)
        bar.grid(row=3, column=0, sticky="ew", pady=(9, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(bar, bg=PANEL2, fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 11))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=13)
        self.entry.bind("<Return>", lambda _: self._send())
        self._button(bar, "SEND", self._send).grid(row=0, column=1, padx=(7, 0))
        self.mic = self._button(bar, "◉ MIC", self._voice)
        self.mic.grid(row=0, column=2, padx=(7, 0))

        telemetry = tk.Frame(right, bg=BG)
        telemetry.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        for i in range(4):
            telemetry.grid_columnconfigure(i, weight=1)
        self.metrics = []
        for i, name in enumerate(("CPU", "RAM", "GPU", "UPTIME")):
            box = tk.Frame(telemetry, bg=PANEL, highlightthickness=1, highlightbackground=DIM)
            box.grid(row=0, column=i, sticky="ew", padx=2)
            label = tk.Label(box, text=f"{name}\n--", fg=WHITE, bg=PANEL, font=("Consolas", 8, "bold"), pady=7)
            label.pack(fill="both", expand=True)
            self.metrics.append(label)
        tk.Label(right, text="LOCAL WHISPER  •  ELEVENLABS / LOCAL TTS  •  ONE AI BRAIN", fg="#31525e", bg=BG, font=("Consolas", 7)).grid(row=5, column=0, sticky="w", pady=(7, 0))

    def _button(self, parent: tk.Frame, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg="#092530", fg=CYAN, activebackground="#103b48", activeforeground=WHITE, relief="flat", bd=0, cursor="hand2", font=("Consolas", 9, "bold"), padx=16, pady=9)

    def _render(self) -> None:
        if not self.running:
            return
        c = self.canvas
        w = max(c.winfo_width(), 500)
        h = max(c.winfo_height(), 500)
        c.delete("all")
        cx, cy = w * 0.5, h * 0.49
        base = min(w, h) * 0.27
        t = time.monotonic()
        step = max(45, int(min(w, h) / 13))

        for x in range(0, w + step, step):
            c.create_line(x, 0, x, h, fill=GRID)
        for y in range(0, h + step, step):
            c.create_line(0, y, w, y, fill=GRID)

        m, b = 20, 28
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = m if sx > 0 else w - m
            y = m if sy > 0 else h - m
            c.create_line(x, y, x + sx * b, y, fill=DIM, width=2)
            c.create_line(x, y, x, y + sy * b, fill=DIM, width=2)

        pulse = 1 + 0.025 * math.sin(t * 3)
        rings = ((1.0, 8, 32, CYAN, 2), (0.80, -12, 24, CYAN2, 1), (0.62, 17, 20, DIM, 1))
        for factor, speed, count, outline, width in rings:
            r = base * factor * pulse
            for i in range(count):
                if (i + int(t * 2)) % (5 if count > 24 else 4) == 0:
                    continue
                start = i * (360 / count) + t * speed
                c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start, extent=360/count-4, style="arc", outline=outline, width=width)

        for i in range(72):
            a = math.radians(i * 5 + t * (14 if i % 2 else -7))
            r1 = base * 1.03
            r2 = r1 + (13 if i % 6 == 0 else 6)
            c.create_line(cx + math.cos(a)*r1, cy + math.sin(a)*r1, cx + math.cos(a)*r2, cy + math.sin(a)*r2, fill=CYAN if i % 6 == 0 else DIM, width=2 if i % 6 == 0 else 1)

        core = base * 0.29 * (1 + 0.05 * math.sin(t * 4))
        for factor, outline in ((1.7, DIM), (1.35, CYAN2), (1.0, CYAN)):
            r = core * factor
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=outline, width=2 if factor == 1.35 else 1)
        c.create_oval(cx-core*.72, cy-core*.72, cx+core*.72, cy+core*.72, fill="#0a2c36", outline=CYAN, width=2)
        c.create_oval(cx-core*.28, cy-core*.28, cx+core*.28, cy+core*.28, fill=CYAN, outline=WHITE, width=1)
        c.create_text(cx, cy-7, text="J.A.R.V.I.S.", fill=WHITE, font=("Segoe UI", max(16, int(20*base/205)), "bold"))
        c.create_text(cx, cy+20, text=self.activity, fill=CYAN, font=("Consolas", 9, "bold"))

        for title, value, rx, ry in (("NEURAL CORE", "ACTIVE", .07, .18), ("VOICE ARRAY", "READY", .73, .18), ("SYSTEM LINK", "SECURE", .07, .79), ("ACTION BUS", "STANDBY", .73, .79)):
            x, y = w*rx, h*ry
            c.create_text(x, y, text=title, anchor="w", fill=MUTED, font=("Consolas", 8, "bold"))
            c.create_text(x, y+16, text=value, anchor="w", fill=CYAN, font=("Consolas", 9, "bold"))

        self.root.after(40, self._render)

    def _status_tick(self) -> None:
        if not self.running:
            return
        try:
            if psutil:
                self.metrics[0].config(text=f"CPU\n{psutil.cpu_percent(None):.0f}%")
                self.metrics[1].config(text=f"RAM\n{psutil.virtual_memory().percent:.0f}%")
            self.metrics[2].config(text="GPU\nOK")
            elapsed = int(time.monotonic() - self.started)
            self.metrics[3].config(text=f"UPTIME\n{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}")
            provider = self.brain.provider.upper()
            self.provider.config(text=provider)
            self.model.config(text=self.brain.config.claude_model if provider == "CLAUDE" else self.brain.config.ollama_model)
        except Exception:
            pass
        self.root.after(1000, self._status_tick)

    def set_state(self, state: str) -> None:
        self.activity = state.upper()
        if self.running:
            self.root.after(0, self._state_ui)

    def _state_ui(self) -> None:
        if not self.running:
            return
        self.activity_label.config(text=self.activity)
        self.activity_line.config(text=f"◈  NEURAL LINK  /  {self.activity}")
        if "LISTEN" in self.activity:
            self.status_label.config(text="● LISTENING", fg=AMBER)
        elif "PROCESS" in self.activity or "THINK" in self.activity:
            self.status_label.config(text="● PROCESSING", fg=CYAN)
        elif "SPEAK" in self.activity:
            self.status_label.config(text="● SPEAKING", fg=GREEN)
        else:
            self.status_label.config(text="● ONLINE", fg=GREEN)

    def _log(self, who: str, text: str) -> None:
        tag = who.lower()
        self.log.insert("end", f"[{who}]  {text}\n\n", tag if tag in {"system", "user", "jarvis", "voice"} else "system")
        self.log.see("end")

    def add_message(self, who: str, text: str) -> None:
        if self.running:
            self.root.after(0, self._log, who, text)

    def _send(self) -> None:
        command = self.entry.get().strip()
        if not command:
            return
        self.entry.delete(0, "end")
        self._log("USER", command)
        self.set_state("PROCESSING COMMAND")
        threading.Thread(target=self.process_command, args=(command,), daemon=True).start()

    def _voice(self) -> None:
        if self.listening:
            return
        self.listening = True
        self.mic.config(text="◉ LISTENING", fg=WHITE)
        self._log("VOICE", "MIC ARRAY ACTIVE // LISTENING")
        self.set_state("LISTENING")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.add_message("USER", command)
                self.set_state("PROCESSING COMMAND")
                self.process_command(command)
            else:
                self.add_message("VOICE", "No activation word detected.")
        except Exception as exc:
            self.add_message("VOICE", f"Error: {exc}")
        finally:
            if self.running:
                self.root.after(0, self._voice_idle)

    def _voice_idle(self) -> None:
        self.listening = False
        self.mic.config(text="◉ MIC", fg=CYAN)
        self.set_state("SYSTEM READY")

    def set_response(self, text: str) -> None:
        self.set_state("SPEAKING")
        self.add_message("JARVIS", text)
        self.root.after(max(1000, min(4500, len(text) * 30)), lambda: self.set_state("SYSTEM READY"))

    def _close(self) -> None:
        self.running = False
        self.shutdown_callback()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()
