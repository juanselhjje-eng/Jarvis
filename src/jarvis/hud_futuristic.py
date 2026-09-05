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
    """Mission Control cinematográfico: reactor, estado de misión, evidencias, chat y telemetría."""

    def __init__(self, brain, voice, process_command: Callable[[str], None], shutdown: Callable[[], None], evidence=None, execution=None) -> None:
        self.brain = brain
        self.voice = voice
        self.process_command = process_command
        self.shutdown_callback = shutdown
        self.evidence = evidence
        self.execution = execution
        self.running = True
        self.listening = False
        self.activity = "SYSTEM READY"
        self.started = time.monotonic()
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. // MISSION CONTROL")
        self.root.configure(bg=BG)
        self.root.minsize(1180, 720)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1550x900")
        self._build()
        self._render()
        self._status_tick()

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=BG, height=74)
        top.pack(fill="x", padx=26, pady=(14, 0))
        top.pack_propagate(False)
        left = tk.Frame(top, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="J.A.R.V.I.S.", fg=WHITE, bg=BG, font=("Segoe UI", 27, "bold")).pack(side="left")
        tk.Label(left, text="  //  MISSION CONTROL", fg=CYAN2, bg=BG, font=("Consolas", 10, "bold")).pack(side="left", pady=(11, 0))
        status = tk.Frame(top, bg=BG)
        status.pack(side="right", pady=7)
        self.status_label = tk.Label(status, text="● ONLINE", fg=GREEN, bg=BG, font=("Consolas", 10, "bold"))
        self.status_label.pack(anchor="e")
        self.activity_label = tk.Label(status, text=self.activity, fg=MUTED, bg=BG, font=("Consolas", 8))
        self.activity_label.pack(anchor="e", pady=(3, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=26, pady=(0, 20))
        body.grid_columnconfigure(0, weight=5)
        body.grid_columnconfigure(1, weight=4)
        body.grid_columnconfigure(2, weight=5)
        body.grid_rowconfigure(0, weight=1)
        self._build_reactor(body)
        self._build_mission(body)
        self._build_console(body)

    def _panel(self, parent, row=0, column=0, padx=0, pady=0, **kwargs):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=DIM, **kwargs)
        frame.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)
        return frame

    def _build_reactor(self, parent) -> None:
        shell = self._panel(parent, padx=(0, 9))
        self.canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

    def _build_mission(self, parent) -> None:
        col = tk.Frame(parent, bg=BG)
        col.grid(row=0, column=1, sticky="nsew", padx=(0, 9))
        col.grid_rowconfigure(1, weight=1)
        col.grid_rowconfigure(2, weight=1)
        col.grid_columnconfigure(0, weight=1)

        brain = self._panel(col)
        tk.Label(brain, text="NEURAL CORE", fg=MUTED, bg=PANEL, font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.provider = tk.Label(brain, text=self.brain.provider.upper(), fg=CYAN, bg=PANEL, font=("Consolas", 16, "bold"))
        self.provider.pack(anchor="w", padx=14)
        self.model = tk.Label(brain, text="", fg=WHITE, bg=PANEL, font=("Consolas", 8))
        self.model.pack(anchor="w", padx=14, pady=(1, 11))

        mission = self._panel(col, row=1, pady=(9, 9))
        tk.Label(mission, text="MISSION STATUS", fg=CYAN2, bg=PANEL, font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        self.task_label = tk.Label(mission, text="IDLE / AWAITING OBJECTIVE", fg=WHITE, bg=PANEL, font=("Segoe UI", 11, "bold"), wraplength=330, justify="left")
        self.task_label.pack(anchor="w", padx=14, pady=(0, 8))
        self.phase_label = tk.Label(mission, text="PHASE 01  /  READY", fg=GREEN, bg=PANEL, font=("Consolas", 8, "bold"))
        self.phase_label.pack(anchor="w", padx=14, pady=(0, 12))

        evidence = self._panel(col, row=2)
        tk.Label(evidence, text="EVIDENCE BOARD", fg=CYAN2, bg=PANEL, font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        self.evidence_title = tk.Label(evidence, text="No active investigation", fg=WHITE, bg=PANEL, font=("Segoe UI", 10, "bold"), wraplength=330, justify="left")
        self.evidence_title.pack(anchor="w", padx=14)
        self.evidence_status = tk.Label(evidence, text="STATUS  /  IDLE", fg=MUTED, bg=PANEL, font=("Consolas", 8))
        self.evidence_status.pack(anchor="w", padx=14, pady=(4, 4))
        self.evidence_findings = tk.Label(evidence, text="Findings: 0    Sources: 0", fg=WHITE, bg=PANEL, font=("Consolas", 8))
        self.evidence_findings.pack(anchor="w", padx=14, pady=(0, 12))

    def _build_console(self, parent) -> None:
        right = tk.Frame(parent, bg=BG)
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        head = tk.Frame(right, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.activity_line = tk.Label(head, text="◈  NEURAL LINK  /  READY", fg=CYAN2, bg=BG, font=("Consolas", 8, "bold"))
        self.activity_line.pack(side="left")
        tk.Label(head, text="LOCAL INTELLIGENCE", fg=MUTED, bg=BG, font=("Consolas", 7)).pack(side="right")

        self.log = scrolledtext.ScrolledText(right, bg=PANEL, fg=WHITE, insertbackground=CYAN, selectbackground="#10323e", relief="flat", bd=0, font=("Consolas", 9), wrap="word", padx=14, pady=12, spacing1=2, spacing3=6)
        self.log.grid(row=1, column=0, sticky="nsew")
        for tag, color in (("system", MUTED), ("user", CYAN), ("jarvis", WHITE), ("voice", AMBER)):
            self.log.tag_configure(tag, foreground=color)
        self._log("SYSTEM", "MISSION CONTROL ONLINE. AWAITING OBJECTIVE.")

        bar = tk.Frame(right, bg=BG)
        bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(bar, bg=PANEL2, fg=WHITE, insertbackground=CYAN, relief="flat", bd=0, font=("Segoe UI", 11))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=12)
        self.entry.bind("<Return>", lambda _: self._send())
        self._button(bar, "EXECUTE", self._send).grid(row=0, column=1, padx=(6, 0))
        self.mic = self._button(bar, "◉ MIC", self._voice)
        self.mic.grid(row=0, column=2, padx=(6, 0))

        telemetry = tk.Frame(right, bg=BG)
        telemetry.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        for i in range(4):
            telemetry.grid_columnconfigure(i, weight=1)
        self.metrics = []
        for i, name in enumerate(("CPU", "RAM", "GPU", "UPTIME")):
            box = tk.Frame(telemetry, bg=PANEL, highlightthickness=1, highlightbackground=DIM)
            box.grid(row=0, column=i, sticky="ew", padx=2)
            label = tk.Label(box, text=f"{name}\n--", fg=WHITE, bg=PANEL, font=("Consolas", 8, "bold"), pady=6)
            label.pack(fill="both", expand=True)
            self.metrics.append(label)
        tk.Label(right, text="WHISPER LOCAL  •  OLLAMA / CLAUDE  •  ONE AI BRAIN  •  ACTIONS VERIFIED", fg="#31525e", bg=BG, font=("Consolas", 7)).grid(row=4, column=0, sticky="w", pady=(6, 0))

    def _button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#092530", fg=CYAN, activebackground="#103b48", activeforeground=WHITE, relief="flat", bd=0, cursor="hand2", font=("Consolas", 8, "bold"), padx=13, pady=8)

    def _render(self) -> None:
        if not self.running:
            return
        c = self.canvas
        w, h = max(c.winfo_width(), 420), max(c.winfo_height(), 500)
        c.delete("all")
        cx, cy = w * .5, h * .49
        base = min(w, h) * .29
        t = time.monotonic()
        step = max(42, int(min(w, h) / 13))
        for x in range(0, w + step, step): c.create_line(x, 0, x, h, fill=GRID)
        for y in range(0, h + step, step): c.create_line(0, y, w, y, fill=GRID)
        for sx, sy in ((1,1),(-1,1),(1,-1),(-1,-1)):
            x, y, b = (18 if sx > 0 else w-18), (18 if sy > 0 else h-18), 26
            c.create_line(x, y, x+sx*b, y, fill=DIM, width=2)
            c.create_line(x, y, x, y+sy*b, fill=DIM, width=2)
        pulse = 1 + .025 * math.sin(t * 3)
        for factor, speed, count, outline, width in ((1,8,36,CYAN,2),(.82,-12,28,CYAN2,1),(.64,17,22,DIM,1)):
            r = base * factor * pulse
            for i in range(count):
                if (i + int(t*2)) % 5 == 0: continue
                start = i * 360 / count + t * speed
                c.create_arc(cx-r, cy-r, cx+r, cy+r, start=start, extent=360/count-4, style="arc", outline=outline, width=width)
        for i in range(72):
            a = math.radians(i*5 + t*(14 if i%2 else -7))
            r1, r2 = base*1.03, base*1.03 + (14 if i%6==0 else 6)
            c.create_line(cx+math.cos(a)*r1, cy+math.sin(a)*r1, cx+math.cos(a)*r2, cy+math.sin(a)*r2, fill=CYAN if i%6==0 else DIM, width=2 if i%6==0 else 1)
        core = base*.28*(1+.05*math.sin(t*4))
        for factor, outline in ((1.8,DIM),(1.4,CYAN2),(1,CYAN)):
            r=core*factor; c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=outline,width=2 if factor==1.4 else 1)
        c.create_oval(cx-core*.72,cy-core*.72,cx+core*.72,cy+core*.72,fill="#0a2c36",outline=CYAN,width=2)
        c.create_oval(cx-core*.28,cy-core*.28,cx+core*.28,cy+core*.28,fill=CYAN,outline=WHITE,width=1)
        c.create_text(cx, cy-8, text="J.A.R.V.I.S.", fill=WHITE, font=("Segoe UI", max(15,int(19*base/205)), "bold"))
        c.create_text(cx, cy+18, text=self.activity, fill=CYAN, font=("Consolas", 8, "bold"))
        for title, value, rx, ry in (("CORE","ACTIVE",.06,.16),("VOICE","READY",.73,.16),("SYSTEM","SECURE",.06,.83),("ACTION BUS","STANDBY",.73,.83)):
            c.create_text(w*rx,h*ry,text=title,anchor="w",fill=MUTED,font=("Consolas",7,"bold"))
            c.create_text(w*rx,h*ry+15,text=value,anchor="w",fill=CYAN,font=("Consolas",8,"bold"))
        self.root.after(40, self._render)

    def _status_tick(self) -> None:
        if not self.running: return
        try:
            if psutil:
                self.metrics[0].config(text=f"CPU\n{psutil.cpu_percent(None):.0f}%")
                self.metrics[1].config(text=f"RAM\n{psutil.virtual_memory().percent:.0f}%")
            self.metrics[2].config(text="GPU\nOK")
            elapsed=int(time.monotonic()-self.started)
            self.metrics[3].config(text=f"UPTIME\n{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}")
            p=self.brain.provider.upper(); self.provider.config(text=p)
            self.model.config(text=self.brain.config.claude_model if p=="CLAUDE" else self.brain.config.ollama_model)
            if self.execution:
                snap=self.execution.snapshot()
                objective=snap.get("command") or "IDLE / AWAITING OBJECTIVE"
                self.task_label.config(text=objective[:160])
                state=str(snap.get("state", "IDLE")).upper()
                self.phase_label.config(text=f"PHASE  /  {state}")
            if self.evidence:
                item=self.evidence.snapshot()
                self.evidence_title.config(text=str(item.get("title","Sin investigación activa"))[:130])
                self.evidence_status.config(text=f"STATUS  /  {str(item.get('status','IDLE')).upper()}")
                self.evidence_findings.config(text=f"Findings: {len(item.get('findings',[]))}    Sources: {len(item.get('sources',[]))}")
        except Exception:
            pass
        self.root.after(1000, self._status_tick)

    def set_state(self, state: str) -> None:
        self.activity = state.upper()
        if self.running: self.root.after(0, self._state_ui)

    def _state_ui(self) -> None:
        if not self.running: return
        self.activity_label.config(text=self.activity)
        self.activity_line.config(text=f"◈  NEURAL LINK  /  {self.activity}")
        if "LISTEN" in self.activity: self.status_label.config(text="● LISTENING", fg=AMBER)
        elif "PROCESS" in self.activity or "THINK" in self.activity: self.status_label.config(text="● PROCESSING", fg=CYAN)
        elif "SPEAK" in self.activity: self.status_label.config(text="● SPEAKING", fg=GREEN)
        else: self.status_label.config(text="● ONLINE", fg=GREEN)

    def _log(self, who: str, text: str) -> None:
        tag=who.lower()
        self.log.insert("end", f"[{who}]  {text}\n\n", tag if tag in {"system","user","jarvis","voice"} else "system")
        self.log.see("end")

    def add_message(self, who: str, text: str) -> None:
        if self.running: self.root.after(0, self._log, who, text)

    def _send(self) -> None:
        command=self.entry.get().strip()
        if not command: return
        self.entry.delete(0,"end"); self._log("USER",command); self.set_state("PROCESSING COMMAND")
        threading.Thread(target=self.process_command,args=(command,),daemon=True).start()

    def _voice(self) -> None:
        if self.listening: return
        self.listening=True; self.mic.config(text="◉ LISTENING",fg=WHITE); self._log("VOICE","MIC ARRAY ACTIVE // LISTENING"); self.set_state("LISTENING")
        threading.Thread(target=self._listen_worker,daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            command=self.voice.listen_for_command(seconds=7)
            if command:
                self.add_message("USER",command); self.set_state("PROCESSING COMMAND"); self.process_command(command)
            else: self.add_message("VOICE","No activation word detected.")
        except Exception as exc: self.add_message("VOICE",f"Error: {exc}")
        finally:
            if self.running: self.root.after(0,self._voice_idle)

    def _voice_idle(self) -> None:
        self.listening=False; self.mic.config(text="◉ MIC",fg=CYAN); self.set_state("SYSTEM READY")

    def set_response(self, text: str) -> None:
        self.set_state("SPEAKING"); self.add_message("JARVIS",text)
        self.root.after(max(1000,min(4500,len(text)*30)),lambda:self.set_state("SYSTEM READY"))

    def _close(self) -> None:
        self.running=False
        self.shutdown_callback()
        try: self.root.destroy()
        except tk.TclError: pass

    def run(self) -> None:
        self.root.mainloop()
