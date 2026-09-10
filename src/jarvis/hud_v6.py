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
    Image = ImageTk = None

BG = "#020509"
PANEL = "#071018"
PANEL2 = "#0a141d"
LINE = "#16333f"
CYAN = "#25d9ff"
BLUE = "#4e8cff"
GREEN = "#3ee5a1"
ORANGE = "#ffad4a"
RED = "#ff5f73"
PURPLE = "#a77cff"
WHITE = "#e8f6fa"
MUTED = "#718b95"


class JarvisHUDv6:
    """Mission-control HUD nativo, centrado en el reactor y el equipo de subagentes."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], neural=None, stop_mission: Callable[[], None] | None = None, subagents=None):
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.stop_mission_callback = stop_mission or (lambda: None)
        self.neural = neural
        self.subagents = subagents
        self.root = tk.Tk()
        self.state = "STANDBY"
        self.phase = 0.0
        self.mouse_x = self.mouse_y = 0.0
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._main_thread = threading.get_ident()
        self._screen_photo = None
        self._particles = self._make_particles(170)
        self._build_window()
        self._build_ui()
        self._pump_ui()
        self._animate()
        self._clock()
        self._telemetry()

    def _make_particles(self, count):
        random.seed(17)
        return [{"a": random.random() * math.tau, "b": random.random() * math.tau, "r": random.uniform(120, 310), "s": random.uniform(.001, .004), "z": random.choice((1, 1, 1, 2))} for _ in range(count)]

    def _build_window(self):
        self.root.title("J.A.R.V.I.S. // AUTONOMOUS MISSION CONTROL")
        self.root.configure(bg=BG)
        self.root.minsize(1360, 820)
        try: self.root.state("zoomed")
        except tk.TclError: self.root.geometry("1680x980")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<F2>", lambda _e: self.entry.focus_set())
        self.root.bind("<F8>", lambda _e: self._quick("mira la pantalla"))
        self.root.bind("<Escape>", lambda _e: self._stop_mission())

    def label(self, parent, text, size=9, fg=WHITE, bold=False, anchor="w"):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor=anchor, justify="left")

    def button(self, parent, text, command, accent=False, danger=False, width=None):
        return tk.Button(parent, text=text, command=command, width=width, bg="#102a35" if accent else ("#281017" if danger else "#0a1b24"), fg=RED if danger else (CYAN if accent else WHITE), activebackground="#173c49", activeforeground=WHITE, relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=8, pady=7)

    def panel(self, parent, row, col, **kw):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        f.grid(row=row, column=col, sticky="nsew", **kw)
        return f

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#010307", height=62, highlightthickness=1, highlightbackground=LINE)
        header.pack(fill="x"); header.pack_propagate(False)
        self.label(header, "J.A.R.V.I.S.", 17, CYAN, True).pack(side="left", padx=20)
        self.label(header, "AUTONOMOUS COGNITIVE MISSION CONTROL", 8, MUTED, True).pack(side="left", padx=8)
        self.state_chip = tk.Label(header, text="STANDBY", bg="#0b2029", fg=CYAN, font=("Consolas", 8, "bold"), padx=12, pady=5); self.state_chip.pack(side="right", padx=14)
        self.clock_label = self.label(header, "--:--:--", 9, WHITE, True); self.clock_label.pack(side="right", padx=8)
        self.provider_label = self.label(header, "CORE: --", 8, GREEN, True); self.provider_label.pack(side="right", padx=16)

        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, minsize=285); body.grid_columnconfigure(1, weight=1); body.grid_columnconfigure(2, minsize=350)
        body.grid_rowconfigure(0, weight=1)
        self._left(body); self._center(body); self._right(body)
        self._composer()

    def _left(self, body):
        left = self.panel(body, 0, 0, padx=(0,5))
        self.label(left, "COGNITIVE CREW", 9, CYAN, True).pack(anchor="w", padx=14, pady=(15,3))
        self.label(left, "ONE AGENT · SPECIALIZED ROLES", 7, MUTED, True).pack(anchor="w", padx=14, pady=(0,10))
        self.agent_rows = {}
        roster = self.subagents.roster() if self.subagents else []
        for agent in roster:
            row = tk.Frame(left, bg="#09141c", highlightthickness=1, highlightbackground="#102833")
            row.pack(fill="x", padx=11, pady=3)
            dot = tk.Label(row, text="●", bg=row["bg"], fg=agent.color, font=("Segoe UI", 9, "bold")); dot.pack(side="left", padx=(8,6), pady=7)
            text = tk.Frame(row, bg=row["bg"]); text.pack(side="left", fill="x", expand=True, pady=5)
            self.label(text, agent.name, 8, WHITE, True).pack(anchor="w")
            self.label(text, agent.focus, 6, MUTED).pack(anchor="w")
            self.agent_rows[agent.name] = (row, dot)
        self.label(left, "OPERATIONS", 8, CYAN, True).pack(anchor="w", padx=14, pady=(18,6))
        for text, cmd in (("DIAGNOSTIC", "revisa mi pc"), ("OBSERVE SCREEN", "mira la pantalla"), ("OPEN TEAMS", "abre teams personal"), ("NEURAL LAB", "crea una red neuronal")):
            self.button(left, text, lambda c=cmd: self._quick(c)).pack(fill="x", padx=11, pady=3)
        self.button(left, "STOP CURRENT MISSION", self._stop_mission, danger=True).pack(fill="x", padx=11, pady=(10,3))
        self.label(left, "SAFETY", 8, CYAN, True).pack(anchor="w", padx=14, pady=(17,5))
        self.label(left, "VISIBLE DESKTOP CONTROL\nNO KEYLOGGING / NO CREDENTIAL CAPTURE\nHUMAN GATE REQUIRED FOR EXTERNAL ACTIONS", 6, MUTED).pack(anchor="w", padx=14)

    def _center(self, body):
        center = self.panel(body, 0, 1, padx=5)
        center.grid_rowconfigure(1, weight=1); center.grid_rowconfigure(2, minsize=122); center.grid_columnconfigure(0, weight=1)
        top = tk.Frame(center, bg=center["bg"], height=42); top.grid(row=0,column=0,sticky="ew")
        self.label(top, "HOLOGRAPHIC REACTOR", 9, WHITE, True).pack(side="left", padx=15, pady=12)
        self.depth_label = self.label(top, "3D DEPTH FIELD // ONLINE", 7, CYAN, True); self.depth_label.pack(side="right", padx=15)
        field = tk.Frame(center, bg="#010509"); field.grid(row=1,column=0,sticky="nsew",padx=9,pady=8); field.grid_rowconfigure(0,weight=1); field.grid_columnconfigure(0,weight=1)
        self.canvas = tk.Canvas(field, bg="#010509", highlightthickness=0); self.canvas.grid(row=0,column=0,sticky="nsew")
        self.canvas.bind("<Motion>", self._mouse); self.canvas.bind("<Leave>", lambda _e: self._set_mouse(0,0))
        stream_box=tk.Frame(center,bg=center["bg"]); stream_box.grid(row=2,column=0,sticky="nsew",padx=9,pady=(0,9))
        self.label(stream_box,"LIVE EVENT STREAM",8,CYAN,True).pack(anchor="w",padx=5,pady=(2,3))
        self.stream=tk.Text(stream_box,bg="#02070b",fg="#9ab2ba",relief="flat",bd=0,font=("Consolas",8),state="disabled",height=6); self.stream.pack(fill="both",expand=True)

    def _right(self, body):
        right=self.panel(body,0,2,padx=(5,0))
        self.label(right,"MISSION CONTROL",10,WHITE,True).pack(anchor="w",padx=14,pady=(14,2))
        self.mission=self.label(right,"No active mission.",8,MUTED); self.mission.pack(anchor="w",padx=14,pady=(0,8))
        self.phase_labels={}
        for name in ("OBSERVE","ORIENT","DECIDE","ACT","VERIFY"):
            item=self.label(right,"○  "+name,8,MUTED,True); item.pack(anchor="w",padx=15,pady=2); self.phase_labels[name]=item
        self.label(right,"ACTIVE SUBAGENTS",8,CYAN,True).pack(anchor="w",padx=14,pady=(13,5))
        self.subagent_status=self.label(right,"ORCHESTRATOR",7,WHITE,True); self.subagent_status.pack(anchor="w",padx=14)
        self.label(right,"SCREEN FEED",8,CYAN,True).pack(anchor="w",padx=14,pady=(12,4))
        frame=tk.Frame(right,bg="#010509",height=155,highlightthickness=1,highlightbackground=LINE); frame.pack(fill="x",padx=12); frame.pack_propagate(False)
        self.screen_preview=self.label(frame,"NO FRAME\nF8 / OBSERVE",8,MUTED,True,"center"); self.screen_preview.pack(fill="both",expand=True)
        self.label(right,"TELEMETRY",8,CYAN,True).pack(anchor="w",padx=14,pady=(12,4))
        self.telemetry=self.label(right,"CPU --\nRAM --\nDISK --",8,MUTED); self.telemetry.pack(anchor="w",padx=14)
        self.label(right,"HUMAN GATE",8,CYAN,True).pack(anchor="w",padx=14,pady=(10,4))
        self.gate=self.label(right,"ARMED · EXTERNAL ACTIONS REQUIRE CONFIRMATION",7,ORANGE,True); self.gate.pack(anchor="w",padx=14)
        self.button(right,"NEW MISSION",self._new_session,accent=True).pack(fill="x",padx=12,pady=(13,3))
        self.button(right,"OBSERVE NOW",lambda:self._quick("mira la pantalla")).pack(fill="x",padx=12,pady=3)
        self.button(right,"STOP JARVIS",self._close,danger=True).pack(fill="x",padx=12,pady=3)

    def _composer(self):
        bar=tk.Frame(self.root,bg="#010307",highlightthickness=1,highlightbackground=LINE); bar.pack(fill="x",padx=10,pady=(0,10))
        self.entry=tk.Entry(bar,bg="#08131b",fg=WHITE,insertbackground=CYAN,relief="flat",bd=0,font=("Segoe UI",10)); self.entry.pack(side="left",fill="x",expand=True,padx=(10,5),pady=8,ipady=9)
        self.entry.insert(0,"Escribe una misión para JARVIS..."); self.entry.bind("<FocusIn>",self._clear); self.entry.bind("<Return>",lambda _e:self._send())
        self.mic_button=self.button(bar,"MIC",self._voice,width=6); self.mic_button.pack(side="left",padx=3)
        self.button(bar,"EXECUTE",self._send,accent=True,width=10).pack(side="left",padx=(3,10))

    def _clear(self,_e=None):
        if self.entry.get()=="Escribe una misión para JARVIS...": self.entry.delete(0,"end")

    def _mouse(self,e): self._set_mouse((e.x/max(self.canvas.winfo_width(),1)-.5)*2,(e.y/max(self.canvas.winfo_height(),1)-.5)*2)
    def _set_mouse(self,x,y): self.mouse_x=x; self.mouse_y=y

    def _draw(self):
        c=self.canvas; w=max(c.winfo_width(),700); h=max(c.winfo_height(),450); c.delete("all")
        cx=w*.5+self.mouse_x*18; cy=h*.46+self.mouse_y*12; t=self.phase
        horizon=h*.70
        for i in range(13): c.create_line(0,horizon+(i*i)*2.2,w,horizon+(i*i)*2.2,fill="#06141b")
        for x in range(-w,w*2,70): c.create_line(w/2,horizon,x,h,fill="#06141b")
        c.create_line(0,horizon,w,horizon,fill="#0d3540")
        # Orbit ellipses and reactor sphere.
        for ring in (70,105,145,190):
            c.create_oval(cx-ring,cy-ring*.48,cx+ring,cy+ring*.48,outline="#0a4a59",width=1)
        for i in range(22):
            a=i*math.tau/22+t*.7; x=math.cos(a)*125; y=math.sin(a)*125*.52; c.create_line(cx-x*.2,cy-y*.2,cx+x,cy+y,fill="#083744")
        pts=[]
        for p in self._particles:
            a=p["a"]+t*p["s"]*80; b=p["b"]+t*p["s"]*45
            x=p["r"]*math.cos(a)*math.sin(b); y=p["r"]*.58*math.sin(a)*math.sin(b); z=p["r"]*math.cos(b)
            depth=1/(1+z*.0025); px=cx+x*depth; py=cy+y*depth
            if 0<px<w and 0<py<h: pts.append((z,px,py,p["z"]))
        for z,px,py,s in sorted(pts): c.create_oval(px-s,py-s,px+s,py+s,fill=CYAN,outline="")
        # Mesh.
        for lat in range(-3,4):
            y=lat*24; span=math.sqrt(max(0,95*95-y*y)); c.create_arc(cx-span,cy+y-span*.18,cx+span,cy+y+span*.18,start=0,extent=359,outline="#0d6171")
        for lon in range(0,12):
            a=lon*math.pi/12+t*.15; x=math.cos(a)*95; c.create_oval(cx-x*.16,cy-95,cx+x*.16,cy+95,outline="#0b4d5d")
        for r,outline in ((50,"#15596a"),(35,"#1b7384"),(21,"#39cbe7")):
            c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=outline,width=2)
        c.create_oval(cx-13,cy-13,cx+13,cy+13,fill=CYAN,outline=WHITE,width=1)
        c.create_text(cx,cy+120,text="J.A.R.V.I.S.",fill=CYAN,font=("Consolas",10,"bold"))
        c.create_text(cx,cy+140,text=self.state,fill=WHITE,font=("Consolas",8,"bold"))

    def _animate(self):
        self.phase += .018; self._draw(); self.root.after(40,self._animate)
    def _clock(self): self.clock_label.config(text=datetime.now().strftime("%H:%M:%S")); self.root.after(1000,self._clock)
    def _telemetry(self):
        if psutil:
            self.telemetry.config(text=f"CPU {psutil.cpu_percent():.1f}%\nRAM {psutil.virtual_memory().percent:.1f}%\nDISK {psutil.disk_usage('C:/').percent:.1f}%")
        self.root.after(1800,self._telemetry)

    def _send(self):
        text=self.entry.get().strip()
        if not text or text=="Escribe una misión para JARVIS...": return
        self.entry.delete(0,"end"); self.add_message("YOU",text); threading.Thread(target=self.process_command,args=(text,),daemon=True).start()
    def _voice(self):
        try: self.voice.toggle_microphone()
        except Exception: pass
    def _quick(self,cmd): self.add_message("QUICK",cmd); threading.Thread(target=self.process_command,args=(cmd,),daemon=True).start()
    def _new_session(self): self.add_message("SYSTEM","New mission context initialized."); self.set_state("STANDBY")
    def _observe_screen(self): self._quick("mira la pantalla")
    def _stop_mission(self): self.stop_mission_callback(); self.set_state("STANDBY"); self.add_message("SYSTEM","Mission stopped.")
    def _close(self): self.shutdown_callback();

    def set_state(self,state):
        self.state=state.upper(); self._queue(lambda:self.state_chip.config(text=self.state))
    def set_mission(self,text): self._queue(lambda:self.mission.config(text=text))
    def set_response(self,text): self.add_message("JARVIS",text)
    def update_provider(self): self._queue(lambda:self.provider_label.config(text=f"CORE: {self.brain.provider.upper()}"))
    def add_message(self,source,text):
        def apply():
            self.stream.config(state="normal"); self.stream.insert("end",f"[{source}] {text}\n"); self.stream.see("end"); self.stream.config(state="disabled")
        self._queue(apply)
    def show_alert(self,text,color=RED): self.add_message("ALERT",text)
    def show_screen(self,image_base64,width=0,height=0):
        if not image_base64 or Image is None or ImageTk is None: return
        def apply():
            try:
                image=Image.open(io.BytesIO(base64.b64decode(image_base64))); image.thumbnail((330,150)); self._screen_photo=ImageTk.PhotoImage(image); self.screen_preview.config(image=self._screen_photo,text="")
            except Exception: pass
        self._queue(apply)
    def update_subagents(self,agents):
        names=[a.name for a in agents]
        def apply():
            self.subagent_status.config(text=" · ".join(names))
            for name,(row,dot) in self.agent_rows.items(): row.config(bg="#102a35" if name in names else "#09141c"); dot.config(fg=CYAN if name in names else MUTED)
        self._queue(apply)
    def set_phase(self,phase):
        def apply():
            for name,label in self.phase_labels.items(): label.config(text=("●  " if name==phase else "○  ")+name,fg=CYAN if name==phase else MUTED)
        self._queue(apply)
    def _queue(self,fn): self._ui_queue.put(fn)
    def _pump_ui(self):
        try:
            while True: self._ui_queue.get_nowait()()
        except queue.Empty: pass
        self.root.after(40,self._pump_ui)
    def run(self): self.root.mainloop()
