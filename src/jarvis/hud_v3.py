from __future__ import annotations

import math
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

from .hrz_features import FeatureHub, ReminderItem

BG = "#020508"
PANEL = "#071016"
PANEL2 = "#0a151c"
LINE = "#18313a"
CYAN = "#21e5f1"
CYAN_D = "#0a7e89"
WHITE = "#edf8fa"
MUTED = "#718991"
GREEN = "#45e0a4"
AMBER = "#f0bd50"
RED = "#e86778"


class JarvisHUDv3:
    """Interfaz nativa de Mission Control: módulos funcionales y estado operativo en tiempo real."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.features = FeatureHub()
        self.running = True
        self.state = "STANDBY"
        self.module = "Inicio"
        self.phase = 0.0
        self.messages: list[tuple[str, str]] = []
        self._reminder_stop = threading.Event()
        self._build()
        threading.Thread(target=self.features.reminder_loop, args=(self._reminder_fired, self._reminder_stop), daemon=True).start()
        self._tick()

    def _build(self):
        self.root = tk.Tk()
        self.root.title("JARVIS — Mission Control")
        self.root.configure(bg=BG)
        self.root.minsize(1280, 780)
        try: self.root.state("zoomed")
        except tk.TclError: self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        top = tk.Frame(self.root, bg="#050a0e", height=54, highlightthickness=1, highlightbackground=LINE); top.pack(fill="x"); top.pack_propagate(False)
        self._label(top, "◉  J.A.R.V.I.S", 12, WHITE, True).pack(side="left", padx=20)
        self._label(top, "PERSONAL INTELLIGENCE SYSTEM", 8, CYAN, True).pack(side="left", padx=14)
        self.top_alert = self._label(top, "● ALL SYSTEMS NOMINAL", 8, GREEN, True); self.top_alert.pack(side="right", padx=20)
        self.clock = self._label(top, "--:--:--", 9, WHITE, True); self.clock.pack(side="right", padx=10)

        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, minsize=72); body.grid_columnconfigure(1, minsize=250); body.grid_columnconfigure(2, weight=1); body.grid_columnconfigure(3, minsize=310); body.grid_rowconfigure(0, weight=1)
        self._rail(body); self._sidebar(body); self._workspace(body); self._mission(body)

        bottom = tk.Frame(self.root, bg="#071016", height=40, highlightthickness=1, highlightbackground=LINE); bottom.pack(fill="x"); bottom.pack_propagate(False)
        self.alert = self._label(bottom, "READY", 8, MUTED); self.alert.pack(side="left", padx=18)
        self._button(bottom, "COPILOTO  F2", self._open_copilot).pack(side="right", padx=10, pady=5)
        self._button(bottom, "NUEVA MISIÓN", lambda: self.command("planifica una nueva misión")).pack(side="right", padx=3, pady=5)

    def _label(self, parent, text, size=9, fg=WHITE, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w")

    def _button(self, parent, text, command, width=None):
        return tk.Button(parent, text=text, command=command, width=width, bg=PANEL, fg=WHITE, activebackground="#123039", activeforeground=CYAN, relief="flat", bd=0, cursor="hand2", padx=10, pady=7, font=("Segoe UI", 8, "bold"))

    def _card(self, parent, bg=PANEL):
        return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def _rail(self, body):
        p = tk.Frame(body, bg="#04080b"); p.grid(row=0, column=0, sticky="nsew")
        items = [("⌂", "Inicio"), ("◇", "Mis Chats"), ("✓", "Tareas"), ("◷", "Recordatorios"), ("G", "Gmail"), ("C", "Google Calendar"), ("➤", "Telegram"), ("◉", "GitHub"), ("⌁", "Noticias"), ("☼", "Clima"), ("⚙", "Configuración")]
        for icon, name in items:
            b = self._button(p, icon, lambda n=name: self.show(n), 3); b.pack(fill="x", padx=9, pady=4)
            b.bind("<Enter>", lambda e, n=name: self.notify(n))

    def _sidebar(self, body):
        p = tk.Frame(body, bg="#060b0f"); p.grid(row=0, column=1, sticky="nsew")
        self.side_title = self._label(p, "MISSION CONTROL", 13, WHITE, True); self.side_title.pack(anchor="w", padx=16, pady=(20, 12))
        self._button(p, "＋  NUEVA CONVERSACIÓN", self._new_chat).pack(fill="x", padx=10, pady=(0, 8))
        self.search = tk.Entry(p, bg="#0d171d", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0); self.search.pack(fill="x", padx=10, ipady=9); self.search.insert(0, "Buscar en sesión…")
        self.chat_list = tk.Frame(p, bg=p.cget("bg")); self.chat_list.pack(fill="x", padx=10, pady=14); self._refresh_chats()
        self._label(p, "CORE TELEMETRY", 8, CYAN, True).pack(anchor="w", padx=16, pady=(12, 5))
        self.stats = self._label(p, "", 8, MUTED); self.stats.pack(anchor="w", padx=16)
        self._label(p, "ACTIVE CAPABILITIES", 8, CYAN, True).pack(anchor="w", padx=16, pady=(24, 6))
        self.capabilities = self._label(p, "AI  •  ONLINE\nMEMORY  •  LOCAL\nVOICE  •  READY\nPC CONTROL  •  READY\nCOMPUTER USE  •  READY", 8, MUTED); self.capabilities.pack(anchor="w", padx=16)

    def _workspace(self, body):
        p = tk.Frame(body, bg=BG); p.grid(row=0, column=2, sticky="nsew"); p.grid_rowconfigure(0, weight=1); p.grid_columnconfigure(0, weight=1)
        self.content = tk.Frame(p, bg=BG); self.content.grid(row=0, column=0, sticky="nsew")
        composer = tk.Frame(p, bg=BG); composer.grid(row=1, column=0, sticky="ew", padx=20, pady=14); composer.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(composer, bg="#0d171d", fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 10)); self.entry.grid(row=0, column=0, sticky="ew", ipady=14); self.entry.bind("<Return>", lambda e: self._send())
        self._button(composer, "MIC", self._voice, 6).grid(row=0, column=1, padx=5)
        self._button(composer, "ENVIAR", self._send).grid(row=0, column=2)
        self._label(composer, "ORDEN DIRECTA  •  PLANIFICACIÓN  •  CONTROL VISIBLE  •  CONFIRMACIÓN PARA ACCIONES EXTERNAS", 7, MUTED).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

    def _mission(self, body):
        p = tk.Frame(body, bg="#060b0f"); p.grid(row=0, column=3, sticky="nsew")
        self._label(p, "MISSION CONTROL", 12, WHITE, True).pack(anchor="w", padx=16, pady=(20, 2))
        self._label(p, "Plan • execute • verify", 8, MUTED).pack(anchor="w", padx=16, pady=(0, 12))
        self.mission = self._card(p, "#09151b"); self.mission.pack(fill="x", padx=10)
        self.mission_state = self._label(self.mission, self.state, 16, CYAN, True); self.mission_state.pack(anchor="w", padx=13, pady=(12, 2))
        self.mission_detail = self._label(self.mission, "En espera de una orden.", 8, MUTED); self.mission_detail.pack(anchor="w", padx=13, pady=(0, 13))
        self._label(p, "LIVE ACTIVITY", 8, CYAN, True).pack(anchor="w", padx=16, pady=(16, 5))
        self.activity = tk.Text(p, height=10, bg="#04080b", fg=MUTED, relief="flat", bd=0, font=("Consolas", 8), state="disabled"); self.activity.pack(fill="x", padx=10)
        self._label(p, "QUICK ACTIONS", 8, CYAN, True).pack(anchor="w", padx=16, pady=(15, 5))
        for text, cmd in (("Diagnóstico del PC", "revisa mi pc"), ("Abrir Teams", "abre teams"), ("Observar pantalla", "mira la pantalla"), ("Buscar noticias", "busca noticias")):
            self._button(p, text, lambda c=cmd: self.command(c)).pack(fill="x", padx=10, pady=2)
        self._label(p, "EVIDENCE", 8, CYAN, True).pack(anchor="w", padx=16, pady=(15, 4))
        self.evidence_label = self._label(p, "Sin evidencia todavía.", 8, MUTED); self.evidence_label.pack(anchor="w", padx=16)

    def _home(self):
        self._clear()
        self.content.grid_columnconfigure(0, weight=1); self.content.grid_rowconfigure(0, weight=1)
        cv = tk.Canvas(self.content, bg=BG, highlightthickness=0); cv.grid(row=0, column=0, sticky="nsew"); self.core = cv
        self._label(self.content, "JARVIS", 10, WHITE, True).place(x=28, y=24)
        self._label(self.content, "PERSONAL AI  /  MARK VI", 8, MUTED).place(x=28, y=46)
        self._label(self.content, f"{self.brain.provider.upper()}  •  LOCAL CONTROL", 8, CYAN, True).place(relx=1, x=-28, y=25, anchor="ne")
        self._label(self.content, "ORDENES  •  MEMORIA  •  VOZ  •  PC  •  WEB  •  MISIONES", 8, MUTED).place(relx=.5, rely=.88, anchor="center")

    def _draw_core(self):
        if not hasattr(self, "core") or not self.core.winfo_exists(): return
        c = self.core; w = max(c.winfo_width(), 720); h = max(c.winfo_height(), 500); cx = w * .5; cy = h * .43; r = min(w, h) * .18; c.delete("all")
        for x in range(0, w, 44): c.create_line(x, 0, x, h, fill="#071116")
        for y in range(0, h, 44): c.create_line(0, y, w, y, fill="#071116")
        for i in range(12):
            rr = r + i * 9 + math.sin(self.phase * (1 + i * .07)) * 4; start = (self.phase * 28 + i * 31) % 360; extent = 270 if i % 2 else 320
            c.create_arc(cx - rr, cy - rr, cx + rr, cy + rr, start=start, extent=extent, outline=CYAN if i % 2 == 0 else CYAN_D, width=2 if i in (0, 6, 11) else 1)
        pulse = r * (.8 + .08 * math.sin(self.phase * 2))
        c.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill="#030a0e", outline=CYAN_D, width=2)
        c.create_oval(cx - r * .53, cy - r * .53, cx + r * .53, cy + r * .53, fill="#050d12", outline=CYAN, width=1)
        c.create_text(cx, cy - 12, text="J.A.R.V.I.S", fill=WHITE, font=("Segoe UI", 17, "bold")); c.create_text(cx, cy + 16, text=self.state, fill=CYAN, font=("Segoe UI", 9, "bold"))
        c.create_text(24, h - 26, text=f"CORE  {self.brain.provider.upper()}  •  {self._model()}", anchor="w", fill=MUTED, font=("Consolas", 8)); c.create_text(w - 24, h - 26, text="MEMORY LOCAL  •  VISIBLE COMPUTER USE", anchor="e", fill=MUTED, font=("Consolas", 8))

    def _model(self):
        cfg = getattr(self.brain, "config", None); return getattr(cfg, "gemini_model", "gemini") if self.brain.provider == "gemini" else getattr(cfg, "ollama_model", "ollama")

    def _tick(self):
        if not self.running: return
        self.phase += .045
        if self.module == "Inicio": self._draw_core()
        self.clock.config(text=datetime.now().strftime("%H:%M:%S"))
        if psutil:
            total, done, rem = self.features.counts(); self.stats.config(text=f"CPU {psutil.cpu_percent():.0f}%   RAM {psutil.virtual_memory().percent:.0f}%\nTareas {done}/{total}   Avisos {rem}\n{self.brain.provider.upper()} • {self._model()}")
        self.root.after(1000, self._tick)

    def show(self, name):
        self.module = name; self.side_title.config(text=name.upper())
        if name in ("Inicio", "Mis Chats"): self._home(); return
        self._clear(); self._label(self.content, name, 25, WHITE, True).pack(anchor="w", padx=30, pady=(28, 3)); self._label(self.content, self._desc(name), 9, MUTED).pack(anchor="w", padx=30, pady=(0, 18))
        handlers = {"Tareas": self._tasks, "Recordatorios": self._reminders, "Configuración": self._settings, "Gmail": lambda: self._integration("Gmail", "abre gmail"), "Google Calendar": lambda: self._integration("Google Calendar", "abre calendar"), "Telegram": lambda: self._integration("Telegram", "abre telegram"), "GitHub": lambda: self._integration("GitHub", "abre github"), "Noticias": lambda: self._web_module("Noticias", ["busca noticias", "busca tecnología", "busca noticias Colombia"]), "Clima": lambda: self._web_module("Clima", ["busca clima", "busca pronóstico", "busca clima Medellín"])}
        if name in handlers: handlers[name]()
        else: self._home()

    def _desc(self, name):
        return {"Tareas": "Misiones persistentes con estado real.", "Recordatorios": "Avisos locales que aparecen en cualquier módulo.", "Configuración": "Controla cerebro, razonamiento, voz, pantalla y datos.", "Gmail": "Acceso a tu sesión autorizada de Gmail.", "Google Calendar": "Acceso a tu calendario autorizado.", "Telegram": "Acceso mediante tu sesión del navegador.", "GitHub": "Centro de desarrollo y repositorios.", "Noticias": "Búsqueda web inmediata.", "Clima": "Consulta meteorológica inmediata."}.get(name, "Centro operativo")

    def _clear(self):
        for c in self.content.winfo_children(): c.destroy()

    def _tasks(self):
        box = self._card(self.content, PANEL2); box.pack(fill="x", padx=30, pady=4); box.grid_columnconfigure(0, weight=1)
        e = tk.Entry(box, bg="#0e1a20", fg=WHITE, relief="flat", bd=0); e.grid(row=0, column=0, sticky="ew", padx=10, pady=10, ipady=10); e.insert(0, "Nueva misión")
        self._button(box, "CREAR", lambda: (self.features.add_task(e.get().strip()) if e.get().strip() and e.get() != "Nueva misión" else None, self.show("Tareas"))).grid(row=0, column=1, padx=8, pady=8)
        for i, t in enumerate(self.features.tasks):
            row = self._card(self.content, "#080f14"); row.pack(fill="x", padx=30, pady=3); self._label(row, "●" if t.done else "○", 12, GREEN if t.done else MUTED, True).pack(side="left", padx=13, pady=12); self._label(row, t.title, 9, WHITE if not t.done else MUTED).pack(side="left")
            if not t.done: self._button(row, "COMPLETAR", lambda i=i: self._complete(i)).pack(side="right", padx=8, pady=6)

    def _complete(self, i): self.features.complete_task(i); self.show("Tareas"); self.notify("Misión completada", GREEN)

    def _reminders(self):
        box = self._card(self.content, PANEL2); box.pack(fill="x", padx=30, pady=4); box.grid_columnconfigure(0, weight=1)
        e = tk.Entry(box, bg="#0e1a20", fg=WHITE, relief="flat", bd=0); e.grid(row=0, column=0, sticky="ew", padx=8, pady=10, ipady=10); e.insert(0, "Nuevo aviso")
        d = tk.Entry(box, bg="#0e1a20", fg=WHITE, relief="flat", bd=0, width=19); d.grid(row=0, column=1, padx=5, pady=10, ipady=10); d.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        def add():
            try: when = datetime.strptime(d.get(), "%Y-%m-%d %H:%M")
            except ValueError: self.notify("Formato: YYYY-MM-DD HH:MM", RED); return
            if e.get().strip() and e.get() != "Nuevo aviso": self.features.add_reminder(e.get().strip(), when.isoformat(timespec="minutes")); self.show("Recordatorios"); self.notify("Aviso programado", GREEN)
        self._button(box, "PROGRAMAR", add).grid(row=0, column=2, padx=8, pady=8)
        for r in self.features.reminders:
            if not r.fired:
                row = self._card(self.content, "#080f14"); row.pack(fill="x", padx=30, pady=3); self._label(row, "◷", 12, AMBER, True).pack(side="left", padx=13, pady=12); self._label(row, f"{r.title}   •   {r.when}", 9, WHITE).pack(side="left")

    def _integration(self, name, cmd):
        box = self._card(self.content, PANEL2); box.pack(fill="x", padx=30, pady=5); self._label(box, "CONEXIÓN ACTIVA", 8, CYAN, True).pack(anchor="w", padx=15, pady=(15, 4)); self._label(box, "La acción usa la sesión normal del usuario; no se saltan autenticaciones.", 10, WHITE).pack(anchor="w", padx=15, pady=3); self._button(box, "ABRIR AHORA", lambda: self.command(cmd)).pack(anchor="w", padx=15, pady=14)

    def _web_module(self, title, commands):
        box = self._card(self.content, PANEL2); box.pack(fill="x", padx=30, pady=5); self._label(box, "WEB SEARCH", 8, CYAN, True).pack(anchor="w", padx=15, pady=(15, 8))
        for cmd in commands: self._button(box, cmd.replace("busca ", "BUSCAR ").upper(), lambda c=cmd: self.command(c)).pack(fill="x", padx=15, pady=3)

    def _settings(self):
        self._settings_brain(); self._settings_reasoning(); self._settings_control(); self._settings_voice(); self._settings_data()

    def _settings_group(self, title):
        box = self._card(self.content, PANEL2); box.pack(fill="x", padx=30, pady=5); self._label(box, title, 8, CYAN, True).pack(anchor="w", padx=15, pady=(13, 8)); return box

    def _settings_brain(self):
        box = self._settings_group("CEREBRO / MODELO")
        self._button(box, "USAR GEMINI", lambda: self.command("usa gemini")).pack(side="left", padx=15, pady=5)
        self._button(box, "USAR OLLAMA LOCAL", lambda: self.command("usa ollama")).pack(side="left", padx=4, pady=5)
        model = tk.Entry(box, bg="#0e1a20", fg=WHITE, relief="flat", bd=0, width=30); model.pack(side="left", padx=10, pady=5, ipady=7); model.insert(0, self._model())
        self._button(box, "APLICAR MODELO", lambda: self._apply_model(model.get())).pack(side="left", padx=4, pady=5)

    def _apply_model(self, model):
        model = model.strip()
        if not model: return
        if self.brain.provider == "gemini": self.brain.config.gemini_model = model
        else: self.brain.config.ollama_model = model
        self.notify(f"Modelo activo: {model}", GREEN)

    def _settings_reasoning(self):
        box = self._settings_group("RAZONAMIENTO / AUTOCORRECCIÓN")
        for label, cmd in (("BAJO", "esfuerzo bajo"), ("MEDIO", "esfuerzo medio"), ("ALTO", "esfuerzo alto")):
            self._button(box, label, lambda c=cmd: self.command(c), 10).pack(side="left", padx=6, pady=5)
        self._label(box, "Alto usa una pasada adicional de verificación; nunca muestra cadenas privadas de pensamiento.", 8, MUTED).pack(anchor="w", padx=15, pady=(0, 10))

    def _settings_control(self):
        box = self._settings_group("CONTROL DEL EQUIPO")
        for text, cmd in (("DIAGNÓSTICO", "revisa mi pc"), ("ABRIR TEAMS", "abre teams"), ("OBSERVAR PANTALLA", "mira la pantalla"), ("ABRIR GOOGLE", "abre google")):
            self._button(box, text, lambda c=cmd: self.command(c)).pack(side="left", padx=5, pady=5)
        self._label(box, "Computer Use funciona solo por órdenes explícitas y de forma visible.", 8, MUTED).pack(anchor="w", padx=15, pady=(0, 10))

    def _settings_voice(self):
        box = self._settings_group("VOZ")
        self._button(box, "PROBAR TTS", self._test_voice).pack(side="left", padx=15, pady=5)
        self._button(box, "ESCUCHAR 7 S", self._voice).pack(side="left", padx=5, pady=5)
        self._label(box, "STT local • VAD • wake word", 8, MUTED).pack(side="left", padx=15)

    def _settings_data(self):
        box = self._settings_group("MEMORIA / DATOS")
        self._button(box, "NUEVA CONVERSACIÓN", self._new_chat).pack(side="left", padx=15, pady=5)
        self._button(box, "ABRIR DATOS", self._open_data).pack(side="left", padx=5, pady=5)
        self._button(box, "LIMPIAR CONTEXTO", lambda: self.command("limpiar conversación")).pack(side="left", padx=5, pady=5)

    def _test_voice(self): threading.Thread(target=self.voice.speak, args=("Prueba de voz de JARVIS completada.",), daemon=True).start()
    def _open_data(self): os.startfile(str(Path("data").resolve()))
    def _send(self): self.command(self.entry.get().strip()); self.entry.delete(0, "end")
    def _voice(self): self.set_state("ESCUCHANDO"); threading.Thread(target=self._voice_worker, daemon=True).start()
    def _voice_worker(self):
        try:
            cmd = self.voice.listen_for_command(seconds=7)
            if cmd: self.root.after(0, lambda: self.command(cmd))
            else: self.root.after(0, lambda: self.set_state("STANDBY"))
        except Exception as exc: self.root.after(0, lambda: self.notify(f"Error de voz: {exc}", RED))

    def command(self, cmd):
        if not cmd: return
        self.add_message("TÚ", cmd); self.set_state("PROCESANDO"); self._activity("ORDEN  " + cmd); threading.Thread(target=self.process_command, args=(cmd,), daemon=True).start()
    def add_message(self, role, text): self.messages.append((role, text)); self.messages = self.messages[-30:]; self._refresh_chats()
    def set_response(self, text): self.root.after(0, lambda: self.add_message("JARVIS", text)); self.root.after(0, lambda: self.set_state("STANDBY"))
    def set_state(self, state):
        self.state = state.upper()
        if hasattr(self, "mission_state"):
            self.mission_state.config(text=self.state, fg=RED if self.state == "ERROR" else CYAN)
            self.mission_detail.config(text={"STANDBY": "En espera de una orden.", "ESCUCHANDO": "Micrófono activo.", "PROCESANDO": "Ejecutando herramientas.", "PENSANDO": "Planificando.", "VERIFICANDO": "Comprobando resultado."}.get(self.state, "Sistema activo."))
    def _activity(self, text):
        def write():
            self.activity.config(state="normal"); self.activity.insert("end", f"[{datetime.now():%H:%M:%S}] {text}\n"); self.activity.see("end"); self.activity.config(state="disabled")
        self.root.after(0, write)
    def notify(self, text, fg=CYAN):
        self.root.after(0, lambda: self.alert.config(text=text.upper(), fg=fg)); self.root.after(6500, lambda: self.alert.config(text="READY", fg=MUTED))
    def _new_chat(self): self.messages.clear(); self.brain.reset_conversation(); self._refresh_chats(); self.show("Inicio"); self.notify("Nueva conversación", GREEN)
    def _refresh_chats(self):
        if not hasattr(self, "chat_list"): return
        for c in self.chat_list.winfo_children(): c.destroy()
        title = "Sesión actual" if not self.messages else self.messages[-1][1][:34]
        self._label(self.chat_list, "◉  JARVIS", 10, CYAN, True).pack(anchor="w", pady=4); self._label(self.chat_list, title, 8, MUTED).pack(anchor="w", pady=(0, 6))
        for role, text in self.messages[-4:]: self._label(self.chat_list, f"{role}: {text[:26]}", 7, WHITE if role == "TÚ" else MUTED).pack(anchor="w", pady=2)
    def _open_copilot(self):
        try:
            from .copilot_panel import CopilotPanel
            CopilotPanel(self.root, self.process_command).open()
        except Exception as exc: self.notify(str(exc), RED)
    def _reminder_fired(self, reminder: ReminderItem):
        self.root.after(0, lambda: self.notify(f"AVISO: {reminder.title}", AMBER)); self.root.after(0, lambda: messagebox.showinfo("JARVIS — Aviso", reminder.title, parent=self.root))
    def run(self): self.root.mainloop()
    def _close(self): self.running = False; self._reminder_stop.set(); self.shutdown_callback(); self.root.destroy()
