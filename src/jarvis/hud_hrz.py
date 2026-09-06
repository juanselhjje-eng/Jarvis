from __future__ import annotations

import math
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

from .hrz_features import FeatureHub, ReminderItem

BG = "#050608"
BG2 = "#080b0f"
PANEL = "#0b0e12"
PANEL_HI = "#11161c"
LINE = "#1b242c"
CYAN = "#12dbe8"
CYAN_DIM = "#087e88"
WHITE = "#f0f4f6"
MUTED = "#68727b"
GREEN = "#42e69b"
AMBER = "#f0bd45"
RED = "#ed6375"


class JarvisHRZHUD:
    """Interfaz nativa inspirada en el flujo visual de JARVIS-HRZ."""

    def __init__(
        self,
        brain,
        voice,
        process_command: Callable[[str], None],
        shutdown: Callable[[], None],
        evidence=None,
        execution=None,
    ) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.features = FeatureHub()
        self.running = True
        self.state = "ESCUCHANDO"
        self.phase = 0.0
        self.chat_messages: list[tuple[str, str]] = []
        self._reminder_stop = threading.Event()
        self._build_window()
        self._build()
        self._animate()
        self._clock()
        self._telemetry()
        threading.Thread(target=self.features.reminder_loop, args=(self._reminder_fired, self._reminder_stop), daemon=True, name="jarvis-reminders").start()

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("JARVIS AI")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 720)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _label(self, parent, text, size=9, fg=WHITE, bg=None, bold=False) -> tk.Label:
        return tk.Label(parent, text=text, fg=fg, bg=bg or parent.cget("bg"), font=("Segoe UI", size, "bold" if bold else "normal"))

    def _panel(self, parent, bg=PANEL) -> tk.Frame:
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def _button(self, parent, text, command, width=None, active=None) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, width=width,
            bg=PANEL, fg=WHITE, activebackground=active or "#12232a", activeforeground=CYAN,
            relief="flat", bd=0, font=("Segoe UI", 9), cursor="hand2", padx=8, pady=7,
        )

    def _build(self) -> None:
        self._build_topbar()
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, weight=0, minsize=54)
        main.grid_columnconfigure(1, weight=0, minsize=245)
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)
        self._build_icon_rail(main)
        self._build_sidebar(main)
        self._build_workspace(main)
        self._build_alert_bar()

    def _build_topbar(self) -> None:
        top = tk.Frame(self.root, bg="#07090c", height=40)
        top.pack(fill="x")
        top.pack_propagate(False)
        self._label(top, "◉  JARVIS AI", 9, WHITE, top["bg"], True).pack(side="left", padx=16)
        self._label(top, "Asistente IA", 8, MUTED, top["bg"]).pack(side="left")
        self._label(top, "JARVIS-HRZ", 8, CYAN, top["bg"], True).pack(side="right", padx=14)
        self.clock = self._label(top, "--:--", 8, WHITE, top["bg"], True)
        self.clock.pack(side="right", padx=10)
        self._button(top, "⚙", self._open_settings, width=3).pack(side="right", padx=4, pady=4)

    def _build_icon_rail(self, main: tk.Frame) -> None:
        rail = tk.Frame(main, bg="#07090c")
        rail.grid(row=0, column=0, sticky="nsew")
        icons = [
            ("⌂", lambda: self._set_workspace("Inicio")),
            ("▢", lambda: self._set_workspace("Mis Chats")),
            ("✓", lambda: self._set_workspace("Tareas")),
            ("◷", lambda: self._set_workspace("Recordatorios")),
            ("G", lambda: self._set_workspace("Gmail")),
            ("➤", lambda: self._set_workspace("Telegram")),
            ("◉", lambda: self._set_workspace("GitHub")),
            ("⌁", lambda: self._set_workspace("Noticias")),
            ("☼", lambda: self._set_workspace("Clima")),
            ("⚙", self._open_settings),
        ]
        for symbol, command in icons:
            self._button(rail, symbol, command, width=3).pack(fill="x", padx=7, pady=5)

    def _build_sidebar(self, main: tk.Frame) -> None:
        side = tk.Frame(main, bg="#080a0d")
        side.grid(row=0, column=1, sticky="nsew")
        self.workspace_title = self._label(side, "Mis Chats", 14, WHITE, side["bg"], True)
        self.workspace_title.pack(anchor="w", padx=13, pady=(16, 11))
        self._button(side, "Nueva conversación       +", self._new_chat).pack(fill="x", padx=8, pady=(0, 10))
        self.search = tk.Entry(side, bg="#101419", fg=MUTED, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 9))
        self.search.pack(fill="x", padx=8, ipady=8)
        self.search.insert(0, "⌕  Buscar en chats...")

        self.chat_card = tk.Frame(side, bg="#07131a", highlightthickness=1, highlightbackground="#0a5363")
        self.chat_card.pack(fill="x", padx=8, pady=12)
        self._label(self.chat_card, "◉   JARVIS", 10, CYAN, self.chat_card["bg"], True).pack(anchor="w", padx=12, pady=(10, 2))
        self._label(self.chat_card, "Sesión actual", 8, MUTED, self.chat_card["bg"]).pack(anchor="w", padx=12, pady=(0, 10))

        self.sidebar_info = self._panel(side, "#0a0d11")
        self.sidebar_info.pack(fill="x", padx=8, pady=(0, 8))
        self._label(self.sidebar_info, "CENTRO DE CONTROL", 8, CYAN, self.sidebar_info["bg"], True).pack(anchor="w", padx=10, pady=(10, 6))
        self.stats_label = self._label(self.sidebar_info, "", 8, MUTED, self.sidebar_info["bg"])
        self.stats_label.pack(anchor="w", padx=10, pady=(0, 10))
        self._refresh_stats()

        self._label(side, "Integraciones", 8, MUTED, side["bg"], True).pack(anchor="w", padx=13, pady=(15, 5))
        for name in ("Gmail", "Google Calendar", "Telegram", "GitHub"):
            row = tk.Frame(side, bg=side["bg"]); row.pack(fill="x", padx=12, pady=2)
            self._label(row, "●", 8, CYAN_DIM, row["bg"], True).pack(side="left")
            self._label(row, name, 8, MUTED, row["bg"]).pack(side="left", padx=7)

    def _build_workspace(self, main: tk.Frame) -> None:
        work = tk.Frame(main, bg=BG)
        work.grid(row=0, column=2, sticky="nsew")
        work.grid_rowconfigure(0, weight=1)
        work.grid_rowconfigure(1, weight=0)
        work.grid_columnconfigure(0, weight=1)

        self.content = tk.Frame(work, bg=BG)
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self._build_home()

        composer = tk.Frame(work, bg=BG)
        composer.grid(row=1, column=0, sticky="ew", padx=22, pady=(8, 18))
        composer.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(composer, bg="#11151a", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=11)
        self.entry.bind("<Return>", lambda _e: self._send())
        self.entry.insert(0, "Escribe una orden para JARVIS…")
        self.entry.config(fg=MUTED)
        self.entry.bind("<FocusIn>", self._placeholder)
        self._button(composer, "▣", self._voice, width=4).grid(row=0, column=1, padx=6)
        self._button(composer, "Enviar", self._send).grid(row=0, column=2)

    def _build_home(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(self.content, bg=BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        self.core_canvas = canvas

        self._label(self.content, "JARVIS-HRZ", 10, WHITE, BG, True).place(x=28, y=24)
        self._label(self.content, "Asistente IA", 8, MUTED, BG).place(x=28, y=44)
        self._label(self.content, "v3.1.0  •  CORE ONLINE", 8, CYAN, BG, True).place(relx=1.0, x=-28, y=30, anchor="ne")

        self.state_big = self._label(self.content, self.state, 10, CYAN, BG, True)
        self.state_big.place(relx=0.5, rely=0.70, anchor="center")
        self._label(self.content, "MEMORIA LOCAL  •  VOZ  •  PLANIFICACIÓN  •  CONTROL", 7, MUTED, BG).place(relx=0.5, rely=0.75, anchor="center")

    def _build_alert_bar(self) -> None:
        self.alert = tk.Frame(self.root, bg="#0d1419", height=42)
        self.alert.pack(fill="x", side="bottom")
        self.alert.pack_propagate(False)
        self.alert_text = self._label(self.alert, "Sistemas listos. No hay avisos pendientes.", 8, MUTED, self.alert["bg"])
        self.alert_text.pack(side="left", padx=18, fill="y", pady=11)
        self._button(self.alert, "Ocultar", self._hide_alert, width=7).pack(side="right", padx=6, pady=4)

    def _draw_core(self) -> None:
        c = self.core_canvas
        if not c.winfo_exists():
            return
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 480)
        cx, cy = w * 0.5, h * 0.46
        base = min(w, h) * 0.20
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BG, outline="")
        # rejilla discreta
        for x in range(0, w, 48):
            c.create_line(x, 0, x, h, fill="#0b1116")
        for y in range(0, h, 48):
            c.create_line(0, y, w, y, fill="#0b1116")
        # anillos cinemáticos
        for i in range(7):
            radius = base + i * 13 + math.sin(self.phase * (1 + i * 0.08)) * 4
            c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=CYAN_DIM if i % 2 else CYAN, width=2 if i == 0 else 1)
        for i in range(40):
            a = i * (math.tau / 40) + self.phase * (0.4 if i % 2 else -0.25)
            r = base * (0.72 + 0.26 * math.sin(i * 4.1 + self.phase * 2))
            x = cx + math.cos(a) * r; y = cy + math.sin(a) * r
            c.create_oval(x-1.4, y-1.4, x+1.4, y+1.4, fill=CYAN, outline="")
        c.create_oval(cx-base*0.68, cy-base*0.68, cx+base*0.68, cy+base*0.68, fill="#050b0e", outline=CYAN_DIM, width=2)
        c.create_text(cx, cy-8, text="JARVIS", fill=WHITE, font=("Segoe UI", 15, "bold"))
        c.create_text(cx, cy+15, text=self.state, fill=CYAN, font=("Segoe UI", 9, "bold"))
        c.create_text(24, h-30, text=f"AI CORE  {self.brain.provider.upper()}    •    {self._model_name()}", anchor="w", fill=MUTED, font=("Consolas", 8))
        c.create_text(w-24, h-30, text="MIC LOCAL  •  MEMORY LOCAL", anchor="e", fill=MUTED, font=("Consolas", 8))

    def _model_name(self) -> str:
        config = getattr(self.brain, "config", None)
        if self.brain.provider == "gemini":
            return str(getattr(config, "gemini_model", "gemini"))
        return str(getattr(config, "ollama_model", "ollama"))

    def _animate(self) -> None:
        if not self.running:
            return
        self.phase += 0.035
        self._draw_core()
        self.root.after(40, self._animate)

    def _clock(self) -> None:
        if not self.running:
            return
        self.clock.config(text=datetime.now().strftime("%H:%M"))
        self.root.after(1000, self._clock)

    def _telemetry(self) -> None:
        if not self.running:
            return
        total, done, reminders = self.features.counts()
        cpu = psutil.cpu_percent() if psutil else 0
        ram = psutil.virtual_memory().percent if psutil else 0
        self.stats_label.config(text=f"CPU {cpu:.0f}%   RAM {ram:.0f}%\nTareas {done}/{total}   Avisos {reminders}\n{self.state}  •  {self._model_name()}")
        self.root.after(2000, self._telemetry)

    def _placeholder(self, _event=None) -> None:
        if self.entry.get().startswith("Escribe una orden"):
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text or text.startswith("Escribe una orden"):
            return
        self.entry.delete(0, "end")
        self.add_message("TÚ", text)
        self.set_state("PROCESANDO")
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _voice(self) -> None:
        self.set_state("ESCUCHANDO")
        self.show_alert("Escuchando… habla ahora.", CYAN)
        threading.Thread(target=self._voice_worker, daemon=True, name="jarvis-manual-voice").start()

    def _voice_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.root.after(0, lambda: self.add_message("TÚ", command))
                self.process_command(command)
            else:
                self.root.after(0, lambda: self.set_state("ESCUCHANDO"))
        except Exception as exc:
            self.root.after(0, lambda: self.show_alert(f"Error de voz: {exc}", RED))
            self.root.after(0, lambda: self.set_state("ESCUCHANDO"))

    def add_message(self, role: str, text: str) -> None:
        self.chat_messages.append((role, text))
        self.chat_messages = self.chat_messages[-20:]
        if role == "JARVIS":
            self.show_alert(text[:160], CYAN)

    def set_response(self, text: str) -> None:
        self.root.after(0, lambda: self.add_message("JARVIS", text))
        self.root.after(0, lambda: self.set_state("ESCUCHANDO"))

    def set_state(self, state: str) -> None:
        self.state = state.upper()
        if hasattr(self, "state_big"):
            self.root.after(0, lambda: self.state_big.config(text=self.state, fg=CYAN if self.state != "ERROR" else RED))

    def update_provider(self) -> None:
        self.set_state("ESCUCHANDO")
        self._draw_core()

    def _refresh_stats(self) -> None:
        total, done, reminders = self.features.counts()
        if hasattr(self, "stats_label"):
            self.stats_label.config(text=f"CPU --%   RAM --%\nTareas {done}/{total}   Avisos {reminders}\n{self.state}")

    def show_alert(self, text: str, color: str = CYAN) -> None:
        self.alert_text.config(text=text, fg=color)
        self.alert.config(bg="#10171d")
        self.root.after(7000, self._hide_alert)

    def _hide_alert(self) -> None:
        if self.running:
            self.alert_text.config(text="Sistemas listos. No hay avisos pendientes.", fg=MUTED)
            self.alert.config(bg="#0d1419")

    def _reminder_fired(self, reminder: ReminderItem) -> None:
        self.root.after(0, lambda: self.show_alert(f"AVISO: {reminder.title}", AMBER))
        self.root.after(0, lambda: messagebox.showinfo("JARVIS — Aviso", reminder.title, parent=self.root))

    def _set_workspace(self, name: str) -> None:
        if name == "Inicio" or name == "Mis Chats":
            self.workspace_title.config(text=name)
            self._build_home()
            return
        self.workspace_title.config(text=name)
        self._show_module(name)

    def _show_module(self, name: str) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        title = self._label(self.content, name, 22, WHITE, BG, True)
        title.pack(anchor="w", padx=28, pady=(28, 5))
        self._label(self.content, self._module_description(name), 9, MUTED, BG).pack(anchor="w", padx=28, pady=(0, 18))
        if name == "Tareas":
            self._tasks_module()
        elif name == "Recordatorios":
            self._reminders_module()
        else:
            self._integration_module(name)

    def _module_description(self, name: str) -> str:
        return {
            "Tareas": "Organiza, prioriza y marca tareas como completadas.",
            "Recordatorios": "Avisos locales persistentes con fecha y hora.",
            "Gmail": "Borradores y envío mediante OAuth, siempre con confirmación.",
            "Google Calendar": "Eventos y recordatorios sincronizados mediante OAuth.",
            "Telegram": "Control remoto del asistente mediante un bot autorizado.",
            "GitHub": "Repositorios, ramas, commits y automatizaciones autorizadas.",
            "Noticias": "Panel preparado para fuentes de noticias y mapa de eventos.",
            "Clima": "Panel preparado para temperatura, humedad y pronóstico.",
        }.get(name, "Módulo JARVIS-HRZ")

    def _tasks_module(self) -> None:
        box = self._panel(self.content, "#080c10"); box.pack(fill="x", padx=28)
        entry = tk.Entry(box, bg="#11161b", fg=WHITE, relief="flat", bd=0, font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True, padx=10, pady=10, ipady=8)
        entry.insert(0, "Nueva tarea…")
        def add():
            title = entry.get().strip()
            if title and title != "Nueva tarea…":
                self.features.add_task(title)
                entry.delete(0, "end"); self._show_module("Tareas"); self.show_alert("Tarea guardada.", GREEN)
        self._button(box, "Agregar", add).pack(side="right", padx=8, pady=7)
        for i, task in enumerate(self.features.tasks):
            row = self._panel(self.content, "#0a0e12"); row.pack(fill="x", padx=28, pady=4)
            symbol = "✓" if task.done else "○"
            self._label(row, symbol, 10, GREEN if task.done else MUTED, row["bg"], True).pack(side="left", padx=12, pady=10)
            self._label(row, task.title, 9, WHITE if not task.done else MUTED, row["bg"], True).pack(side="left", pady=10)
            if not task.done:
                self._button(row, "Completar", lambda idx=i: self._complete_task(idx)).pack(side="right", padx=8, pady=4)

    def _complete_task(self, index: int) -> None:
        self.features.complete_task(index)
        self._show_module("Tareas")
        self.show_alert("Tarea completada.", GREEN)

    def _reminders_module(self) -> None:
        box = self._panel(self.content, "#080c10"); box.pack(fill="x", padx=28)
        title = tk.Entry(box, bg="#11161b", fg=WHITE, relief="flat", bd=0, font=("Segoe UI", 9)); title.pack(side="left", fill="x", expand=True, padx=8, pady=10, ipady=8); title.insert(0, "Aviso…")
        when = tk.Entry(box, bg="#11161b", fg=WHITE, relief="flat", bd=0, width=20, font=("Consolas", 8)); when.pack(side="left", padx=5, pady=10, ipady=8); when.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        def add():
            try:
                parsed = datetime.strptime(when.get().strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                self.show_alert("Formato: YYYY-MM-DD HH:MM", RED); return
            self.features.add_reminder(title.get(), parsed.isoformat(timespec="minutes")); self._show_module("Recordatorios"); self.show_alert("Aviso programado.", GREEN)
        self._button(box, "Programar", add).pack(side="right", padx=8, pady=7)
        for item in self.features.reminders:
            if item.fired: continue
            row = self._panel(self.content, "#0a0e12"); row.pack(fill="x", padx=28, pady=4)
            self._label(row, "◷", 10, AMBER, row["bg"], True).pack(side="left", padx=12, pady=10)
            self._label(row, f"{item.title}   •   {item.when}", 9, WHITE, row["bg"]).pack(side="left", pady=10)

    def _integration_module(self, name: str) -> None:
        status = self.features.integration_status().get(name, "Módulo local")
        box = self._panel(self.content, "#080c10"); box.pack(fill="x", padx=28, pady=5)
        self._label(box, "ESTADO", 8, CYAN, box["bg"], True).pack(anchor="w", padx=14, pady=(14, 3))
        self._label(box, status, 10, WHITE, box["bg"], True).pack(anchor="w", padx=14, pady=(0, 14))
        self._label(box, "La interfaz y el punto de integración están listos. Las cuentas externas requieren su autorización normal; JARVIS no saltará autenticaciones.", 8, MUTED, box["bg"]).pack(anchor="w", padx=14, pady=(0, 14))
        self._button(box, "Abrir módulo", lambda: self.process_command(f"abre {name}")).pack(anchor="w", padx=14, pady=(0, 14))

    def _open_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Configuración")
        win.configure(bg="#0b0e12")
        win.geometry("940x620")
        win.transient(self.root)
        win.grab_set()
        win.grid_columnconfigure(1, weight=1); win.grid_rowconfigure(0, weight=1)
        nav = tk.Frame(win, bg="#080a0d", width=220); nav.grid(row=0, column=0, sticky="nsew"); nav.grid_propagate(False)
        body = tk.Frame(win, bg="#0d1116"); body.grid(row=0, column=1, sticky="nsew")
        self._label(nav, "Configuración", 15, WHITE, nav["bg"], True).pack(anchor="w", padx=18, pady=(22, 20))
        categories = ["Modelos de IA", "Ubicación", "Voz y audio", "Apariencia y trato", "Control y accesos", "Cuenta y datos"]
        for category in categories:
            self._button(nav, category, lambda c=category: self._settings_page(body, c)).pack(fill="x", padx=10, pady=2)
        self._settings_page(body, "Voz y audio")

    def _settings_page(self, body: tk.Frame, category: str) -> None:
        for child in body.winfo_children(): child.destroy()
        self._label(body, category, 17, WHITE, body["bg"], True).pack(anchor="w", padx=24, pady=(22, 4))
        self._label(body, "Configura cómo JARVIS escucha, responde y ejecuta acciones.", 8, MUTED, body["bg"]).pack(anchor="w", padx=24, pady=(0, 18))
        if category == "Voz y audio":
            self._setting_row(body, "Lectura de voz", "JARVIS responde también por voz", True)
            self._setting_row(body, "Escucha continua", "Reconoce la palabra JARVIS desde el micrófono local", True)
            self._setting_row(body, "Micrófono", "Predeterminado del sistema", False)
            self._setting_row(body, "Idioma", "Español", False)
        elif category == "Modelos de IA":
            self._setting_row(body, "Proveedor principal", self.brain.provider.upper(), False)
            self._setting_row(body, "Modelo", self._model_name(), False)
            self._setting_row(body, "Respaldo local", "Ollama", False)
        elif category == "Control y accesos":
            self._setting_row(body, "Confirmación externa", "Siempre antes de enviar mensajes/correos", True)
            self._setting_row(body, "Control visible del escritorio", "Activo cuando se solicite", True)
            self._setting_row(body, "Captura de credenciales", "Desactivada", False)
        elif category == "Apariencia y trato":
            self._setting_row(body, "Tema", "Oscuro / JARVIS-HRZ", False)
            self._setting_row(body, "Interfaz", "Centro de control", False)
        elif category == "Ubicación":
            self._setting_row(body, "Ubicación", "Configurable para clima y noticias", False)
            self._setting_row(body, "Privacidad", "No se muestra la dirección exacta", False)
        else:
            self._setting_row(body, "Memoria", "Local", False)
            self._setting_row(body, "Datos", "Guardados en data/", False)

    def _setting_row(self, parent: tk.Frame, title: str, value: str, toggle: bool) -> None:
        row = self._panel(parent, "#10151a"); row.pack(fill="x", padx=24, pady=5)
        self._label(row, title, 9, WHITE, row["bg"], True).pack(anchor="w", padx=12, pady=(9, 1))
        self._label(row, value, 8, MUTED, row["bg"]).pack(anchor="w", padx=12, pady=(0, 9))
        if toggle:
            self._label(row, "● ACTIVADO", 7, GREEN, row["bg"], True).pack(side="right", padx=12, pady=12)

    def _new_chat(self) -> None:
        self.chat_messages.clear()
        try: self.brain.reset_conversation()
        except Exception: pass
        self._build_home()
        self.show_alert("Nueva conversación iniciada.", GREEN)

    def _close(self) -> None:
        if not self.running:
            return
        self.running = False
        self._reminder_stop.set()
        try:
            self.shutdown_callback()
        finally:
            try: self.root.destroy()
            except tk.TclError: pass

    def run(self) -> None:
        self.root.mainloop()
