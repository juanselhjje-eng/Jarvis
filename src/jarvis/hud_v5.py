from __future__ import annotations

import base64
import io
import math
import queue
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None


BG = "#03070b"
PANEL = "#071018"
PANEL_ALT = "#0b151d"
LINE = "#18303c"
CYAN = "#25d9ff"
CYAN_DARK = "#0b6475"
ORANGE = "#ffad4a"
GREEN = "#3ee5a1"
RED = "#ff5f73"
WHITE = "#e8f6fa"
MUTED = "#6d8791"


class JarvisHUDv5:
    """HUD nativo de escritorio: monitor de misión + vista de pantalla + controles seguros.

    Toda actualización proveniente de hilos de IA pasa por una cola hacia Tkinter.
    Así la red, Whisper y Computer Use no escriben directamente en la UI.
    """

    def __init__(
        self,
        brain,
        voice,
        process_command: Callable[[str], None],
        shutdown: Callable[[], None],
        neural=None,
        stop_mission: Callable[[], None] | None = None,
    ):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.stop_mission_callback = stop_mission or (lambda: None)
        self.neural = neural
        self.root = tk.Tk()
        self.state = "STANDBY"
        self.phase = 0.0
        self.history: list[str] = []
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._main_thread = threading.get_ident()
        self._screen_photo = None
        self._last_screen = None
        self._build_window()
        self._build_ui()
        self._pump_ui()
        self._pulse()
        self._clock()
        self._telemetry()

    def _build_window(self) -> None:
        self.root.title("J.A.R.V.I.S. // COMPUTER AGENT")
        self.root.configure(bg=BG)
        self.root.minsize(1280, 780)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<F2>", lambda _e: self.entry.focus_set())
        self.root.bind("<F8>", lambda _e: self._observe_screen())
        self.root.bind("<Escape>", lambda _e: self._stop_mission())

    def label(self, parent, text, size=9, fg=WHITE, bold=False, anchor="w"):
        return tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg=fg,
            font=("Segoe UI", size, "bold" if bold else "normal"),
            anchor=anchor,
            justify="left",
        )

    def button(self, parent, text, command, width=None, accent=False, danger=False):
        fg = RED if danger else (CYAN if accent else WHITE)
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg="#0a1a23" if not danger else "#241118",
            fg=fg,
            activebackground="#173844",
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            padx=8,
            pady=7,
        )

    def panel(self, parent, row, column, padx=0, pady=0, sticky="nsew"):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        frame.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
        return frame

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#010307", height=62, highlightthickness=1, highlightbackground=LINE)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.label(header, "J.A.R.V.I.S.", 16, CYAN, True).pack(side="left", padx=20)
        self.label(header, "PERSONAL COMPUTER AGENT  /  MISSION CONTROL", 8, MUTED, True).pack(side="left", padx=8)
        self.state_chip = tk.Label(header, text="STANDBY", bg="#0b2029", fg=CYAN, font=("Consolas", 8, "bold"), padx=12, pady=5)
        self.state_chip.pack(side="right", padx=14)
        self.clock_label = self.label(header, "--:--:--", 9, WHITE, True)
        self.clock_label.pack(side="right", padx=8)
        self.provider_label = self.label(header, "CORE: --", 8, GREEN, True)
        self.provider_label.pack(side="right", padx=16)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, minsize=235)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=335)
        body.grid_rowconfigure(0, weight=1)
        self._left(body)
        self._center(body)
        self._right(body)
        self._composer()

    def _left(self, body) -> None:
        left = self.panel(body, 0, 0, padx=(0, 6))
        self.label(left, "SYSTEM MAP", 9, CYAN, True).pack(anchor="w", padx=14, pady=(15, 10))
        modules = [
            ("01", "CORE", "Gemini → Ollama"),
            ("02", "VISION", "Screen on demand"),
            ("03", "PLANNER", "Goal decomposition"),
            ("04", "OODA", "Observe / act / verify"),
            ("05", "DESKTOP", "Mouse + keyboard"),
            ("06", "MEMORY", "Local context"),
            ("07", "NEURAL LAB", "Local training"),
        ]
        for num, name, detail in modules:
            row = tk.Frame(left, bg=left["bg"])
            row.pack(fill="x", padx=12, pady=4)
            self.label(row, num, 7, CYAN_DARK, True).pack(side="left", padx=(0, 8))
            text = tk.Frame(row, bg=row["bg"])
            text.pack(side="left", fill="x")
            self.label(text, name, 8, WHITE, True).pack(anchor="w")
            self.label(text, detail, 7, MUTED).pack(anchor="w")

        self.label(left, "DIRECT OPERATIONS", 9, CYAN, True).pack(anchor="w", padx=14, pady=(20, 7))
        for text, command in (
            ("DIAGNOSTIC", "revisa mi pc"),
            ("OBSERVE SCREEN", "mira la pantalla"),
            ("OPEN TEAMS", "abre teams personal"),
            ("NEURAL LAB", "crea una red neuronal"),
        ):
            self.button(left, text, lambda c=command: self._quick(c)).pack(fill="x", padx=12, pady=3)

        self.button(left, "STOP CURRENT MISSION", self._stop_mission, danger=True).pack(fill="x", padx=12, pady=(10, 3))
        self.label(left, "HOTKEYS", 8, CYAN, True).pack(anchor="w", padx=14, pady=(18, 5))
        self.label(left, "F2  command focus\nF8  observe screen\nESC  stop mission", 7, MUTED).pack(anchor="w", padx=14)

        self.label(left, "POLICY", 8, CYAN, True).pack(anchor="w", padx=14, pady=(18, 5))
        self.label(left, "VISIBLE CONTROL\nNO KEYLOGGING\nNO CREDENTIAL CAPTURE\nHUMAN GATE ON", 7, MUTED).pack(anchor="w", padx=14)

    def _center(self, body) -> None:
        center = self.panel(body, 0, 1, padx=6)
        center.grid_rowconfigure(1, weight=1)
        center.grid_rowconfigure(2, minsize=135)
        center.grid_columnconfigure(0, weight=1)

        top = tk.Frame(center, bg=center["bg"], height=42)
        top.grid(row=0, column=0, sticky="ew")
        self.label(top, "SCREEN PERCEPTION", 9, WHITE, True).pack(side="left", padx=15, pady=12)
        self.screen_status = self.label(top, "NO CAPTURE", 8, MUTED, True)
        self.screen_status.pack(side="right", padx=15)

        field = tk.Frame(center, bg="#010509")
        field.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        field.grid_rowconfigure(0, weight=1)
        field.grid_columnconfigure(0, weight=1)
        self.screen_canvas = tk.Canvas(field, bg="#010509", highlightthickness=0)
        self.screen_canvas.grid(row=0, column=0, sticky="nsew")
        self.screen_canvas.bind("<Configure>", lambda _e: self._render_screen())

        stream_box = tk.Frame(center, bg=center["bg"])
        stream_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.label(stream_box, "AGENT EVENT BUS", 8, CYAN, True).pack(anchor="w", padx=5, pady=(3, 4))
        self.stream = tk.Text(
            stream_box,
            bg="#02070b",
            fg="#9ab2ba",
            insertbackground=CYAN,
            relief="flat",
            bd=0,
            font=("Consolas", 8),
            state="disabled",
            height=7,
        )
        self.stream.pack(fill="both", expand=True)

        self._draw_empty_screen()

    def _draw_empty_screen(self) -> None:
        self.screen_canvas.delete("all")
        w = max(700, self.screen_canvas.winfo_width())
        h = max(450, self.screen_canvas.winfo_height())
        self.screen_canvas.create_rectangle(1, 1, w - 1, h - 1, outline=LINE)
        self.screen_canvas.create_text(w / 2, h / 2 - 12, text="SCREEN FEED", fill=MUTED, font=("Consolas", 16, "bold"))
        self.screen_canvas.create_text(w / 2, h / 2 + 18, text="F8 / OBSERVE SCREEN para capturar la pantalla", fill=CYAN_DARK, font=("Consolas", 9))

    def _right(self, body) -> None:
        right = self.panel(body, 0, 2, padx=(6, 0))
        self.label(right, "MISSION CONTROL", 10, WHITE, True).pack(anchor="w", padx=14, pady=(15, 2))
        self.label(right, "GOAL → PLAN → OBSERVE → ACT → VERIFY", 7, MUTED, True).pack(anchor="w", padx=14, pady=(0, 12))
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
        self.learning = self.label(right, "NEURAL LAB: idle", 7, MUTED)
        self.learning.pack(anchor="w", padx=14)
        if self.neural:
            self.learning.config(text=self.neural.status())

        self.label(right, "HUMAN GATE", 8, CYAN, True).pack(anchor="w", padx=14, pady=(17, 5))
        self.gate = self.label(right, "ARMED\nExternal actions require confirmation", 8, ORANGE, True)
        self.gate.pack(anchor="w", padx=14)

        self.button(right, "NEW MISSION", self._new_session, accent=True).pack(fill="x", padx=12, pady=(18, 4))
        self.button(right, "OBSERVE NOW", self._observe_screen).pack(fill="x", padx=12, pady=4)
        self.button(right, "STOP JARVIS", self._close, danger=True).pack(fill="x", padx=12, pady=4)

    def _composer(self) -> None:
        bar = tk.Frame(self.root, bg="#010307", highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(bar, bg="#08131b", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10, ipady=10)
        self.entry.insert(0, "Escribe una orden para JARVIS...")
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", lambda _e: self._send())
        self.button(bar, "MIC", self._voice, width=6).pack(side="left", padx=3)
        self.button(bar, "EXECUTE", self._send, width=10, accent=True).pack(side="left", padx=(3, 10))

    def _clear_placeholder(self, _event=None) -> None:
        if self.entry.get() == "Escribe una orden para JARVIS...":
            self.entry.delete(0, "end")

    def _pump_ui(self) -> None:
        try:
            for _ in range(40):
                callback = self._ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(35, self._pump_ui)

    def _ui(self, callback: Callable[[], None]) -> None:
        if threading.get_ident() == self._main_thread:
            callback()
        else:
            self._ui_queue.put(callback)

    def _draw_reactor(self) -> None:
        c = self.screen_canvas
        if self._last_screen is not None:
            return
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 450)
        c.delete("all")
        for x in range(0, w, 30):
            c.create_line(x, 0, x, h, fill="#07131a")
        for y in range(0, h, 30):
            c.create_line(0, y, w, y, fill="#07131a")
        cx, cy = w / 2, h / 2
        pulse = math.sin(self.phase * 1.8) * 5
        for r in (145, 112, 78):
            c.create_oval(cx-r-pulse, cy-r-pulse, cx+r+pulse, cy+r+pulse, outline="#0b2933", width=1)
        for i, radius in enumerate((92, 55, 25)):
            points = []
            for j in range(6):
                angle = math.radians(j * 60 - 30 + self.phase * (1 if i == 0 else -0.5))
                points += [cx + (radius + pulse) * math.cos(angle), cy + (radius + pulse) * math.sin(angle)]
            c.create_polygon(*points, outline=(CYAN_DARK, CYAN, WHITE)[i], fill="", width=2 if i < 2 else 1)
        c.create_text(cx, cy - 12, text="J.A.R.V.I.S.", fill=WHITE, font=("Segoe UI", 16, "bold"))
        c.create_text(cx, cy + 16, text=self.state, fill=CYAN, font=("Consolas", 9, "bold"))
        c.create_text(18, 18, text="PERCEPTION CORE / READY", fill=CYAN_DARK, anchor="nw", font=("Consolas", 8))
        c.create_text(w - 18, 18, text="HUMAN GATE / ACTIVE", fill=ORANGE, anchor="ne", font=("Consolas", 8))

    def _pulse(self):
        if self.root.winfo_exists():
            self.phase += 0.06
            if self._last_screen is None:
                self._draw_reactor()
            self.root.after(55, self._pulse)

    def _clock(self):
        if self.root.winfo_exists():
            self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
            self.root.after(500, self._clock)

    def _telemetry(self):
        if self.root.winfo_exists() and psutil:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("C:\\").percent
                self.telemetry.config(text=f"CPU  {cpu:>5.1f}%\nRAM  {ram:>5.1f}%\nDISK {disk:>5.1f}%")
            except Exception as exc:
                self.telemetry.config(text=f"Telemetry error\n{exc}")
            self.root.after(1200, self._telemetry)

    def run(self) -> None:
        self.root.mainloop()

    def set_state(self, state: str) -> None:
        def apply() -> None:
            self.state = state.upper()
            danger = self.state in {"ERROR", "FALLO"}
            self.state_chip.config(text=self.state, fg=RED if danger else CYAN)
            self.state_label_update()
            mapping = {"OBSERVANDO": 0, "ANALIZANDO": 1, "PENSANDO": 2, "PROCESANDO": 2, "OODA": 3, "EJECUTANDO": 3, "VERIFICANDO": 4}
            active = mapping.get(self.state)
            for i, item in enumerate(self.ooda):
                name = item.cget("text").split("  ", 1)[-1]
                item.config(fg=CYAN if i == active else MUTED, text=("●" if i == active else "○") + "  " + name)
        self._ui(apply)

    def state_label_update(self) -> None:
        if hasattr(self, "screen_status"):
            self.screen_status.config(text="LIVE CAPTURE" if self._last_screen else "NO CAPTURE", fg=GREEN if self._last_screen else MUTED)

    def update_provider(self) -> None:
        self._ui(lambda: self.provider_label.config(text=f"CORE: {self.brain.provider.upper()}"))

    def add_message(self, role: str, text: str) -> None:
        def apply() -> None:
            line = f"[{datetime.now().strftime('%H:%M:%S')}] {role:<8} {text}"
            self.history.append(line)
            self.stream.config(state="normal")
            self.stream.insert("end", line + "\n")
            self.stream.see("end")
            self.stream.config(state="disabled")
        self._ui(apply)

    def set_response(self, text: str) -> None:
        def apply() -> None:
            self.mission.config(text=text[:600])
        self._ui(apply)
        self.add_message("JARVIS", text)

    def set_mission(self, text: str) -> None:
        def apply() -> None:
            self.mission.config(text=text[:600])
        self._ui(apply)
        self.add_message("MISSION", text)

    def show_screen(self, image_base64: str | None, width: int = 0, height: int = 0) -> None:
        def apply() -> None:
            if not image_base64 or Image is None or ImageTk is None:
                self._last_screen = None
                self._draw_empty_screen()
                self.state_label_update()
                return
            try:
                image = Image.open(io.BytesIO(base64.b64decode(image_base64))).convert("RGB")
                self._last_screen = image.copy()
                self.screen_status.config(text=f"LIVE CAPTURE  {width}x{height}", fg=GREEN)
                self._render_screen()
            except Exception as exc:
                self._last_screen = None
                self.screen_status.config(text="CAPTURE ERROR", fg=RED)
                self._draw_empty_screen()
                self.add_message("HUD", f"No se pudo renderizar la captura: {exc}")
        self._ui(apply)

    def _render_screen(self) -> None:
        if self._last_screen is None or ImageTk is None:
            self._draw_reactor()
            return
        try:
            canvas_w = max(300, self.screen_canvas.winfo_width() - 18)
            canvas_h = max(220, self.screen_canvas.winfo_height() - 18)
            image = self._last_screen.copy()
            image.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            self._screen_photo = ImageTk.PhotoImage(image)
            self.screen_canvas.delete("all")
            w = self.screen_canvas.winfo_width()
            h = self.screen_canvas.winfo_height()
            self.screen_canvas.create_image(w / 2, h / 2, image=self._screen_photo, anchor="center")
            self.screen_canvas.create_rectangle(1, 1, w - 1, h - 1, outline=CYAN_DARK)
            self.screen_canvas.create_text(12, 12, text="SCREEN / USER-DIRECTED", fill=CYAN, anchor="nw", font=("Consolas", 8, "bold"))
        except Exception:
            pass

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text or text == "Escribe una orden para JARVIS...":
            return
        self.entry.delete(0, "end")
        self.add_message("USER", text)
        self.set_state("ANALIZANDO")
        self.process_command(text)

    def _voice(self) -> None:
        def worker() -> None:
            self.set_state("ESCUCHANDO")
            try:
                text = self.voice.listen_for_command(seconds=7)
                if text:
                    self._ui(lambda: (self.entry.delete(0, "end"), self.entry.insert(0, text)))
                    self._ui(self._send)
            except Exception as exc:
                self.add_message("VOICE", f"Error: {exc}")
                self.set_state("ERROR")
        threading.Thread(target=worker, daemon=True, name="jarvis-hud-mic").start()

    def _observe_screen(self) -> None:
        def worker() -> None:
            self.set_state("OBSERVANDO")
            try:
                observation = self._computer_observer()
                if observation is None:
                    return
                self.show_screen(observation.image_base64, observation.width, observation.height)
                if observation.image_base64:
                    result = self.brain.analyze_screen(observation.image_base64, "Describe brevemente lo que es visible en la pantalla y menciona solo elementos relevantes para el usuario.")
                    self.set_response(result)
                else:
                    self.add_message("VISION", observation.note)
            except Exception as exc:
                self.add_message("VISION", f"Error: {exc}")
                self.set_state("ERROR")
        threading.Thread(target=worker, daemon=True, name="jarvis-screen-observer").start()

    def _computer_observer(self):
        # Import local para mantener el HUD desacoplado del runtime principal.
        from .computer_use import ComputerUse
        return ComputerUse().observe()

    def _stop_mission(self) -> None:
        try:
            self.stop_mission_callback()
            self.set_state("VERIFICANDO")
            self.add_message("SYSTEM", "Parada de misión solicitada.")
        except Exception as exc:
            self.add_message("SYSTEM", f"No pude detener la misión: {exc}")

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
        self._last_screen = None
        self._draw_empty_screen()
        self.set_state("STANDBY")

    def _close(self) -> None:
        try:
            self.shutdown_callback()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass
