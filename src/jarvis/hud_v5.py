from __future__ import annotations

import base64
import io
import math
import queue
import random
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

BG = "#02050a"
PANEL = "#071018"
LINE = "#16313d"
CYAN = "#25d9ff"
CYAN_DARK = "#0b6577"
BLUE = "#347dff"
ORANGE = "#ffad4a"
GREEN = "#3ee5a1"
RED = "#ff5f73"
WHITE = "#e8f6fa"
MUTED = "#6d8791"


class JarvisHUDv5:
    """Interfaz nativa de JARVIS con núcleo holográfico 3D generado en Tkinter.

    El centro no es una imagen ni un círculo plano: se calcula una esfera mediante
    coordenadas 3D, perspectiva, profundidad, partículas, órbitas y parallax del ratón.
    """

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], neural=None, stop_mission: Callable[[], None] | None = None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.stop_mission_callback = stop_mission or (lambda: None)
        self.neural = neural
        self.root = tk.Tk()
        self.state = "STANDBY"
        self.phase = 0.0
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.history: list[str] = []
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._main_thread = threading.get_ident()
        self._screen_photo = None
        self._last_screen: tuple[str, int, int] | None = None
        self._particles = self._make_particles(130)
        self._build_window()
        self._build_ui()
        self._pump_ui()
        self._pulse()
        self._clock()
        self._telemetry()

    def _make_particles(self, count: int) -> list[dict[str, float]]:
        random.seed(11)
        return [{
            "theta": random.random() * math.tau,
            "phi": math.acos(2 * random.random() - 1),
            "radius": random.uniform(135, 255),
            "speed": random.uniform(0.10, 0.55),
            "size": random.choice((1, 1, 1, 2)),
        } for _ in range(count)]

    def _build_window(self) -> None:
        self.root.title("J.A.R.V.I.S. // 3D COGNITIVE SYSTEM")
        self.root.configure(bg=BG)
        self.root.minsize(1360, 820)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1680x980")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<F2>", lambda _e: self.entry.focus_set())
        self.root.bind("<F8>", lambda _e: self._quick("mira la pantalla"))
        self.root.bind("<Escape>", lambda _e: self._stop_mission())

    def label(self, parent, text, size=9, fg=WHITE, bold=False, anchor="w"):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor=anchor, justify="left")

    def button(self, parent, text, command, width=None, accent=False, danger=False):
        return tk.Button(parent, text=text, command=command, width=width, bg="#102934" if accent else ("#251017" if danger else "#0a1a23"), fg=RED if danger else (CYAN if accent else WHITE), activebackground="#173844", activeforeground=WHITE, relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=8, pady=7)

    def panel(self, parent, row, column, padx=0, pady=0):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        frame.grid(row=row, column=column, padx=padx, pady=pady, sticky="nsew")
        return frame

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#010307", height=62, highlightthickness=1, highlightbackground=LINE)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.label(header, "J.A.R.V.I.S.", 17, CYAN, True).pack(side="left", padx=20)
        self.label(header, "3D COGNITIVE CORE  /  AUTONOMOUS COMPUTER AGENT", 8, MUTED, True).pack(side="left", padx=8)
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
        body.grid_columnconfigure(2, minsize=340)
        body.grid_rowconfigure(0, weight=1)
        self._left(body)
        self._center(body)
        self._right(body)
        self._composer()

    def _left(self, body) -> None:
        left = self.panel(body, 0, 0, padx=(0, 6))
        self.label(left, "SYSTEM ARCHITECTURE", 9, CYAN, True).pack(anchor="w", padx=14, pady=(15, 10))
        modules = [("01", "CORE AGENT", "Gemini / Ollama"), ("02", "VISION", "Screen perception"), ("03", "PLANNER", "Task decomposition"), ("04", "OODA", "Observe / decide / act"), ("05", "DESKTOP", "Mouse + keyboard"), ("06", "MEMORY", "Local context"), ("07", "NEURAL LAB", "Local training")]
        for num, name, detail in modules:
            row = tk.Frame(left, bg=left["bg"])
            row.pack(fill="x", padx=12, pady=4)
            self.label(row, num, 7, CYAN_DARK, True).pack(side="left", padx=(0, 8))
            text = tk.Frame(row, bg=row["bg"])
            text.pack(side="left", fill="x")
            self.label(text, name, 8, WHITE, True).pack(anchor="w")
            self.label(text, detail, 7, MUTED).pack(anchor="w")
        self.label(left, "OPERATIONS", 9, CYAN, True).pack(anchor="w", padx=14, pady=(20, 7))
        for text, command in (("DIAGNOSTIC", "revisa mi pc"), ("OBSERVE SCREEN", "mira la pantalla"), ("OPEN TEAMS", "abre teams personal"), ("NEURAL LAB", "crea una red neuronal")):
            self.button(left, text, lambda c=command: self._quick(c)).pack(fill="x", padx=12, pady=3)
        self.button(left, "STOP CURRENT MISSION", self._stop_mission, danger=True).pack(fill="x", padx=12, pady=(10, 3))
        self.label(left, "CONTROLS", 8, CYAN, True).pack(anchor="w", padx=14, pady=(18, 5))
        self.label(left, "F2  COMMAND\nF8  SCREEN OBSERVE\nESC  STOP MISSION\nMOUSE  3D PARALLAX", 7, MUTED).pack(anchor="w", padx=14)
        self.label(left, "POLICY", 8, CYAN, True).pack(anchor="w", padx=14, pady=(18, 5))
        self.label(left, "VISIBLE CONTROL\nNO KEYLOGGING\nNO CREDENTIAL CAPTURE\nHUMAN GATE ON", 7, MUTED).pack(anchor="w", padx=14)

    def _center(self, body) -> None:
        center = self.panel(body, 0, 1, padx=6)
        center.grid_rowconfigure(1, weight=1)
        center.grid_rowconfigure(2, minsize=135)
        center.grid_columnconfigure(0, weight=1)
        top = tk.Frame(center, bg=center["bg"], height=42)
        top.grid(row=0, column=0, sticky="ew")
        self.label(top, "HOLOGRAPHIC 3D CORE", 9, WHITE, True).pack(side="left", padx=15, pady=12)
        self.depth_label = self.label(top, "DEPTH FIELD / PARALLAX ACTIVE", 7, CYAN_DARK, True)
        self.depth_label.pack(side="right", padx=15)
        field = tk.Frame(center, bg="#010509")
        field.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        field.grid_rowconfigure(0, weight=1)
        field.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(field, bg="#010509", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Motion>", self._mouse_motion)
        self.canvas.bind("<Leave>", lambda _e: self._set_mouse(0.0, 0.0))
        stream_box = tk.Frame(center, bg=center["bg"])
        stream_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.label(stream_box, "AGENT EVENT BUS", 8, CYAN, True).pack(anchor="w", padx=5, pady=(3, 4))
        self.stream = tk.Text(stream_box, bg="#02070b", fg="#9ab2ba", insertbackground=CYAN, relief="flat", bd=0, font=("Consolas", 8), state="disabled", height=7)
        self.stream.pack(fill="both", expand=True)

    def _right(self, body) -> None:
        right = self.panel(body, 0, 2, padx=(6, 0))
        self.label(right, "MISSION CONTROL", 10, WHITE, True).pack(anchor="w", padx=14, pady=(15, 2))
        self.label(right, "GOAL → PLAN → PERCEIVE → ACT → VERIFY", 7, MUTED, True).pack(anchor="w", padx=14, pady=(0, 12))
        self.mission = self.label(right, "No active mission.", 8, MUTED)
        self.mission.pack(anchor="w", padx=14, pady=(0, 8))
        self.ooda = []
        for name in ("PERCEIVE", "ORIENT", "DECIDE", "ACT", "VERIFY"):
            item = self.label(right, "○  " + name, 8, MUTED, True)
            item.pack(anchor="w", padx=16, pady=3)
            self.ooda.append(item)
        self.label(right, "SCREEN FEED", 8, CYAN, True).pack(anchor="w", padx=14, pady=(15, 5))
        self.screen_frame = tk.Frame(right, bg="#010509", highlightthickness=1, highlightbackground=LINE, height=170)
        self.screen_frame.pack(fill="x", padx=12)
        self.screen_frame.pack_propagate(False)
        self.screen_preview = self.label(self.screen_frame, "NO SCREEN FRAME\nF8 / OBSERVE SCREEN", 8, MUTED, True, anchor="center")
        self.screen_preview.pack(fill="both", expand=True)
        self.label(right, "TELEMETRY", 8, CYAN, True).pack(anchor="w", padx=14, pady=(15, 5))
        self.telemetry = self.label(right, "CPU --\nRAM --\nDISK --", 8, MUTED)
        self.telemetry.pack(anchor="w", padx=14)
        self.label(right, "LEARNING", 8, CYAN, True).pack(anchor="w", padx=14, pady=(14, 5))
        self.learning = self.label(right, "NEURAL LAB: idle", 7, MUTED)
        self.learning.pack(anchor="w", padx=14)
        if self.neural:
            self.learning.config(text=self.neural.status())
        self.label(right, "HUMAN GATE", 8, CYAN, True).pack(anchor="w", padx=14, pady=(14, 5))
        self.gate = self.label(right, "ARMED\nExternal actions require confirmation", 8, ORANGE, True)
        self.gate.pack(anchor="w", padx=14)
        self.button(right, "NEW MISSION", self._new_session, accent=True).pack(fill="x", padx=12, pady=(16, 4))
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

    def _project(self, x: float, y: float, z: float, cx: float, cy: float):
        depth = 1.0 / max(0.52, 1.0 + z * 0.0030)
        return cx + x * depth, cy + y * depth, depth

    def _draw_3d(self) -> None:
        c = self.canvas
        w = max(c.winfo_width(), 720)
        h = max(c.winfo_height(), 480)
        c.delete("all")
        cx = w * 0.50 + self.mouse_x * 22
        cy = h * 0.46 + self.mouse_y * 15
        t = self.phase

        # Infinite perspective grid.
        horizon = h * 0.70
        for i in range(12):
            y = horizon + (i * i) * 2.45
            c.create_line(0, y, w, y, fill="#06141b")
        for x in range(-w, w * 2, 65):
            c.create_line(w / 2, horizon, x, h, fill="#06141b")
        c.create_line(0, horizon, w, horizon, fill="#0c3541")

        # Orbital ellipses in different planes.
        for ring in range(7):
            radius = 118 + ring * 21
            tilt = 0.22 + ring * 0.055
            pts = []
            for i in range(81):
                a = math.tau * i / 80 + t * (0.16 if ring % 2 == 0 else -0.11)
                x = math.cos(a) * radius
                y = math.sin(a) * radius * tilt
                z = math.sin(a) * radius
                px, py, _ = self._project(x, y, z, cx, cy)
                pts.extend((px, py))
            c.create_line(*pts, fill=CYAN_DARK if ring < 4 else "#123946", width=1, smooth=True)

        # Spherical latitude and longitude mesh.
        for lat in range(-75, 90, 15):
            phi = math.radians(lat)
            pts = []
            for i in range(61):
                lon = math.tau * i / 60 + t * 0.52
                rr = 108 * math.cos(phi)
                x = rr * math.cos(lon)
                y = 108 * math.sin(phi)
                z = rr * math.sin(lon)
                px, py, _ = self._project(x, y, z, cx, cy)
                pts.extend((px, py))
            c.create_line(*pts, fill="#0a4251", width=1, smooth=True)
        for lon_i in range(12):
            lon = math.tau * lon_i / 12 + t * 0.52
            pts = []
            for i in range(41):
                phi = -math.pi / 2 + math.pi * i / 40
                rr = 108 * math.cos(phi)
                x = rr * math.cos(lon)
                y = 108 * math.sin(phi)
                z = rr * math.sin(lon)
                px, py, _ = self._project(x, y, z, cx, cy)
                pts.extend((px, py))
            c.create_line(*pts, fill="#0a3948", width=1, smooth=True)

        # Floating particles with depth-aware size.
        for p in self._particles:
            a = p["theta"] + t * p["speed"]
            phi = p["phi"]
            r = p["radius"]
            x = r * math.sin(phi) * math.cos(a)
            y = r * math.cos(phi)
            z = r * math.sin(phi) * math.sin(a)
            px, py, depth = self._project(x, y, z, cx, cy)
            size = max(1.0, p["size"] * depth)
            fill = CYAN if depth > 0.93 else (BLUE if depth > 0.78 else CYAN_DARK)
            c.create_oval(px - size, py - size, px + size, py + size, fill=fill, outline="")

        # Central volumetric core layers.
        pulse = math.sin(t * 2.2) * 5
        for radius, outline, width in ((94, "#0b6073", 2), (75, "#0b849b", 2), (56, CYAN_DARK, 2), (39, CYAN, 1)):
            r = radius + pulse * (radius / 94)
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=outline, width=width)
        c.create_oval(cx - 30, cy - 30, cx + 30, cy + 30, outline=WHITE, width=1)
        c.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, fill=CYAN, outline=WHITE, width=1)

        # Energy spokes and depth markers.
        for i in range(18):
            a = math.tau * i / 18 + t * 0.75
            inner = 118 + math.sin(t + i) * 4
            outer = 150 + math.cos(t * 0.8 + i) * 7
            x1, y1, _ = self._project(math.cos(a) * inner, math.sin(a) * inner, math.sin(a) * inner, cx, cy)
            x2, y2, _ = self._project(math.cos(a) * outer, math.sin(a) * outer, math.sin(a) * outer, cx, cy)
            c.create_line(x1, y1, x2, y2, fill="#0b5361", width=1)

        # Technical labels and targeting brackets.
        c.create_text(20, 18, text="HOLOGRAPHIC CORE // 3D DEPTH FIELD", fill=CYAN_DARK, anchor="nw", font=("Consolas", 8, "bold"))
        c.create_text(w - 20, 18, text="PARALLAX: ON", fill=GREEN, anchor="ne", font=("Consolas", 8, "bold"))
        c.create_text(cx, cy - 150, text="J.A.R.V.I.S.", fill=MUTED, font=("Segoe UI", 10, "bold"))
        c.create_text(cx, cy + 137, text=self.state, fill=CYAN, font=("Consolas", 9, "bold"))
        s = 162
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x, y = cx + sx * s, cy + sy * s
            c.create_line(x, y, x - sx * 20, y, fill="#155362")
            c.create_line(x, y, x, y - sy * 20, fill="#155362")

    def _pulse(self) -> None:
        try:
            if self.root.winfo_exists():
                self.phase += 0.035
                self._draw_3d()
                self.root.after(45, self._pulse)
        except tk.TclError:
            pass

    def _clock(self) -> None:
        try:
            if self.root.winfo_exists():
                self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
                self.root.after(500, self._clock)
        except tk.TclError:
            pass

    def _telemetry(self) -> None:
        try:
            if self.root.winfo_exists() and psutil:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("C:\\").percent
                self.telemetry.config(text=f"CPU  {cpu:>5.1f}%\nRAM  {ram:>5.1f}%\nDISK {disk:>5.1f}%")
                self.root.after(1200, self._telemetry)
        except (tk.TclError, OSError):
            pass

    def _mouse_motion(self, event) -> None:
        w, h = max(self.canvas.winfo_width(), 1), max(self.canvas.winfo_height(), 1)
        self._set_mouse((event.x - w / 2) / (w / 2), (event.y - h / 2) / (h / 2))

    def _set_mouse(self, x: float, y: float) -> None:
        self.mouse_x = max(-1.0, min(1.0, x))
        self.mouse_y = max(-1.0, min(1.0, y))

    def _ui(self, callback: Callable[[], None]) -> None:
        if threading.get_ident() == self._main_thread:
            callback()
        else:
            self._ui_queue.put(callback)

    def _pump_ui(self) -> None:
        try:
            for _ in range(50):
                callback = self._ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(30, self._pump_ui)
        except tk.TclError:
            pass

    def run(self) -> None:
        self.root.mainloop()

    def set_state(self, state: str) -> None:
        self._ui(lambda: self._set_state_now(state))

    def _set_state_now(self, state: str) -> None:
        self.state = state.upper()
        self.state_chip.config(text=self.state, fg=RED if self.state in {"ERROR", "FALLO"} else CYAN)
        mapping = {"OBSERVANDO": 0, "ANALIZANDO": 1, "PENSANDO": 2, "PROCESANDO": 2, "OODA": 3, "EJECUTANDO": 3, "VERIFICANDO": 4}
        active = mapping.get(self.state)
        for i, item in enumerate(self.ooda):
            name = item.cget("text").split("  ", 1)[-1]
            item.config(fg=CYAN if i == active else MUTED, text=("●" if i == active else "○") + "  " + name)

    def update_provider(self) -> None:
        self._ui(lambda: self.provider_label.config(text=f"CORE: {self.brain.provider.upper()}"))

    def add_message(self, role: str, text: str) -> None:
        self._ui(lambda: self._add_message_now(role, text))

    def _add_message_now(self, role: str, text: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {role:<8} {text}"
        self.history.append(line)
        self.stream.config(state="normal")
        self.stream.insert("end", line + "\n")
        self.stream.see("end")
        self.stream.config(state="disabled")

    def set_response(self, text: str) -> None:
        self._ui(lambda: (self.mission.config(text=text[:420]), self._add_message_now("JARVIS", text)))

    def set_mission(self, text: str) -> None:
        self._ui(lambda: (self.mission.config(text=text[:420]), self._add_message_now("MISSION", text)))

    def show_screen(self, image_base64: str | None, width: int = 0, height: int = 0) -> None:
        self._ui(lambda: self._show_screen_now(image_base64, width, height))

    def _show_screen_now(self, image_base64: str | None, width: int, height: int) -> None:
        if not image_base64 or Image is None or ImageTk is None:
            self.screen_preview.config(text="NO SCREEN FRAME\nSCREENSHOT UNAVAILABLE", image="")
            self._screen_photo = None
            return
        try:
            image = Image.open(io.BytesIO(base64.b64decode(image_base64))).convert("RGB")
            target_w = max(230, self.screen_frame.winfo_width() - 8)
            target_h = max(120, self.screen_frame.winfo_height() - 8)
            image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            self._screen_photo = ImageTk.PhotoImage(image)
            self.screen_preview.config(image=self._screen_photo, text="")
            self.depth_label.config(text=f"SCREEN FRAME {width}x{height} / 3D CORE ACTIVE")
            self._add_message_now("VISION", f"Frame {width}x{height} recibido.")
        except Exception as exc:
            self.screen_preview.config(text=f"FRAME ERROR\n{exc}", image="")
            self._screen_photo = None

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text or text == "Escribe una orden para JARVIS...":
            return
        self.entry.delete(0, "end")
        self._add_message_now("USER", text)
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
            self._add_message_now("VOICE", f"Error: {exc}")
            self.set_state("ERROR")

    def _quick(self, command: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, command)
        self._send()

    def _observe_screen(self) -> None:
        self._quick("mira la pantalla")

    def _stop_mission(self) -> None:
        self._add_message_now("SYSTEM", "MISSION STOP solicitado por interfaz.")
        try:
            self.stop_mission_callback()
        except Exception as exc:
            self._add_message_now("SYSTEM", f"No pude detener la misión: {exc}")

    def _new_session(self) -> None:
        try:
            self.brain.reset_conversation()
        except Exception:
            pass
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
