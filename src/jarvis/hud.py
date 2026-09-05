from __future__ import annotations

import ctypes
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


# --- High-DPI support -----------------------------------------------------
def _enable_high_dpi() -> None:
    if not hasattr(ctypes, "windll"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_enable_high_dpi()


BG = "#02060a"
BG_2 = "#040b11"
PANEL = "#061018"
PANEL_2 = "#081722"
CYAN = "#58e8ff"
CYAN_2 = "#20b9d8"
CYAN_DIM = "#145263"
CYAN_DARK = "#0a2933"
WHITE = "#dffaff"
MUTED = "#63818d"
GREEN = "#69f7ad"
AMBER = "#ffc85a"
RED = "#ff6570"


class JarvisHUD:
    """HUD de escritorio de JARVIS.

    Es una capa visual: no crea agentes ni toma decisiones de IA. El cerebro
    sigue siendo JarvisBrain y las acciones siguen pasando por el runtime.
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
        self.busy = False
        self._pulse = 0.0
        self._activity = "SYSTEM READY"
        self._started_at = time.monotonic()

        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // PERSONAL INTELLIGENCE SYSTEM")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._maximize()

        self._build()
        self._animate()
        self._refresh_status()

    def _maximize(self) -> None:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1600x950")

    def _build(self) -> None:
        # Header ------------------------------------------------------------
        header = tk.Frame(self.root, bg=BG, height=82)
        header.pack(fill="x", padx=34, pady=(22, 0))
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left", fill="y")
        tk.Label(
            title_box,
            text="J.A.R.V.I.S.",
            fg=WHITE,
            bg=BG,
            font=("Segoe UI", 27, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="PERSONAL INTELLIGENCE SYSTEM   //   BETA 0.2",
            fg=CYAN_DIM,
            bg=BG,
            font=("Consolas", 9, "bold"),
        ).pack(anchor="w", pady=(1, 0))

        status_box = tk.Frame(header, bg=BG)
        status_box.pack(side="right", fill="y")
        self.status_label = tk.Label(
            status_box, text="●  ONLINE", fg=GREEN, bg=BG,
            font=("Consolas", 10, "bold"),
        )
        self.status_label.pack(anchor="e", pady=(7, 0))
        self.activity_label = tk.Label(
            status_box, text="SYSTEM READY", fg=MUTED, bg=BG,
            font=("Consolas", 9),
        )
        self.activity_label.pack(anchor="e", pady=(3, 0))

        # Main grid ---------------------------------------------------------
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=34, pady=(4, 20))
        body.grid_columnconfigure(0, weight=1, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=420)
        body.grid_rowconfigure(0, weight=1)

        self._build_core(body)
        self._build_console(body)

    def _build_core(self, parent: tk.Frame) -> None:
        shell = tk.Frame(parent, bg=BG_2, highlightthickness=1, highlightbackground=CYAN_DARK)
        shell.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.canvas = tk.Canvas(
            shell,
            bg=BG_2,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self._draw_hud())

        # Objects are recreated during animation to keep the visual sharp at
        # the current DPI and window size.
        self._core_ids: list[int] = []
        self._draw_hud()

    def _build_console(self, parent: tk.Frame) -> None:
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        brain = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=CYAN_DARK)
        brain.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        left = tk.Frame(brain, bg=PANEL)
        left.pack(side="left", padx=18, pady=13)
        tk.Label(left, text="ACTIVE BRAIN", fg=MUTED, bg=PANEL,
                 font=("Consolas", 8, "bold")).pack(anchor="w")
        self.provider_value = tk.Label(left, text="OLLAMA", fg=CYAN, bg=PANEL,
                                       font=("Consolas", 16, "bold"))
        self.provider_value.pack(anchor="w", pady=(1, 0))

        self.model_value = tk.Label(brain, text="", fg=WHITE, bg=PANEL,
                                    font=("Consolas", 8))
        self.model_value.pack(side="right", padx=18, pady=(21, 0))

        self.log = scrolledtext.ScrolledText(
            right,
            bg=PANEL,
            fg=WHITE,
            insertbackground=CYAN,
            selectbackground="#123b48",
            selectforeground=WHITE,
            relief="flat",
            borderwidth=0,
            font=("Consolas", 10),
            wrap="word",
            padx=18,
            pady=16,
            spacing1=2,
            spacing3=8,
        )
        self.log.grid(row=1, column=0, sticky="nsew")
        self.log.tag_configure("system", foreground=MUTED)
        self.log.tag_configure("user", foreground=CYAN)
        self.log.tag_configure("jarvis", foreground=WHITE)
        self.log.tag_configure("voice", foreground=AMBER)
        self._log("SYSTEM", "Neural interface initialized. Awaiting command.")

        # Command bar ------------------------------------------------------
        command_bar = tk.Frame(right, bg=BG)
        command_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        command_bar.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            command_bar,
            bg=PANEL_2,
            fg=WHITE,
            insertbackground=CYAN,
            relief="flat",
            font=("Segoe UI", 12),
            bd=0,
        )
        self.entry.grid(row=0, column=0, sticky="ew", ipady=13)
        self.entry.bind("<Return>", lambda _: self._send_text())

        self.send_btn = self._button(command_bar, "SEND", self._send_text)
        self.send_btn.grid(row=0, column=1, padx=(8, 0))
        self.mic_btn = self._button(command_bar, "◉  MIC", self._toggle_voice)
        self.mic_btn.grid(row=0, column=2, padx=(8, 0))

        # Telemetry ---------------------------------------------------------
        telemetry = tk.Frame(right, bg=BG)
        telemetry.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        telemetry.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.cpu = self._metric(telemetry, "CPU")
        self.cpu.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.ram = self._metric(telemetry, "RAM")
        self.ram.grid(row=0, column=1, sticky="ew", padx=4)
        self.gpu = self._metric(telemetry, "GPU")
        self.gpu.grid(row=0, column=2, sticky="ew", padx=4)
        self.uptime = self._metric(telemetry, "UPTIME")
        self.uptime.grid(row=0, column=3, sticky="ew", padx=(4, 0))

        tk.Label(
            right,
            text="VOICE INPUT: LOCAL WHISPER   •   TTS: ELEVENLABS / LOCAL FALLBACK",
            fg="#31535f",
            bg=BG,
            font=("Consolas", 7),
        ).grid(row=4, column=0, sticky="w", pady=(9, 0))

    def _button(self, parent: tk.Frame, text: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#0b2731",
            fg=CYAN,
            activebackground="#123b48",
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Consolas", 9, "bold"),
            padx=17,
            pady=9,
        )

    def _metric(self, parent: tk.Frame, name: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=CYAN_DARK)
        label = tk.Label(
            frame, text=f"{name}\n--", fg=WHITE, bg=PANEL,
            font=("Consolas", 8), justify="center", pady=8,
        )
        label.pack(fill="both", expand=True)
        frame._metric_label = label  # type: ignore[attr-defined]
        return frame

    def _draw_hud(self) -> None:
        if not hasattr(self, "canvas"):
            return
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 400)
        cx, cy = w * 0.50, h * 0.49
        scale = min(w, h) / 760.0
        self.canvas.delete("all")

        # Fine technical grid.
        step = max(38, int(52 * scale))
        for x in range(0, w + step, step):
            self.canvas.create_line(x, 0, x, h, fill="#07151d", width=1)
        for y in range(0, h + step, step):
            self.canvas.create_line(0, y, w, y, fill="#07151d", width=1)

        # Corner brackets.
        bracket = 26
        margin = 22
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = w - margin if sx < 0 else margin
            y = h - margin if sy < 0 else margin
            self.canvas.create_line(x, y, x + sx * bracket, y, fill=CYAN_DIM, width=2)
            self.canvas.create_line(x, y, x, y + sy * bracket, fill=CYAN_DIM, width=2)

        t = time.monotonic()
        pulse = 1.0 + 0.035 * math.sin(t * 2.7)
        base = min(w, h) * 0.255

        # Outer segmented rings.
        for ring_i, radius_factor in enumerate((1.00, 0.82, 0.64)):
            r = base * radius_factor * pulse
            segments = 36 if ring_i != 1 else 24
            gap = 4 if ring_i != 1 else 7
            for i in range(segments):
                if (i + int(t * (ring_i + 1))) % (gap + 1) == 0:
                    continue
                start = i * (360 / segments) + t * (9 if ring_i % 2 == 0 else -12)
                extent = 360 / segments - 2.5
                self.canvas.create_arc(
                    cx-r, cy-r, cx+r, cy+r,
                    start=start, extent=extent,
                    style="arc", outline=CYAN_DIM if ring_i else CYAN,
                    width=2 if ring_i == 0 else 1,
                )

        # Rotating ticks.
        for i in range(48):
            angle = math.radians(i * 7.5 + t * (22 if i % 2 else -11))
            r1 = base * 1.10
            r2 = base * (1.10 + (0.035 if i % 4 == 0 else 0.018))
            self.canvas.create_line(
                cx + math.cos(angle)*r1, cy + math.sin(angle)*r1,
                cx + math.cos(angle)*r2, cy + math.sin(angle)*r2,
                fill=CYAN if i % 4 == 0 else CYAN_DIM,
                width=2 if i % 4 == 0 else 1,
            )

        # Central reactor.
        core = base * 0.30 * (1 + 0.07 * math.sin(t * 4.0))
        self.canvas.create_oval(cx-core*1.35, cy-core*1.35, cx+core*1.35, cy+core*1.35,
                                outline=CYAN_DARK, width=1)
        self.canvas.create_oval(cx-core, cy-core, cx+core, cy+core,
                                fill="#061923", outline=CYAN_2, width=2)
        inner = core * 0.50
        self.canvas.create_oval(cx-inner, cy-inner, cx+inner, cy+inner,
                                fill="#0b3340", outline=CYAN, width=2)
        inner2 = core * 0.20
        self.canvas.create_oval(cx-inner2, cy-inner2, cx+inner2, cy+inner2,
                                fill=CYAN, outline=WHITE, width=1)

        self.canvas.create_text(cx, cy - 9, text="J.A.R.V.I.S.", fill=WHITE,
                                font=("Segoe UI", max(15, int(19*scale)), "bold"))
        self.canvas.create_text(cx, cy + 18, text=self._activity, fill=CYAN,
                                font=("Consolas", max(7, int(9*scale)), "bold"))

        # HUD labels around the reactor.
        labels = [
            ("NEURAL CORE", cx - base*1.65, cy - base*0.98, "ONLINE"),
            ("VOICE ARRAY", cx + base*1.08, cy - base*0.98, "READY"),
            ("SYSTEM LINK", cx - base*1.65, cy + base*0.98, "SECURE"),
            ("ACTION BUS", cx + base*1.08, cy + base*0.98, "STANDBY"),
        ]
        for title, x, y, value in labels:
            self.canvas.create_text(x, y, text=title, anchor="w", fill=MUTED,
                                    font=("Consolas", 8, "bold"))
            self.canvas.create_text(x, y + 17, text=value, anchor="w", fill=CYAN,
                                    font=("Consolas", 9, "bold"))

        # Thin targeting lines.
        for direction in (-1, 1):
            self.canvas.create_line(cx + direction*base*0.34, cy,
                                    cx + direction*base*1.38, cy,
                                    fill=CYAN_DARK, width=1)
        self.canvas.create_text(25, h-24, text="CORE TELEMETRY // LIVE",
                                anchor="w", fill="#234b58", font=("Consolas", 7))

    def _animate(self) -> None:
        if not self.running:
            return
        self._pulse += 0.05
        self._draw_hud()
        self.root.after(50, self._animate)

    def _refresh_status(self) -> None:
        if not self.running:
            return
        try:
            if psutil:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                self.cpu._metric_label.config(text=f"CPU\n{cpu:.0f}%")  # type: ignore[attr-defined]
                self.ram._metric_label.config(text=f"RAM\n{ram:.0f}%")  # type: ignore[attr-defined]

                gpu_text = "--"
                try:
                    import subprocess
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                        capture_output=True, text=True, timeout=1, check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        gpu_text = f"{float(result.stdout.strip().splitlines()[0]):.0f}%"
                except Exception:
                    pass
                self.gpu._metric_label.config(text=f"GPU\n{gpu_text}")  # type: ignore[attr-defined]

            elapsed = int(time.monotonic() - self._started_at)
            self.uptime._metric_label.config(text=f"UPTIME\n{elapsed//60:02d}:{elapsed%60:02d}")  # type: ignore[attr-defined]

            provider = self.brain.provider.upper()
            model = self.brain.config.claude_model if provider == "CLAUDE" else self.brain.config.ollama_model
            self.provider_value.config(text=provider)
            self.model_value.config(text=model)
        except Exception:
            pass
        self.root.after(1000, self._refresh_status)

    def _log(self, who: str, text: str) -> None:
        tags = {"SYSTEM": "system", "YOU": "user", "JARVIS": "jarvis", "VOICE": "voice"}
        tag = tags.get(who, "system")
        self.log.insert("end", f"[{who}] ", tag)
        self.log.insert("end", f"{text}\n\n", tag)
        self.log.see("end")

    def add_message(self, who: str, text: str) -> None:
        if self.running:
            self.root.after(0, self._log, who, text)

    def _send_text(self) -> None:
        command = self.entry.get().strip()
        if not command or not self.running:
            return
        self.entry.delete(0, "end")
        self._log("YOU", command)
        self._activity = "PROCESSING COMMAND"
        self.activity_label.config(text=self._activity)
        self.busy = True
        threading.Thread(target=self._process_worker, args=(command,), daemon=True).start()

    def _process_worker(self, command: str) -> None:
        try:
            self.process_command(command)
        finally:
            self.root.after(0, self._command_idle)

    def _command_idle(self) -> None:
        self.busy = False
        if not self.listening:
            self._activity = "SYSTEM READY"
            self.activity_label.config(text=self._activity)

    def _toggle_voice(self) -> None:
        if self.listening or not self.running:
            return
        self.listening = True
        self._activity = "LISTENING"
        self.activity_label.config(text=self._activity)
        self.mic_btn.config(text="◉  LISTENING", fg=WHITE)
        self._log("VOICE", "Listening for 7 seconds...")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.add_message("YOU", command)
                self.root.after(0, lambda: self._set_processing())
                self.process_command(command)
            else:
                self.add_message("VOICE", "No command detected.")
        except Exception as exc:
            self.add_message("VOICE", f"Error: {exc}")
        finally:
            self.root.after(0, self._voice_idle)

    def _set_processing(self) -> None:
        self._activity = "PROCESSING COMMAND"
        self.activity_label.config(text=self._activity)

    def _voice_idle(self) -> None:
        self.listening = False
        self.mic_btn.config(text="◉  MIC", fg=CYAN)
        if not self.busy:
            self._activity = "SYSTEM READY"
            self.activity_label.config(text=self._activity)

    def set_response(self, text: str) -> None:
        self.add_message("JARVIS", text)

    def _close(self) -> None:
        self.running = False
        try:
            self.shutdown_callback()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def run(self) -> None:
        self.root.mainloop()
