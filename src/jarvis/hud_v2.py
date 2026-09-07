from __future__ import annotations

import math
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Callable

try:
    import psutil
except ImportError:
    psutil = None

from .hrz_features import FeatureHub, ReminderItem

BG = "#030507"
PANEL = "#080d12"
PANEL2 = "#0b1218"
LINE = "#182830"
CYAN = "#12dce8"
CYAN2 = "#087c86"
WHITE = "#edf5f7"
MUTED = "#71818a"
GREEN = "#43e1a1"
AMBER = "#f2bc4e"
RED = "#ed6375"


class JarvisHUDv2:
    """Mission Control nativo: cada módulo tiene controles reales, no tarjetas decorativas."""

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
        self.messages: list[tuple[str, str]] = []
        self.module = "Inicio"
        self._reminder_stop = threading.Event()
        self._build_window()
        self._build_shell()
        self._tick()
        threading.Thread(target=self.features.reminder_loop, args=(self._reminder_fired, self._reminder_stop), daemon=True).start()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("JARVIS — Mission Control")
        self.root.configure(bg=BG)
        self.root.minsize(1250, 760)
        try: self.root.state("zoomed")
        except tk.TclError: self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def label(self, p, text, size=9, fg=WHITE, bold=False, bg=None):
        return tk.Label(p, text=text, bg=bg or p.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w")

    def button(self, p, text, cmd, width=None):
        return tk.Button(p, text=text, command=cmd, width=width, bg=PANEL, fg=WHITE, activebackground="#102c33", activeforeground=CYAN, relief="flat", bd=0, cursor="hand2", padx=9, pady=7, font=("Segoe UI", 9))

    def card(self, p, bg=PANEL):
        return tk.Frame(p, bg=bg, highlightthickness=1, highlightbackground=LINE)

    def _build_shell(self):
        top = tk.Frame(self.root, bg="#06090c", height=48, highlightthickness=1, highlightbackground=LINE); top.pack(fill="x"); top.pack_propagate(False)
        self.label(top, "◉  JARVIS", 11, WHITE, True, top["bg"]).pack(side="left", padx=18)
        self.label(top, "MISSION CONTROL", 8, CYAN, True, top["bg"]).pack(side="left", padx=15)
        self.top_status = self.label(top, "● CORE ONLINE", 8, GREEN, True, top["bg"]); self.top_status.pack(side="right", padx=15)
        self.clock = self.label(top, "--:--:--", 9, WHITE, True, top["bg"]); self.clock.pack(side="right", padx=8)

        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, minsize=64); body.grid_columnconfigure(1, minsize=245); body.grid_columnconfigure(2, weight=1); body.grid_columnconfigure(3, minsize=285); body.grid_rowconfigure(0, weight=1)
        self._rail(body); self._sidebar(body); self._workspace(body); self._mission(body)
        bottom = tk.Frame(self.root, bg="#0a1217", height=38); bottom.pack(fill="x"); bottom.pack_propagate(False)
        self.alert = self.label(bottom, "Sistemas listos", 8, MUTED, False, bottom["bg"]); self.alert.pack(side="left", padx=16)
        self.button(bottom, "Copiloto  F2", self._copilot).pack(side="right", padx=8, pady=4)

    def _rail(self, body):
        p = tk.Frame(body, bg="#05080b"); p.grid(row=0, column=0, sticky="nsew")
        items = [("⌂","Inicio"),("◈","Mis Chats"),("✓","Tareas"),("◷","Recordatorios"),("G","Gmail"),("C","Calendar"),("➤","Telegram"),("◉","GitHub"),("⌁","Noticias"),("☼","Clima"),("⚙","Configuración")]
        for icon, name in items:
            self.button(p, icon, lambda n=name: self.show(n), 3).pack(fill="x", padx=8, pady=4)

    def _sidebar(self, body):
        p = tk.Frame(body, bg="#070a0d"); p.grid(row=0, column=1, sticky="nsew")
        self.side_title = self.label(p, "CONTROL", 13, WHITE, True, p["bg"]); self.side_title.pack(anchor="w", padx=15, pady=(18,10))
        self.button(p, "＋ Nueva conversación", self._new_chat).pack(fill="x", padx=10, pady=(0,8))
        self.search = tk.Entry(p, bg="#10161b", fg=MUTED, insertbackground=CYAN, relief="flat", bd=0); self.search.pack(fill="x", padx=10, ipady=9); self.search.insert(0,"Buscar chats…")
        self.chat_list = tk.Frame(p, bg=p["bg"]); self.chat_list.pack(fill="x", padx=10, pady=12); self._refresh_chats()
        self.label(p,"CORE",8,CYAN,True,p["bg"]).pack(anchor="w",padx=15,pady=(8,4))
        self.stats = self.label(p,"",8,MUTED,False,p["bg"]); self.stats.pack(anchor="w",padx=15)
        self.label(p,"MÓDULOS",8,MUTED,True,p["bg"]).pack(anchor="w",padx=15,pady=(20,5))
        self.module_status = self.label(p,"PC CONTROL  •  ONLINE\nMEMORIA  •  LOCAL\nVOZ  •  LISTA",8,MUTED,False,p["bg"]); self.module_status.pack(anchor="w",padx=15)

    def _workspace(self, body):
        p = tk.Frame(body,bg=BG); p.grid(row=0,column=2,sticky="nsew"); p.grid_rowconfigure(0,weight=1); p.grid_columnconfigure(0,weight=1)
        self.content=tk.Frame(p,bg=BG); self.content.grid(row=0,column=0,sticky="nsew")
        composer=tk.Frame(p,bg=BG); composer.grid(row=1,column=0,sticky="ew",padx=18,pady=14); composer.grid_columnconfigure(0,weight=1)
        self.entry=tk.Entry(composer,bg="#10161b",fg=WHITE,insertbackground=CYAN,relief="flat",bd=0,font=("Segoe UI",10)); self.entry.grid(row=0,column=0,sticky="ew",ipady=13); self.entry.bind("<Return>",lambda e:self._send())
        self.button(composer,"MIC",self._voice,6).grid(row=0,column=1,padx=5); self.button(composer,"ENVIAR",self._send).grid(row=0,column=2)
        self.label(composer,"Orden directa  •  voz local  •  un solo agente  •  acciones externas con confirmación",7,MUTED,False,BG).grid(row=1,column=0,columnspan=3,sticky="w",pady=(4,0))

    def _mission(self, body):
        p=tk.Frame(body,bg="#070b0e"); p.grid(row=0,column=3,sticky="nsew")
        self.label(p,"MISSION CONTROL",12,WHITE,True,p["bg"]).pack(anchor="w",padx=15,pady=(18,2)); self.label(p,"Supervisión de la misión actual",8,MUTED,False,p["bg"]).pack(anchor="w",padx=15,pady=(0,12))
        self.mission=self.card(p,"#091217"); self.mission.pack(fill="x",padx=10); self.mission_state=self.label(self.mission,self.state,16,CYAN,True,self.mission["bg"]); self.mission_state.pack(anchor="w",padx=12,pady=(12,2)); self.mission_detail=self.label(self.mission,"En espera",8,MUTED,False,self.mission["bg"]); self.mission_detail.pack(anchor="w",padx=12,pady=(0,12))
        self.label(p,"ACTIVIDAD",8,CYAN,True,p["bg"]).pack(anchor="w",padx=15,pady=(15,5)); self.activity=tk.Text(p,height=9,bg="#05080b",fg=MUTED,relief="flat",bd=0,font=("Consolas",8),state="disabled"); self.activity.pack(fill="x",padx=10)
        self.label(p,"ACCIONES",8,CYAN,True,p["bg"]).pack(anchor="w",padx=15,pady=(14,5))
        for text,cmd in (("Estado del PC","revisa mi pc"),("Abrir Teams","abre teams"),("Abrir navegador","abre google"),("Buscar en web","busca noticias")):
            self.button(p,text,lambda c=cmd:self.command(c)).pack(fill="x",padx=10,pady=2)
        self.label(p,"EVIDENCIA",8,CYAN,True,p["bg"]).pack(anchor="w",padx=15,pady=(14,5)); self.evidence_label=self.label(p,"Sin misión activa",8,MUTED,False,p["bg"]); self.evidence_label.pack(anchor="w",padx=15)

    def _home(self):
        for c in self.content.winfo_children(): c.destroy()
        self.content.grid_columnconfigure(0,weight=1); self.content.grid_rowconfigure(0,weight=1)
        cv=tk.Canvas(self.content,bg=BG,highlightthickness=0); cv.grid(row=0,column=0,sticky="nsew"); self.core=cv
        self.label(self.content,"JARVIS",10,WHITE,True,BG).place(x=26,y=22); self.label(self.content,"LOCAL PERSONAL AI  /  MARK VI",8,MUTED,False,BG).place(x=26,y=43); self.label(self.content,"GEMINI + OLLAMA",8,CYAN,True,BG).place(relx=1,x=-25,y=25,anchor="ne")
        self.label(self.content,"ORDENES • MEMORIA • VOZ • PC • WEB • MISIONES",8,MUTED,False,BG).place(relx=.5,rely=.86,anchor="center")

    def _draw(self):
        if not hasattr(self,"core") or not self.core.winfo_exists(): return
        c=self.core; w=max(c.winfo_width(),700); h=max(c.winfo_height(),500); cx=w*.5; cy=h*.43; r=min(w,h)*.18; c.delete("all")
        for x in range(0,w,42): c.create_line(x,0,x,h,fill="#071014")
        for y in range(0,h,42): c.create_line(0,y,w,y,fill="#071014")
        for i in range(10):
            rr=r+i*10+math.sin(self.phase*(1+i*.08))*4; start=(self.phase*25+i*39)%360; c.create_arc(cx-rr,cy-rr,cx+rr,cy+rr,start=start,extent=255 if i%2 else 310,outline=CYAN if i%2==0 else CYAN2,width=2 if i in (0,5) else 1)
        c.create_oval(cx-r*.72,cy-r*.72,cx+r*.72,cy+r*.72,fill="#04090c",outline=CYAN2,width=2); c.create_text(cx,cy-10,text="JARVIS",fill=WHITE,font=("Segoe UI",18,"bold")); c.create_text(cx,cy+16,text=self.state,fill=CYAN,font=("Segoe UI",9,"bold"))
        c.create_text(22,h-25,text=f"CORE  {self.brain.provider.upper()}  •  {self._model()}",anchor="w",fill=MUTED,font=("Consolas",8)); c.create_text(w-22,h-25,text="LOCAL MEMORY  •  VISIBLE CONTROL",anchor="e",fill=MUTED,font=("Consolas",8))

    def _model(self):
        cfg=getattr(self.brain,"config",None); return str(getattr(cfg,"gemini_model","gemini")) if self.brain.provider=="gemini" else str(getattr(cfg,"ollama_model","ollama"))
    def _tick(self):
        if not self.running:return
        self.phase+=.04; self._draw(); self.clock.config(text=datetime.now().strftime("%H:%M:%S")); self._telemetry(); self.root.after(1000,self._tick)
    def _telemetry(self):
        total,done,rem=self.features.counts(); cpu=psutil.cpu_percent() if psutil else 0; ram=psutil.virtual_memory().percent if psutil else 0; self.stats.config(text=f"CPU {cpu:.0f}%   RAM {ram:.0f}%\nTareas {done}/{total}   Avisos {rem}\n{self.brain.provider.upper()} • {self._model()}")

    def show(self,name):
        self.module=name; self.side_title.config(text=name.upper());
        if name in ("Inicio","Mis Chats"): self._home(); return
        for c in self.content.winfo_children(): c.destroy()
        title=self.label(self.content,name,24,WHITE,True,BG); title.pack(anchor="w",padx=28,pady=(28,2)); self.label(self.content,self._desc(name),9,MUTED,False,BG).pack(anchor="w",padx=28,pady=(0,20))
        if name=="Tareas": self._tasks()
        elif name=="Recordatorios": self._reminders()
        elif name=="Configuración": self._settings()
        elif name=="Gmail": self._integration("Gmail","abre gmail")
        elif name=="Google Calendar": self._integration("Google Calendar","abre calendar")
        elif name=="Telegram": self._integration("Telegram","abre telegram")
        elif name=="GitHub": self._integration("GitHub","abre github")
        elif name=="Noticias": self._web_module("Noticias","busca noticias",["Buscar noticias","Buscar tecnología","Buscar Colombia"])
        elif name=="Clima": self._web_module("Clima","busca clima",["Buscar clima","Buscar pronóstico","Buscar clima Medellín"])

    def _desc(self,n): return {"Tareas":"Crea y completa misiones persistentes.","Recordatorios":"Programa avisos locales que aparecen aunque estés en otro módulo.","Gmail":"Acceso rápido al correo; la autorización se mantiene en el navegador.","Google Calendar":"Acceso rápido al calendario y preparación para integración OAuth.","Telegram":"Centro de acceso a Telegram mediante sesión autorizada.","GitHub":"Acceso al repositorio y flujos de desarrollo.","Noticias":"Búsqueda web directa desde Mission Control.","Clima":"Consulta meteorología mediante búsqueda web."}.get(n,"Centro de control")

    def _tasks(self):
        box=self.card(self.content,PANEL2); box.pack(fill="x",padx=28,pady=4); box.grid_columnconfigure(0,weight=1)
        e=tk.Entry(box,bg="#11181e",fg=WHITE,relief="flat",bd=0); e.grid(row=0,column=0,sticky="ew",padx=10,pady=10,ipady=9); e.insert(0,"Nueva misión")
        self.button(box,"AGREGAR",lambda:(self.features.add_task(e.get()) if e.get().strip() and e.get()!="Nueva misión" else None,self.show("Tareas"))).grid(row=0,column=1,padx=8,pady=7)
        for i,t in enumerate(self.features.tasks):
            row=self.card(self.content,"#090e13"); row.pack(fill="x",padx=28,pady=3); self.label(row,"✓" if t.done else "○",11,GREEN if t.done else MUTED,True,row["bg"]).pack(side="left",padx=12,pady=12); self.label(row,t.title,9,WHITE if not t.done else MUTED,False,row["bg"]).pack(side="left");
            if not t.done:self.button(row,"COMPLETAR",lambda i=i:self._complete(i)).pack(side="right",padx=8,pady=6)
    def _complete(self,i): self.features.complete_task(i); self.show("Tareas"); self.notify("Misión completada",GREEN)

    def _reminders(self):
        box=self.card(self.content,PANEL2); box.pack(fill="x",padx=28,pady=4); box.grid_columnconfigure(0,weight=1)
        e=tk.Entry(box,bg="#11181e",fg=WHITE,relief="flat",bd=0); e.grid(row=0,column=0,sticky="ew",padx=8,pady=10,ipady=9); e.insert(0,"Nuevo aviso")
        d=tk.Entry(box,bg="#11181e",fg=WHITE,relief="flat",bd=0,width=18); d.grid(row=0,column=1,padx=5,pady=10,ipady=9); d.insert(0,datetime.now().strftime("%Y-%m-%d %H:%M"))
        def add():
            try: datetime.strptime(d.get(),"%Y-%m-%d %H:%M")
            except ValueError: self.notify("Usa YYYY-MM-DD HH:MM",RED); return
            if e.get().strip() and e.get()!="Nuevo aviso": self.features.add_reminder(e.get(),datetime.strptime(d.get(),"%Y-%m-%d %H:%M").isoformat(timespec="minutes")); self.show("Recordatorios"); self.notify("Aviso programado",GREEN)
        self.button(box,"PROGRAMAR",add).grid(row=0,column=2,padx=8,pady=7)
        for r in self.features.reminders:
            if not r.fired:
                row=self.card(self.content,"#090e13"); row.pack(fill="x",padx=28,pady=3); self.label(row,"◷",11,AMBER,True,row["bg"]).pack(side="left",padx=12,pady=12); self.label(row,f"{r.title}   •   {r.when}",9,WHITE,False,row["bg"]).pack(side="left")

    def _integration(self,name,cmd):
        box=self.card(self.content,PANEL2); box.pack(fill="x",padx=28,pady=5); self.label(box,"CONEXIÓN",8,CYAN,True,box["bg"]).pack(anchor="w",padx=14,pady=(14,3)); self.label(box,"Acceso normal / sesión del usuario",11,WHITE,True,box["bg"]).pack(anchor="w",padx=14,pady=3); self.label(box,"El botón ejecuta una acción real: abre el servicio en el navegador.",8,MUTED,False,box["bg"]).pack(anchor="w",padx=14,pady=(0,12)); self.button(box,"ABRIR AHORA",lambda:self.command(cmd)).pack(anchor="w",padx=14,pady=(0,14))

    def _web_module(self,title,default,buttons):
        box=self.card(self.content,PANEL2); box.pack(fill="x",padx=28,pady=5); self.label(box,"BÚSQUEDA WEB",8,CYAN,True,box["bg"]).pack(anchor="w",padx=14,pady=(14,8))
        for text in buttons:self.button(box,text,lambda q=text:self.command(default if text==buttons[0] else f"busca {text.lower()}")).pack(fill="x",padx=14,pady=3)

    def _settings(self):
        self._setting_group("CEREBRO",[("Gemini",lambda:self._provider("gemini")),("Ollama local",lambda:self._provider("ollama"))])
        self._setting_group("VOZ",[("Probar voz",self._test_voice),("Escuchar 7 segundos",self._voice)])
        self._setting_group("CONTROL",[("Estado del PC",lambda:self.command("revisa mi pc")),("Abrir Teams personal",lambda:self.command("abre teams")),("Optimización segura",lambda:self.command("optimiza mi pc"))])
        self._setting_group("DATOS",[("Nueva conversación",self._new_chat),("Abrir carpeta de datos",self._open_data)])
    def _setting_group(self,title,items):
        box=self.card(self.content,PANEL2); box.pack(fill="x",padx=28,pady=5); self.label(box,title,8,CYAN,True,box["bg"]).pack(anchor="w",padx=14,pady=(12,7));
        for text,cmd in items:self.button(box,text,cmd).pack(anchor="w",padx=14,pady=3); self.label(box,"Acción local y visible",7,MUTED,False,box["bg"]).pack(anchor="w",padx=14,pady=(0,4))
    def _provider(self,p):
        try:self.brain.set_provider(p); self.notify(f"Proveedor: {p.upper()}",GREEN)
        except Exception as e:self.notify(str(e),RED)
    def _test_voice(self): threading.Thread(target=self.voice.speak,args=("Prueba de voz de JARVIS completada.",),daemon=True).start()
    def _open_data(self):
        import os; os.startfile(str(Path("data").resolve()))

    def _send(self): self.command(self.entry.get().strip()); self.entry.delete(0,"end")
    def _voice(self): self.set_state("ESCUCHANDO"); threading.Thread(target=self._voice_worker,daemon=True).start()
    def _voice_worker(self):
        try:
            cmd=self.voice.listen_for_command(seconds=7)
            if cmd:self.root.after(0,lambda:self.command(cmd))
            else:self.root.after(0,lambda:self.set_state("STANDBY"))
        except Exception as e:self.root.after(0,lambda:self.notify(f"Error de voz: {e}",RED))
    def command(self,cmd):
        if not cmd:return
        self.add_message("TÚ",cmd); self.set_state("PROCESANDO"); self._activity(f"ORDEN  {cmd}"); threading.Thread(target=self.process_command,args=(cmd,),daemon=True).start()
    def add_message(self,r,t): self.messages.append((r,t)); self.messages=self.messages[-30:]; self._refresh_chats()
    def set_response(self,t): self.root.after(0,lambda:self.add_message("JARVIS",t)); self.root.after(0,lambda:self.set_state("STANDBY"))
    def set_state(self,s):
        self.state=s.upper();
        if hasattr(self,"mission_state"): self.mission_state.config(text=self.state,fg=RED if self.state=="ERROR" else CYAN); self.mission_detail.config(text={"STANDBY":"En espera","ESCUCHANDO":"Micrófono activo","PROCESANDO":"Ejecutando orden","PENSANDO":"Planificando","VERIFICANDO":"Comprobando resultado"}.get(self.state,"Sistema activo"))
    def _activity(self,t):
        def w(): self.activity.config(state="normal"); self.activity.insert("end",f"[{datetime.now():%H:%M:%S}] {t}\n"); self.activity.see("end"); self.activity.config(state="disabled")
        self.root.after(0,w)
    def notify(self,t,color=CYAN): self.root.after(0,lambda:self.alert.config(text=t,fg=color)); self.root.after(6500,lambda:self.alert.config(text="Sistemas listos",fg=MUTED))
    def _new_chat(self): self.messages.clear(); self.brain.reset_conversation(); self._refresh_chats(); self.show("Inicio"); self.notify("Nueva conversación",GREEN)
    def _refresh_chats(self):
        if not hasattr(self,"chat_list"):return
        for c in self.chat_list.winfo_children():c.destroy()
        title="Sesión actual" if not self.messages else self.messages[-1][1][:30]
        self.label(self.chat_list,"◉  JARVIS",10,CYAN,True,self.chat_list["bg"]).pack(anchor="w",pady=4); self.label(self.chat_list,title,8,MUTED,False,self.chat_list["bg"]).pack(anchor="w",pady=(0,6))
    def _copilot(self):
        try:
            from .copilot_panel import CopilotPanel
            CopilotPanel(self.root,self.process_command).open()
        except Exception as e:self.notify(str(e),RED)
    def _reminder_fired(self,r:ReminderItem): self.root.after(0,lambda:self.notify(f"AVISO: {r.title}",AMBER)); self.root.after(0,lambda:messagebox.showinfo("JARVIS — Aviso",r.title,parent=self.root))
    def run(self): self.root.mainloop()
    def _close(self): self.running=False; self._reminder_stop.set(); self.shutdown_callback(); self.root.destroy()
