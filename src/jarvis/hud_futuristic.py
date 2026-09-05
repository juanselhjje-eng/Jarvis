from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
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
    """High-DPI cinematic HUD. Visual layer only; JarvisBrain remains the sole AI agent."""

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
        self.root.minsize(1200, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1600x950")

        self._build()
        self._tick()
        self._status_tick()

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=BG, height=86)
        top.pack(fill="x", padx=34, pady=(20, 0))
        top.pack_propagate(False)
        tk.Label(top, text="J.A.R.V.I.S.", fg=WHITE, bg=BG, font=("Segoe UI", 30, "bold")).pack(side="left", pady=10)
        tk.Label(top, text="  //  PERSONAL INTELLIGENCE SYSTEM", fg=DIM, bg=BG,
                 font=("Consolas", 9, "bold")).pack(side="left", pady=20)
        status = tk.Frame(top, bg=BG)
        status.pack(side="right", pady=13)
        self.status_label = tk.Label(status, text="● ONLINE", fg=GREEN, bg=BG,
                                     font=("Consolas", 10, "bold"))
        self.status_label.pack(anchor="e")
        self.activity_label = tk.Label(status, text="SYSTEM READY", fg=MUTED, bg=BG,
                                       font=("Consolas", 8))
        self.activity_label.pack(anchor="e", pady=(3, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=34, pady=(0, 24))
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
        self.canvas.bind("<Configure>", lambda _: self._draw())

    def _build_console(self, parent: tk.Frame) -> None:
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        brain = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=DIM)
        brain.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.provider = tk.Label(brain, text="OLLAMA", fg=CYAN, bg=PANEL,
                                 font=("Consolas", 18, "bold"))
        self.provider.pack(side="left", padx=18, pady=15)
        self.model = tk.Label(brain, text="", fg=WHITE, bg=PANEL, font=("Consolas", 8))
        self.model.pack(side="right", padx=18, pady=20)

        activity = tk.Frame(right, bg=BG)
        activity.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.activity_line = tk.Label(activity, text="◈  NEURAL LINK  /  READY", fg=CYAN2, bg=BG,
                                      font=("Consolas", 8, "bold"))
        self.activity_line.pack(anchor="w")

        self.log = scrolledtext.ScrolledText(right, bg=PANEL, fg=WHITE, insertbackground=CYAN,
                                             selectbackground="#10323e", relief="flat", bd=0,
                                             font=("Consolas", 10), wrap="word", padx=18, pady=16,
                                             spacing1=2, spacing3=8)
        self.log.grid(row=2, column=0, sticky="nsew")
        self.log.tag_configure("system", foreground=MUTED)
        self.log.tag_configure("user", foreground=CYAN)
        self.log.tag_configure("jarvis", foreground=WHITE)
        self.log.tag_configure("voice", foreground=AMBER)
        self._log("SYSTEM", "NEURAL CORE ONLINE. AWAITING COMMAND.")

        bar = tk.Frame(right, bg=BG)
        bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(bar, bg=PANEL2, fg=WHITE, insertbackground=CYAN,
                              relief="flat", bd=0, font=("Segoe UI", 12))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=14)
        self.entry.bind("<Return>", lambda _: self._send())
        self.send = self._button(bar, "SEND", self._send)
        self.send.grid(row=0, column=1, padx=(8, 0))
        self.mic = self._button(bar, "◉  MIC", self._voice)
        self.mic.grid(row=0, column=2, padx=(8, 0))

        telemetry = tk.Frame(right, bg=BG)
        telemetry.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        for i in range(4):
            telemetry.grid_columnconfigure(i, weight=1)
        self.metrics = []
        for i, name in enumerate(("CPU", "RAM", "GPU", "UPTIME")):
            box = tk.Frame(telemetry, bg=PANEL, highlightthickness=1, highlightbackground=DIM)
            box.grid(row=0, column=i, sticky="ew", padx=3)
            label = tk.Label(box, text=f"{name}\n--", fg=WHITE, bg=PANEL,
                             font=("Consolas", 8, "bold"), pady=8)
            label.pack(fill="both", expand=True)
            self.metrics.append(label)

        tk.Label(right, text="LOCAL WHISPER  •  ELEVENLABS TTS  •  ONE AI BRAIN",
                 fg="#31525e", bg=BG, font=("Consolas", 7)).grid(row=5, column=0, sticky="w", pady=(8, 0))

    def _button(self, parent: tk.Frame, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg="#092530", fg=CYAN,
                         activebackground="#103b48", activeforeground=WHITE, relief="flat", bd=0,
                         cursor="hand2", font=("Consolas", 9, "bold"), padx=18, pady=10)

    def _draw(self) -> None:
        if not self.running:
            return
        c = self.canvas
        w, h = max(c.winfo_width(), 500), max(c.winfo_height(), 500)
        c.delete("all")
        cx, cy = w * 0.50, h * 0.49
        scale = min(w, h) / 760
        step = max(42, int(52 * scale))

        for x in range(0, w + step, step):
            c.create_line(x, 0, x, h, fill=GRID)
        for y in range(0, h + step, step):
            c.create_line(0, y, w, y, fill=GRID)

        # HUD frame corners.
        m, b = 22, 30
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = m if sx > 0 else w - m
            y = m if sy > 0 else h - m
            c.create_line(x, y, x + sx*b, y, fill=DIM, width=2)
            c.create_line(x, y, x, y + sy*b, fill=DIM, width=2)

        t = time.monotonic()
        base = min(w, h) * 0.27
        pulse = 1 + math.sin(t * 3) * 0.035

        # Large rotating rings.
        for ring, factor, speed, color in ((0, 1.0, 8, CYAN), (1, .82, -13, CYAN2), (2, .64, 17, DIM)):
            r = base * factor * pulse
            for seg in range(24 if ring else 32):
                if (seg + int(t * 2)) % (5 if ring != 1 else 7) == 0:
                    continue
                start = seg * (360 / (24 if ring else 32)) + t * speed
                c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start,
                             extent=(360 / (24 if ring else 32)) - 3,
                             style="arc", outline=color, width=2 if ring == 0 else 1)

        # Fine radial ticks.
        for i in range(72):
            a = math.radians(i * 5 + t * (18 if i % 2 else -9))
            r1 = base * 1.04
            r2 = r1 + (14 if i % 6 == 0 else 7)
            c.create_line(cx + math.cos(a)*r1, cy + math.sin(a)*r1,
                          cx + math.cos(a)*r2, cy + math.sin(a)*r2,
                          fill=CYAN if i % 6 == 0 else DIM,
                          width=2 if i % 6 == 0 else 1)

        # Reactor glow layers.
        core = base * .30 * (1 + .06 * math.sin(t * 4))
        for factor, outline in ((1.65, DIM), (1.32, CYAN2), (1.0, CYAN)):
            r = core * factor
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=outline, width=2 if factor == 1.32 else 1)
        c.create_oval(cx-core*.72, cy-core*.72, cx+core*.72, cy+core*.72,
                      fill="#0a2c36", outline=CYAN, width=2)
        c.create_oval(cx-core*.28, cy-core*.28, cx+core*.28, cy+core*.28,
                      fill=CYAN, outline=WHITE, width=1)
        c.create_text(cx, cy - 7, text="J.A.R.V.I.S.", fill=WHITE,
                      font=("Segoe UI", max(16, int(21*scale)), "bold"))
        c.create_text(cx, cy + 21, text=self.activity, fill=CYAN,
                      font=("Consolas", max(8, int(9*scale)), "bold"))

        # Data callouts.
        callouts = (("NEURAL CORE", "ACTIVE", .08, .20),
                    ("VOICE ARRAY", "READY", .72, .20),
                    ("SYSTEM LINK", "SECURE", .08, .77),
                    ("ACTION BUS", "STANDBY", .72, .77))
        for title, value, rx, ry in callouts:
            x, y = w * rx, h * ry
            c.create_text(x, y, text=title, anchor="w", fill=MUTED, font=("Consolas", 8, "bold"))
            c.create_text(x, y + 17, text=value, anchor="w", fill=CYAN, font=("Consolas", 9, "bold"))

        self.root.after(33, self._draw)

    def _status_tick(self) -> None:
        if not self.running:
            return
        try:
            if psutil:
                self.metrics[0].config(text=f"CPU\n{psutil.cpu_percent(None):.0f}%")
                self.metrics[1].config(text=f"RAM\n{psutil.virtual_memory().percent:.0f}%")
            elapsed = int(time.monotonic() - self.started)
            self.metrics[3].config(text=f"UPTIME\n{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}")
            provider = self.brain.provider.upper()
            model = self.brain.config.claude_model if provider == "CLAUDE" else self.brain.config.ollama_model
            self.provider.config(text=provider)
            self.model.config(text=model)
        except Exception:
            pass
        self.root.after(1000, self._status_tick)

    def set_state(self, state: str) -> None:
        self.activity = state.upper()
        self.root.after(0, self._state_ui)

    def _state_ui(self) -> None:
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
        self.mic.config(text="◉  LISTENING", fg=WHITE)
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
            self.root.after(0, self._voice_idle)

    def _voice_idle(self) -> None:
        self.listening = False
        self.mic.config(text="◉  MIC", fg=CYAN)
        self.set_state("SYSTEM READY")

    def set_response(self, text: str) -> None:
        self.set_state("SPEAKING")
        self.add_message("JARVIS", text)
        self.root.after(max(1000, min(4500, len(text) * 30)), lambda: self.set_state("SYSTEM READY"))

    def _tick(self) -> None:
        if self.running:
            self.root.after(100, lambda: None)

    def _close(self) -> None:
        self.running = False
        self.shutdown_callback()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()
