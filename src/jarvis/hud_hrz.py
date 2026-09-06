from __future__ import annotations

import math
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

from .hrz_features import FeatureHub, ReminderItem

BG = "#050607"
BG_SOFT = "#080b0e"
PANEL = "#0b0f13"
PANEL_2 = "#0e1419"
LINE = "#1b252c"
CYAN = "#13dbe7"
CYAN_2 = "#087f89"
WHITE = "#edf3f5"
MUTED = "#6d7982"
GREEN = "#3fe3a0"
AMBER = "#f1bd4b"
RED = "#ed6476"


class JarvisHRZHUD:
    """HUD nativo para una experiencia JARVIS tipo HRZ / Mission Control."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.features = FeatureHub()
        self.running = True
        self.state = "STANDBY"
        self.phase = 0.0
        self.chat_messages: list[tuple[str, str]] = []
        self.active_module = "Inicio"
        self._reminder_stop = threading.Event()
        self._build_window()
        self._build()
        self._animate()
        self._clock()
        self._telemetry()
        threading.Thread(target=self.features.reminder_loop, args=(self._reminder_fired, self._reminder_stop), daemon=True).start()

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("JARVIS AI — Mission Control")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 720)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _label(self, parent, text, size=9, fg=WHITE, bg=None, bold=False, anchor="w"):
        return tk.Label(parent, text=text, fg=fg, bg=bg or parent.cget("bg"), font=("Segoe UI", size, "bold" if bold else "normal"), anchor=anchor)

    def _panel(self, parent, bg=PANEL):
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def _button(self, parent, text, command, width=None, active="#12232a"):
        return tk.Button(parent, text=text, command=command, width=width, bg=PANEL, fg=WHITE, activebackground=active, activeforeground=CYAN, relief="flat", bd=0, font=("Segoe UI", 9), cursor="hand2", padx=8, pady=7)

    def _build(self) -> None:
        self._build_topbar()
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, minsize=56)
        main.grid_columnconfigure(1, minsize=255)
        main.grid_columnconfigure(2, weight=1)
        main.grid_columnconfigure(3, minsize=235)
        main.grid_rowconfigure(0, weight=1)
        self._build_rail(main)
        self._build_sidebar(main)
        self._build_workspace(main)
        self._build_mission_panel(main)
        self._build_alert_bar()

    def _build_topbar(self) -> None:
        top = tk.Frame(self.root, bg="#07090b", height=42, highlightthickness=1, highlightbackground="#11181d")
        top.pack(fill="x")
        top.pack_propagate(False)
        self._label(top, "◉  JARVIS AI", 9, WHITE, top["bg"], True).pack(side="left", padx=16)
        self._label(top, "MISSION CONTROL", 8, CYAN, top["bg"], True).pack(side="left", padx=12)
        self._label(top, "CORE ONLINE", 8, GREEN, top["bg"], True).pack(side="right", padx=12)
        self.clock = self._label(top, "--:--:--", 8, WHITE, top["bg"], True)
        self.clock.pack(side="right", padx=8)
        self._button(top, "⚙", self._open_settings, width=3).pack(side="right", padx=5, pady=5)

    def _build_rail(self, main) -> None:
        rail = tk.Frame(main, bg="#07090c")
        rail.grid(row=0, column=0, sticky="nsew")
        items = [
            ("⌂", "Inicio"), ("▢", "Mis Chats"), ("✓", "Tareas"), ("◷", "Recordatorios"),
            ("G", "Gmail"), ("C", "Google Calendar"), ("➤", "Telegram"), ("◉", "GitHub"),
            ("⌁", "Noticias"), ("☼", "Clima"), ("⚙", "Configuración"),
        ]
        self.rail_buttons = {}
        for icon, name in items:
            btn = self._button(rail, icon, lambda n=name: self._set_workspace(n), width=3)
            btn.pack(fill="x", padx=7, pady=4)
            self.rail_buttons[name] = btn

    def _build_sidebar(self, main) -> None:
        side = tk.Frame(main, bg="#080a0d")
        side.grid(row=0, column=1, sticky="nsew")
        self.workspace_title = self._label(side, "Mis Chats", 14, WHITE, side["bg"], True)
        self.workspace_title.pack(anchor="w", padx=14, pady=(17, 10))
        self._button(side, "Nueva conversación                         +", self._new_chat).pack(fill="x", padx=9, pady=(0, 9))
        search_box = tk.Frame(side, bg="#101419")
        search_box.pack(fill="x", padx=9)
        self.search = tk.Entry(search_box, bg="#101419", fg=MUTED, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 9))
        self.search.pack(fill="x", padx=9, ipady=8)
        self.search.insert(0, "Buscar en chats...")
        self.search.bind("<FocusIn>", lambda _e: self._clear_placeholder(self.search, "Buscar en chats..."))

        self.chat_list = tk.Frame(side, bg=side["bg"])
        self.chat_list.pack(fill="both", expand=False, padx=9, pady=12)
        self._refresh_chat_list()

        self._label(side, "CENTRO DE CONTROL", 8, CYAN, side["bg"], True).pack(anchor="w", padx=14, pady=(5, 6))
        self.stats_label = self._label(side, "", 8, MUTED, side["bg"])
        self.stats_label.pack(anchor="w", padx=14)

        self._label(side, "INTEGRACIONES", 8, MUTED, side["bg"], True).pack(anchor="w", padx=14, pady=(18, 5))
        self.integration_labels = {}
        for name in ("Gmail", "Google Calendar", "Telegram", "GitHub"):
            row = tk.Frame(side, bg=side["bg"])
            row.pack(fill="x", padx=14, pady=2)
            dot = self._label(row, "●", 8, CYAN_2, row["bg"], True)
            dot.pack(side="left")
            self._label(row, name, 8, MUTED, row["bg"]).pack(side="left", padx=7)
            self.integration_labels[name] = dot

    def _refresh_chat_list(self) -> None:
        for child in self.chat_list.winfo_children():
            child.destroy()
        title = "Sesión actual" if not self.chat_messages else (self.chat_messages[-1][1][:34] + ("…" if len(self.chat_messages[-1][1]) > 34 else ""))
        card = tk.Frame(self.chat_list, bg="#07141a", highlightthickness=1, highlightbackground="#0b5a68")
        card.pack(fill="x")
        self._label(card, "◉   JARVIS", 10, CYAN, card["bg"], True).pack(anchor="w", padx=12, pady=(10, 2))
        self._label(card, title, 8, MUTED, card["bg"]).pack(anchor="w", padx=12, pady=(0, 10))
        if self.chat_messages:
            self._label(self.chat_list, f"{len(self.chat_messages)} mensajes en esta sesión", 8, MUTED, self.chat_list["bg"]).pack(anchor="w", padx=5, pady=(8, 2))

    def _build_workspace(self, main) -> None:
        work = tk.Frame(main, bg=BG)
        work.grid(row=0, column=2, sticky="nsew")
        work.grid_rowconfigure(0, weight=1)
        work.grid_rowconfigure(1, minsize=78)
        work.grid_columnconfigure(0, weight=1)
        self.content = tk.Frame(work, bg=BG)
        self.content.grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self._build_home()

        composer = tk.Frame(work, bg=BG)
        composer.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 17))
        composer.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(composer, bg="#11161b", fg=MUTED, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=12)
        self.entry.insert(0, "Escribe una orden para JARVIS…")
        self.entry.bind("<FocusIn>", self._entry_focus)
        self.entry.bind("<Return>", lambda _e: self._send())
        self._button(composer, "◉", self._voice, width=4).grid(row=0, column=1, padx=5)
        self._button(composer, "Enviar", self._send).grid(row=0, column=2)
        self._label(composer, "Enter para enviar  •  micrófono para hablar  •  JARVIS puede planificar tareas", 7, MUTED, BG).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _build_mission_panel(self, main) -> None:
        panel = tk.Frame(main, bg="#080b0e")
        panel.grid(row=0, column=3, sticky="nsew")
        self._label(panel, "MISSION CONTROL", 11, WHITE, panel["bg"], True).pack(anchor="w", padx=14, pady=(17, 3))
        self._label(panel, "Estado operativo en tiempo real", 7, MUTED, panel["bg"]).pack(anchor="w", padx=14, pady=(0, 14))

        self.status_card = self._panel(panel, "#091116")
        self.status_card.pack(fill="x", padx=10, pady=4)
        self.status_big = self._label(self.status_card, self.state, 15, CYAN, self.status_card["bg"], True)
        self.status_big.pack(anchor="w", padx=12, pady=(12, 1))
        self.status_detail = self._label(self.status_card, "Sistema preparado", 8, MUTED, self.status_card["bg"])
        self.status_detail.pack(anchor="w", padx=12, pady=(0, 12))

        self._label(panel, "ACTIVIDAD", 8, CYAN, panel["bg"], True).pack(anchor="w", padx=14, pady=(15, 6))
        self.activity = tk.Text(panel, height=10, bg="#06090c", fg=MUTED, insertbackground=CYAN, relief="flat", bd=0, font=("Consolas", 8), state="disabled")
        self.activity.pack(fill="x", padx=10)

        self._label(panel, "ACCIONES RÁPIDAS", 8, CYAN, panel["bg"], True).pack(anchor="w", padx=14, pady=(16, 6))
        quick = tk.Frame(panel, bg=panel["bg"])
        quick.pack(fill="x", padx=10)
        for text, cmd in (("Estado del PC", "revisa mi pc"), ("Abrir Google", "abre google"), ("Optimizar", "optimiza mi pc"), ("Memoria", "qué recuerdas de mí")):
            self._button(quick, text, lambda c=cmd: self._quick_command(c)).pack(fill="x", pady=2)

        self._label(panel, "EVIDENCIA", 8, CYAN, panel["bg"], True).pack(anchor="w", padx=14, pady=(16, 5))
        self.evidence_label = self._label(panel, "Sin misión activa.", 8, MUTED, panel["bg"])
        self.evidence_label.pack(anchor="w", padx=14)

    def _build_alert_bar(self) -> None:
        self.alert = tk.Frame(self.root, bg="#0d151a", height=40)
        self.alert.pack(fill="x", side="bottom")
        self.alert.pack_propagate(False)
        self.alert_text = self._label(self.alert, "Sistemas listos. No hay avisos pendientes.", 8, MUTED, self.alert["bg"])
        self.alert_text.pack(side="left", padx=18, fill="y", pady=10)
        self._button(self.alert, "Ocultar", self._hide_alert, width=7).pack(side="right", padx=6, pady=4)

    def _build_home(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(self.content, bg=BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        self.core_canvas = canvas
        self._label(self.content, "JARVIS-HRZ", 10, WHITE, BG, True).place(x=28, y=24)
        self._label(self.content, "Asistente personal de IA", 8, MUTED, BG).place(x=28, y=44)
        self._label(self.content, "MARK 6  •  CORE ONLINE", 8, CYAN, BG, True).place(relx=1.0, x=-28, y=28, anchor="ne")
        self.state_big = self._label(self.content, self.state, 10, CYAN, BG, True)
        self.state_big.place(relx=0.5, rely=0.73, anchor="center")
        self._label(self.content, "MEMORIA LOCAL   •   VOZ   •   PLANIFICACIÓN   •   CONTROL DEL PC", 7, MUTED, BG).place(relx=0.5, rely=0.78, anchor="center")

    def _draw_core(self) -> None:
        if not hasattr(self, "core_canvas") or not self.core_canvas.winfo_exists():
            return
        c = self.core_canvas
        w, h = max(c.winfo_width(), 700), max(c.winfo_height(), 500)
        cx, cy = w * .5, h * .45
        base = min(w, h) * .19
        c.delete("all")
        for x in range(0, w, 48):
            c.create_line(x, 0, x, h, fill="#0a1014")
        for y in range(0, h, 48):
            c.create_line(0, y, w, y, fill="#0a1014")
        c.create_oval(cx-base*1.85, cy-base*1.85, cx+base*1.85, cy+base*1.85, outline="#071a1f", width=2)
        c.create_oval(cx-base*1.48, cy-base*1.48, cx+base*1.48, cy+base*1.48, outline="#0a3037", width=1)
        for i in range(9):
            radius = base + i * 11 + math.sin(self.phase * (1 + i * .07)) * (3 + i * .25)
            start = (self.phase * (22 + i * 2) + i * 37) % 360
            extent = 245 if i % 3 else 300
            c.create_arc(cx-radius, cy-radius, cx+radius, cy+radius, start=start, extent=extent, style="arc", outline=CYAN if i % 2 == 0 else CYAN_2, width=2 if i in (0, 4) else 1)
        for i in range(80):
            angle = i * math.tau / 80 + self.phase * (.32 if i % 2 else -.22)
            radius = base * (.72 + .28 * math.sin(i * 2.7 + self.phase * 2))
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            size = 1 if i % 3 else 2
            c.create_oval(x-size, y-size, x+size, y+size, fill=CYAN if i % 4 else WHITE, outline="")
        inner = base * (.68 + .025 * math.sin(self.phase * 3))
        c.create_oval(cx-inner, cy-inner, cx+inner, cy+inner, fill="#040a0d", outline=CYAN_2, width=2)
        c.create_oval(cx-inner*.82, cy-inner*.82, cx+inner*.82, cy+inner*.82, outline="#123238", width=1)
        c.create_text(cx, cy-10, text="JARVIS", fill=WHITE, font=("Segoe UI", 17, "bold"))
        c.create_text(cx, cy+15, text=self.state, fill=CYAN if self.state != "ERROR" else RED, font=("Segoe UI", 9, "bold"))
        c.create_text(25, h-28, text=f"AI CORE  {self.brain.provider.upper()}   •   {self._model_name()}", anchor="w", fill=MUTED, font=("Consolas", 8))
        c.create_text(w-25, h-28, text="MIC LOCAL   •   MEMORY LOCAL   •   PC CONTROL", anchor="e", fill=MUTED, font=("Consolas", 8))

    def _model_name(self) -> str:
        config = getattr(self.brain, "config", None)
        if self.brain.provider == "gemini":
            return str(getattr(config, "gemini_model", "gemini"))
        return str(getattr(config, "ollama_model", "ollama"))

    def _animate(self) -> None:
        if not self.running:
            return
        self.phase += .035
        self._draw_core()
        self.root.after(40, self._animate)

    def _clock(self) -> None:
        if self.running:
            self.clock.config(text=datetime.now().strftime("%H:%M:%S"))
            self.root.after(1000, self._clock)

    def _telemetry(self) -> None:
        if not self.running:
            return
        total, done, reminders = self.features.counts()
        cpu = psutil.cpu_percent() if psutil else 0
        ram = psutil.virtual_memory().percent if psutil else 0
        self.stats_label.config(text=f"CPU  {cpu:>3.0f}%    RAM  {ram:>3.0f}%\nTareas  {done}/{total}    Avisos  {reminders}\n{self.state}  •  {self._model_name()}")
        if self.evidence and getattr(self.evidence, "latest", lambda: None)():
            item = self.evidence.latest()
            self.evidence_label.config(text=f"{getattr(item, 'status', 'ACTIVA')}  •  {getattr(item, 'title', '')[:32]}")
        self.root.after(2000, self._telemetry)

    def _entry_focus(self, _event=None) -> None:
        if self.entry.get().startswith("Escribe una orden"):
            self.entry.delete(0, "end")
            self.entry.config(fg=WHITE)

    def _clear_placeholder(self, widget, text: str) -> None:
        if widget.get() == text:
            widget.delete(0, "end")
            widget.config(fg=WHITE)

    def _send(self) -> None:
        text = self.entry.get().strip()
        if not text or text.startswith("Escribe una orden"):
            return
        self.entry.delete(0, "end")
        self.entry.config(fg=WHITE)
        self.add_message("TÚ", text)
        self.set_state("PROCESANDO")
        threading.Thread(target=self.process_command, args=(text,), daemon=True, name="jarvis-command").start()

    def _quick_command(self, command: str) -> None:
        self.add_message("TÚ", command)
        self.set_state("PROCESANDO")
        threading.Thread(target=self.process_command, args=(command,), daemon=True).start()

    def _voice(self) -> None:
        self.set_state("ESCUCHANDO")
        self.show_alert("Escuchando… habla ahora.", CYAN)
        threading.Thread(target=self._voice_worker, daemon=True).start()

    def _voice_worker(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.root.after(0, lambda: self.add_message("TÚ", command))
                self.process_command(command)
            else:
                self.root.after(0, lambda: self.set_state("STANDBY"))
        except Exception as exc:
            self.root.after(0, lambda: self.show_alert(f"Error de voz: {exc}", RED))
            self.root.after(0, lambda: self.set_state("STANDBY"))

    def add_message(self, role: str, text: str) -> None:
        self.chat_messages.append((role, text))
        self.chat_messages = self.chat_messages[-30:]
        self._refresh_chat_list()
        self._activity(f"{role}: {text[:95]}")
        if role == "JARVIS":
            self.show_alert(text[:160], CYAN)

    def set_response(self, text: str) -> None:
        self.root.after(0, lambda: self.add_message("JARVIS", text))
        self.root.after(0, lambda: self.set_state("STANDBY"))

    def set_state(self, state: str) -> None:
        self.state = state.upper()
        if hasattr(self, "state_big"):
            self.root.after(0, lambda: self.state_big.config(text=self.state, fg=RED if self.state == "ERROR" else CYAN))
        if hasattr(self, "status_big"):
            self.root.after(0, lambda: self.status_big.config(text=self.state, fg=RED if self.state == "ERROR" else CYAN))
            self.root.after(0, lambda: self.status_detail.config(text=self._state_detail()))

    def _state_detail(self) -> str:
        return {
            "STANDBY": "Sistema preparado",
            "ESCUCHANDO": "Entrada de voz activa",
            "PROCESANDO": "Ejecutando orden",
            "ANALIZANDO": "Interpretando intención",
            "PENSANDO": "Planificando respuesta",
            "VERIFICANDO": "Comprobando resultado",
            "ERROR": "Requiere atención",
        }.get(self.state, "Sistema activo")

    def update_provider(self) -> None:
        self.set_state("STANDBY")
        self._activity(f"Cerebro cambiado: {self.brain.provider.upper()}")

    def _activity(self, text: str) -> None:
        if not hasattr(self, "activity"):
            return
        def write():
            self.activity.configure(state="normal")
            self.activity.insert("end", f"[{datetime.now():%H:%M:%S}] {text}\n")
            self.activity.see("end")
            self.activity.configure(state="disabled")
        self.root.after(0, write)

    def show_alert(self, text: str, color: str = CYAN) -> None:
        self.alert_text.config(text=text, fg=color)
        self.alert.config(bg="#101a20")
        self.root.after(6500, self._hide_alert)

    def _hide_alert(self) -> None:
        if self.running:
            self.alert_text.config(text="Sistemas listos. No hay avisos pendientes.", fg=MUTED)
            self.alert.config(bg="#0d151a")

    def _reminder_fired(self, reminder: ReminderItem) -> None:
        self.root.after(0, lambda: self.show_alert(f"AVISO: {reminder.title}", AMBER))
        self.root.after(0, lambda: messagebox.showinfo("JARVIS — Aviso", reminder.title, parent=self.root))

    def _set_workspace(self, name: str) -> None:
        self.active_module = name
        if name == "Configuración":
            self._open_settings()
            return
        self.workspace_title.config(text=name if name != "Inicio" else "Mis Chats")
        if name in ("Inicio", "Mis Chats"):
            self._build_home()
        else:
            self._show_module(name)

    def _show_module(self, name: str) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        title = self._label(self.content, name, 22, WHITE, BG, True)
        title.pack(anchor="w", padx=28, pady=(30, 3))
        desc = {
            "Tareas": "Organiza, prioriza y completa misiones.",
            "Recordatorios": "Avisos persistentes con fecha y hora.",
            "Gmail": "Correo preparado para autorización OAuth.",
            "Google Calendar": "Agenda y eventos preparados para OAuth.",
            "Telegram": "Mensajería mediante bot autorizado.",
            "GitHub": "Código y repositorios mediante autorización normal.",
            "Noticias": "Centro de información y búsqueda web.",
            "Clima": "Estado meteorológico y pronóstico.",
        }.get(name, "Módulo JARVIS")
        self._label(self.content, desc, 9, MUTED, BG).pack(anchor="w", padx=28, pady=(0, 18))
        if name == "Tareas":
            self._tasks_module()
        elif name == "Recordatorios":
            self._reminders_module()
        else:
            self._integration_module(name)

    def _tasks_module(self) -> None:
        box = self._panel(self.content, "#080d11")
        box.pack(fill="x", padx=28, pady=3)
        entry = tk.Entry(box, bg="#11171c", fg=WHITE, relief="flat", bd=0, font=("Segoe UI", 9))
        entry.pack(side="left", fill="x", expand=True, padx=10, pady=10, ipady=8)
        entry.insert(0, "Nueva misión…")
        def add():
            title = entry.get().strip()
            if title and title != "Nueva misión…":
                self.features.add_task(title)
                self._show_module("Tareas")
                self.show_alert("Misión guardada.", GREEN)
        self._button(box, "Agregar", add).pack(side="right", padx=8, pady=7)
        for i, task in enumerate(self.features.tasks):
            row = self._panel(self.content, "#0a0e12")
            row.pack(fill="x", padx=28, pady=4)
            self._label(row, "✓" if task.done else "○", 12, GREEN if task.done else MUTED, row["bg"], True).pack(side="left", padx=12, pady=11)
            self._label(row, task.title, 9, MUTED if task.done else WHITE, row["bg"], True).pack(side="left", pady=11)
            if not task.done:
                self._button(row, "Completar", lambda idx=i: self._complete_task(idx)).pack(side="right", padx=8, pady=5)

    def _complete_task(self, index: int) -> None:
        if self.features.complete_task(index):
            self._show_module("Tareas")
            self.show_alert("Misión completada.", GREEN)

    def _reminders_module(self) -> None:
        box = self._panel(self.content, "#080d11")
        box.pack(fill="x", padx=28)
        title = tk.Entry(box, bg="#11171c", fg=WHITE, relief="flat", bd=0, font=("Segoe UI", 9))
        title.pack(side="left", fill="x", expand=True, padx=8, pady=10, ipady=8)
        title.insert(0, "Aviso…")
        when = tk.Entry(box, bg="#11171c", fg=WHITE, relief="flat", bd=0, width=18, font=("Consolas", 8))
        when.pack(side="left", padx=5, pady=10, ipady=8)
        when.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        def add():
            try:
                parsed = datetime.strptime(when.get().strip(), "%Y-%m-%d %H:%M")
            except ValueError:
                self.show_alert("Formato: YYYY-MM-DD HH:MM", RED)
                return
            if not title.get().strip() or title.get().strip() == "Aviso…":
                self.show_alert("Escribe el aviso.", RED)
                return
            self.features.add_reminder(title.get(), parsed.isoformat(timespec="minutes"))
            self._show_module("Recordatorios")
            self.show_alert("Aviso programado.", GREEN)
        self._button(box, "Programar", add).pack(side="right", padx=8, pady=7)
        for item in self.features.reminders:
            if item.fired:
                continue
            row = self._panel(self.content, "#0a0e12")
            row.pack(fill="x", padx=28, pady=4)
            self._label(row, "◷", 11, AMBER, row["bg"], True).pack(side="left", padx=12, pady=11)
            self._label(row, f"{item.title}   •   {item.when}", 9, WHITE, row["bg"]).pack(side="left", pady=11)

    def _integration_module(self, name: str) -> None:
        status = self.features.integration_status().get(name, "Módulo local")
        box = self._panel(self.content, "#080d11")
        box.pack(fill="x", padx=28, pady=4)
        self._label(box, "ESTADO", 8, CYAN, box["bg"], True).pack(anchor="w", padx=14, pady=(14, 3))
        self._label(box, status, 10, WHITE, box["bg"], True).pack(anchor="w", padx=14, pady=(0, 8))
        self._label(box, "La interfaz queda preparada. Las cuentas externas usan su autorización normal; JARVIS no evita autenticaciones ni controles de seguridad.", 8, MUTED, box["bg"]).pack(anchor="w", padx=14, pady=(0, 14))
        command = {"Gmail": "abre gmail", "Google Calendar": "abre calendar", "Telegram": "abre telegram", "GitHub": "abre github", "Noticias": "busca noticias", "Clima": "busca clima"}.get(name)
        if command:
            self._button(box, "Abrir", lambda c=command: self._quick_command(c)).pack(anchor="w", padx=14, pady=(0, 14))

    def _open_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Configuración — JARVIS")
        win.configure(bg="#0a0d10")
        win.geometry("1040x680")
        win.minsize(900, 600)
        win.transient(self.root)
        win.grab_set()
        win.grid_columnconfigure(1, weight=1)
        win.grid_rowconfigure(0, weight=1)

        nav = tk.Frame(win, bg="#080a0d", width=210)
        nav.grid(row=0, column=0, sticky="nsew")
        nav.grid_propagate(False)
        self._label(nav, "Configuración", 16, WHITE, nav["bg"], True).pack(anchor="w", padx=18, pady=(20, 4))
        self._label(nav, "JARVIS-HRZ  •  MARK 6", 8, MUTED, nav["bg"]).pack(anchor="w", padx=18, pady=(0, 22))
        pages = ["Modelos de IA", "Ubicación", "Voz y audio", "Apariencia", "Control y accesos", "Cuenta y datos"]
        body = tk.Frame(win, bg="#0a0d10")
        body.grid(row=0, column=1, sticky="nsew", padx=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        def show(page: str):
            for child in body.winfo_children():
                child.destroy()
            self._label(body, page, 20, WHITE, body["bg"], True).pack(anchor="w", padx=28, pady=(24, 4))
            self._label(body, "Configuración local del centro de control.", 8, MUTED, body["bg"]).pack(anchor="w", padx=28, pady=(0, 18))
            if page == "Modelos de IA":
                self._settings_models(body)
            elif page == "Voz y audio":
                self._settings_voice(body)
            elif page == "Apariencia":
                self._settings_appearance(body)
            elif page == "Control y accesos":
                self._settings_access(body)
            else:
                self._settings_generic(body, page)

        for page in pages:
            self._button(nav, page, lambda p=page: show(p)).pack(fill="x", padx=12, pady=3)
        self._button(nav, "Cerrar", win.destroy).pack(side="bottom", fill="x", padx=12, pady=14)
        show("Modelos de IA")

    def _settings_models(self, parent):
        card = self._panel(parent, PANEL)
        card.pack(fill="x", padx=28, pady=5)
        self._label(card, "CEREBRO PRINCIPAL", 8, CYAN, card["bg"], True).pack(anchor="w", padx=14, pady=(14, 4))
        self._label(card, f"Proveedor activo: {self.brain.provider.upper()}", 10, WHITE, card["bg"], True).pack(anchor="w", padx=14, pady=4)
        self._label(card, f"Modelo: {self._model_name()}", 9, MUTED, card["bg"]).pack(anchor="w", padx=14, pady=(0, 14))
        self._button(card, "Usar Gemini", lambda: self._quick_command("usa gemini")).pack(anchor="w", padx=14, pady=(0, 7))
        self._button(card, "Usar Ollama local", lambda: self._quick_command("usa ollama")).pack(anchor="w", padx=14, pady=(0, 14))

    def _settings_voice(self, parent):
        card = self._panel(parent, PANEL); card.pack(fill="x", padx=28, pady=5)
        self._label(card, "VOZ Y AUDIO", 8, CYAN, card["bg"], True).pack(anchor="w", padx=14, pady=(14, 5))
        self._label(card, "Reconocimiento local por Whisper cuando está disponible.", 9, WHITE, card["bg"]).pack(anchor="w", padx=14, pady=3)
        self._label(card, "Lectura de respuestas: activa desde el motor de voz.", 9, MUTED, card["bg"]).pack(anchor="w", padx=14, pady=(0, 14))

    def _settings_appearance(self, parent):
        card = self._panel(parent, PANEL); card.pack(fill="x", padx=28, pady=5)
        self._label(card, "APARIENCIA", 8, CYAN, card["bg"], True).pack(anchor="w", padx=14, pady=(14, 5))
        self._label(card, "Tema actual: Mission Control / oscuro", 10, WHITE, card["bg"], True).pack(anchor="w", padx=14, pady=4)
        self._label(card, "Núcleo cian, rejilla técnica, paneles compactos y estados operativos.", 8, MUTED, card["bg"]).pack(anchor="w", padx=14, pady=(0, 14))

    def _settings_access(self, parent):
        card = self._panel(parent, PANEL); card.pack(fill="x", padx=28, pady=5)
        self._label(card, "CONTROL Y ACCESOS", 8, CYAN, card["bg"], True).pack(anchor="w", padx=14, pady=(14, 5))
        self._label(card, "Control visible del escritorio: preparado", 9, WHITE, card["bg"]).pack(anchor="w", padx=14, pady=3)
        self._label(card, "Acciones externas y comunicaciones mantienen confirmación antes de enviar.", 8, MUTED, card["bg"]).pack(anchor="w", padx=14, pady=(0, 14))

    def _settings_generic(self, parent, page):
        card = self._panel(parent, PANEL); card.pack(fill="x", padx=28, pady=5)
        self._label(card, page.upper(), 8, CYAN, card["bg"], True).pack(anchor="w", padx=14, pady=(14, 5))
        self._label(card, "Módulo de configuración preparado para la siguiente integración.", 9, WHITE, card["bg"]).pack(anchor="w", padx=14, pady=(0, 14))

    def _new_chat(self) -> None:
        self.chat_messages.clear()
        self._refresh_chat_list()
        self._build_home()
        self.show_alert("Nueva conversación iniciada.", GREEN)

    def run(self) -> None:
        self.root.mainloop()

    def _close(self) -> None:
        if not self.running:
            return
        self.running = False
        self._reminder_stop.set()
        try:
            self.shutdown_callback()
        finally:
            self.root.destroy()
