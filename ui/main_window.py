from __future__ import annotations

import math
import os
import sys
import threading
import time
import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, Signal, QObject, QSize
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QMovie, QPixmap, QImageReader, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFrame, QComboBox, QProgressBar,
    QSizePolicy, QStackedWidget, QSlider, QFormLayout, QFileSystemModel, QTreeView,
    QMessageBox, QToolButton, QGroupBox, QSpinBox, QCheckBox, QSplitter, QFileDialog, QTabWidget, QListWidget, QListWidgetItem, QScrollArea, QPlainTextEdit, QDialog, QDialogButtonBox, QInputDialog,
)

from config.settings import BASE_DIR, WORKSPACE_DIR
from config.user_profile import load_profile, save_profile
from core.orchestrator import Orchestrator
from tools.registry import list_tools, execute_tool
from memory.learning import get_learning_engine
from ui.voice import Speaker, Listener
from plugins.manager import get_plugin_manager

CYAN = "#18e7ff"; ICE = "#aafaff"; BLUE = "#0c6d8d"; BG = "#02060a"
PANEL = "#06131b"; PANEL2 = "#081c27"; PANEL3 = "#0b2632"; TEXT = "#e9fbff"
MUTED = "#6d99a8"; GREEN = "#27efaa"; RED = "#ff4e68"; AMBER = "#ffd166"
GRID = "#0a2935"; BORDER = "#12556b"

STYLE = f"""
* {{ font-family: 'Segoe UI'; color:{TEXT}; }}
QMainWindow, QWidget {{ background:{BG}; }}
QFrame#panel, QFrame#nav, QFrame#topbar, QFrame#statusbar {{
    background:{PANEL}; border:1px solid {BORDER}; border-radius:8px;
}}
QFrame#panel {{ background:{PANEL}; }}
QLabel#title {{ color:{CYAN}; font-size:14px; font-weight:800; letter-spacing:2px; }}
QLabel#sub {{ color:{MUTED}; font-size:9px; letter-spacing:1px; }}
QLabel#value {{ color:{ICE}; font-size:18px; font-weight:700; }}
QLabel#big {{ color:{ICE}; font-size:28px; font-weight:800; letter-spacing:4px; }}
QLabel#section {{ color:{CYAN}; font-size:11px; font-weight:800; letter-spacing:2px; }}
QLabel#tiny {{ color:{MUTED}; font-size:8px; letter-spacing:1px; }}
QPushButton {{
    background:#071a24; border:1px solid #15586b; border-radius:5px;
    padding:9px 12px; color:#dffcff; font-size:10px; font-weight:700;
}}
QPushButton:hover {{ background:#0b2d3b; border-color:{CYAN}; color:white; }}
QPushButton:pressed {{ background:#0f4252; }}
QPushButton#nav {{ text-align:left; padding:12px; border:1px solid transparent; background:transparent; }}
QPushButton#nav:hover, QPushButton#nav:checked {{ background:#092631; border:1px solid #0e7894; color:{CYAN}; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background:#030c12; border:1px solid #14495a; border-radius:5px;
    padding:8px; color:{TEXT};
}}
QTextEdit {{ selection-background-color:#0e6175; }}
QComboBox::drop-down {{ border:0; }}
QProgressBar {{ background:#020a0f; border:1px solid #123d4a; height:7px; border-radius:3px; }}
QProgressBar::chunk {{ background:{CYAN}; border-radius:3px; }}
QSlider::groove:horizontal {{ height:4px; background:#12303b; }}
QSlider::handle:horizontal {{ width:12px; margin:-5px 0; border-radius:6px; background:{CYAN}; }}
QTreeView {{ background:#030c12; border:1px solid #14495a; alternate-background-color:#06161e; }}
QTreeView::item:selected {{ background:#0b4656; }}
QGroupBox {{ border:1px solid #124b5d; margin-top:14px; padding-top:12px; color:{CYAN}; font-weight:700; }}
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 5px; }}
"""


class Worker(QObject):
    done = Signal(str, float)
    busy = Signal(bool)
    mode = Signal(str)
    def __init__(self, router, text, deep):
        super().__init__(); self.router=router; self.text=text; self.deep=deep
    def run(self):
        self.busy.emit(True); self.mode.emit("THINKING"); started=time.perf_counter()
        try:
            result=self.router.handle(self.text, deep=self.deep)
        except Exception as exc:
            result=f"Error: {exc}"
        self.done.emit(str(result), time.perf_counter()-started); self.busy.emit(False)


class ProactiveWorker(QObject):
    done = Signal(str)
    def __init__(self, router):
        super().__init__(); self.router = router
    def run(self):
        try:
            self.done.emit(str(self.router.generate_proactive_question()))
        except Exception:
            self.done.emit("")


class Panel(QFrame):
    def __init__(self, title, code="SYS-01", subtitle="LIVE"):
        super().__init__(); self.setObjectName("panel")
        lay=QVBoxLayout(self); lay.setContentsMargins(12,10,12,12); lay.setSpacing(8)
        h=QHBoxLayout();
        a=QLabel("◆"); a.setStyleSheet(f"color:{CYAN};font-size:8px"); h.addWidget(a)
        t=QLabel(title.upper()); t.setObjectName("title"); h.addWidget(t)
        if subtitle: s=QLabel(subtitle.upper()); s.setObjectName("sub"); h.addWidget(s)
        h.addStretch(); c=QLabel(code); c.setObjectName("tiny"); h.addWidget(c); lay.addLayout(h)
        self.body=lay
    def add(self,w,stretch=0): self.body.addWidget(w,stretch)
    def addLayout(self, layout, stretch=0): self.body.addLayout(layout, stretch)


class Metric(Panel):
    def __init__(self, title, code):
        super().__init__(title,code,"TELEMETRY"); self.val=QLabel("--"); self.val.setObjectName("value"); self.add(self.val)
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setTextVisible(False); self.add(self.bar)
    def set_value(self, value):
        self.val.setText(str(value));
        try: self.bar.setValue(int(float(str(value).replace('%',''))))
        except Exception: self.bar.setValue(0)


class NeuralBrain(QWidget):
    """Cinematic 3-D neural sphere. The core reacts to thinking, listening and speech."""
    def __init__(self):
        super().__init__()
        self.mode="IDLE"
        self.phase=0.0
        self.stats={}
        self.speaking=False
        self.setMinimumSize(520,520)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(25)

    def set_mode(self,m):
        self.mode=m.upper()
        self.update()

    def set_speaking(self,value):
        self.speaking=bool(value)
        if value:
            self.mode="SPEAKING"
        elif self.mode=="SPEAKING":
            self.mode="IDLE"
        self.update()

    def set_stats(self,s):
        self.stats=dict(s or {})
        self.update()

    def tick(self):
        speed={"IDLE":.018,"LISTENING":.052,"THINKING":.105,"EXECUTING":.14,"SPEAKING":.18}.get(self.mode,.025)
        self.phase += speed
        self.update()

    def _ellipse_point(self,cx,cy,rx,ry,a):
        return QPointF(cx+math.cos(a)*rx, cy+math.sin(a)*ry)

    def paintEvent(self,_):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r=self.rect()
        p.fillRect(r,QColor(BG))
        cx=r.center().x()
        cy=r.center().y()-12
        R=min(r.width(),r.height())*.27
        active=self.mode in {"THINKING","EXECUTING","SPEAKING","LISTENING"}
        intensity=1.0 if self.speaking else .72 if active else .42

        # Engineering grid clipped to the panel.
        p.setPen(QPen(QColor(GRID),1))
        for x in range(0,r.width(),24): p.drawLine(x,0,x,r.height())
        for y in range(0,r.height(),24): p.drawLine(0,y,r.width(),y)

        p.setPen(QPen(QColor(CYAN),2))
        for x,y,sx,sy in ((18,18,1,1),(r.width()-18,18,-1,1),(18,r.height()-18,1,-1),(r.width()-18,r.height()-18,-1,-1)):
            p.drawLine(x,y,x+sx*35,y); p.drawLine(x,y,x,y+sy*35)

        # 3-D sphere: concentric rings + perspective longitude/latitude ellipses.
        sphere=min(R*1.02, min(r.width(), r.height())*.275)
        for i in range(10):
            rr=sphere*(1.0-i*.065)
            alpha=max(18,int(90-i*6)*int(0.65+intensity*.35))
            p.setPen(QPen(QColor(24,231,255,alpha),2 if i in (0,9) else 1))
            p.drawEllipse(QPointF(cx,cy),rr,rr)

        # Rotating longitude meridians create the 3-D effect.
        rot=self.phase*.72
        for i in range(9):
            a=rot+i*math.pi/9
            rx=abs(math.sin(a))*sphere
            rx=max(2.0,rx)
            p.setPen(QPen(QColor(24,231,255,75 if i%2 else 125),1))
            p.drawEllipse(QPointF(cx,cy),rx,sphere)

        # Latitude bands tilt and rotate like a holographic globe.
        for i in range(-4,5):
            lat=i/5
            ry=sphere*math.sqrt(max(.08,1-lat*lat))*.23
            yy=cy+lat*sphere*.72
            rx=sphere*math.sqrt(max(.08,1-lat*lat))
            p.setPen(QPen(QColor(170,250,255,70 if i else 125),1))
            p.drawEllipse(QPointF(cx,yy),rx,ry)

        # Radial ticks around the sphere.
        for i in range(96):
            a=rot+i*math.tau/96
            outer=sphere*1.10
            inner=outer-(17 if i%8==0 else 7)
            alpha=145 if i%8==0 else 42
            color = QColor(CYAN)
            color.setAlpha(alpha)
            p.setPen(QPen(color, 2 if i % 8 == 0 else 1))
            p.drawLine(self._ellipse_point(cx,cy,inner,inner,a),self._ellipse_point(cx,cy,outer,outer,a))

        # Neural nodes distributed over the sphere surface.
        nodes=[]
        rings=9
        for ring in range(rings):
            phi=-math.pi/2+(ring+1)*math.pi/(rings+1)
            rr=sphere*math.cos(phi)
            yy=cy+sphere*math.sin(phi)
            count=10+ring*2
            for j in range(count):
                a=rot*.9+j*math.tau/count+ring*.23
                x=cx+rr*math.cos(a)
                y=yy+rr*.20*math.sin(a)
                nodes.append(QPointF(x,y))

        p.setPen(QPen(QColor(24,231,255,48),1))
        for i,a in enumerate(nodes):
            for j in (1,2,5):
                if i+j < len(nodes):
                    b=nodes[i+j]
                    if (a.x()-b.x())**2+(a.y()-b.y())**2 < (sphere*.42)**2:
                        p.drawLine(a,b)

        for i,n in enumerate(nodes):
            wave=(math.sin(self.phase*(8 if active else 3)+i*.37)+1)/2
            rad=1.2+wave*(3.6 if active else 2.1)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(170,250,255,65+int(wave*170*intensity))))
            p.drawEllipse(n,rad,rad)

        # Core reactor / arc reactor at the center.
        pulse=34+(15 if self.speaking else 8)*math.sin(self.phase*(8 if active else 4))
        glow=QRadialGradient(QPointF(cx,cy),100)
        glow.setColorAt(0,QColor(220,255,255,220))
        glow.setColorAt(.18,QColor(24,231,255,145))
        glow.setColorAt(.55,QColor(24,231,255,45))
        glow.setColorAt(1,QColor(24,231,255,0))
        p.setBrush(QBrush(glow)); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(cx,cy),100,100)
        p.setBrush(QBrush(QColor(3,18,25,248))); p.setPen(QPen(QColor(ICE),2)); p.drawEllipse(QPointF(cx,cy),pulse,pulse)
        p.setPen(QPen(QColor(CYAN),2)); p.drawEllipse(QPointF(cx,cy),pulse*.64,pulse*.64)
        pulse_color = QColor(CYAN); pulse_color.setAlpha(145); p.setBrush(QBrush(pulse_color)); p.drawEllipse(QPointF(cx,cy),pulse*.27,pulse*.27)

        # Rotating data arcs and a moving sweep.
        for j in range(4):
            rr=sphere*(1.16+j*.055)
            ring_color = QColor(CYAN); ring_color.setAlpha(max(0, 125-j*22)); p.setPen(QPen(ring_color,2))
            p.drawArc(int(cx-rr),int(cy-rr),int(rr*2),int(rr*2),int((self.phase*95+j*55)%360)*16,190*16)
        sweep=int((math.sin(self.phase*.65)+1)*.5*(r.height()-100))+50
        sweep_color = QColor(CYAN); sweep_color.setAlpha(65); p.setPen(QPen(sweep_color,1)); p.drawLine(30,sweep,r.width()-30,sweep)

        # Voice / system waveform.
        basey=r.height()-52
        amp=16 if self.speaking else (9 if self.mode=="IDLE" else 24)
        beam_color = QColor(CYAN); beam_color.setAlpha(190); p.setPen(QPen(beam_color,2)); prev=None
        for x in range(30,r.width()-30,4):
            y=basey+math.sin(x*.055+self.phase*10)*amp*(.35+.65*math.sin(x*.013)**2)
            point=QPointF(x,y)
            if prev: p.drawLine(prev,point)
            prev=point

        p.setPen(QPen(QColor(MUTED),1)); p.setFont(QFont("Segoe UI",8))
        p.drawText(34,40,"NEURAL SPHERE // 3D CORTEX")
        p.drawText(34,r.height()-22,f"NODES {self.stats.get('nodes',0):04d}   SYNAPSES {self.stats.get('edges',0):04d}   ERRORS {self.stats.get('errors',0):04d}")
        p.drawText(r.width()-190,40,f"STATE // {self.mode}")


class ArmorPanel(Panel):
    """Armor display with real QMovie support and a fallback animated hologram."""
    def __init__(self):
        super().__init__("ARMOR BAY", "ARM-07", "HOLOGRAPHIC")
        self.view=QLabel()
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumHeight(260)
        self.view.setStyleSheet("background:#02080d;border:1px solid #123e4c;border-radius:6px;")
        self.movie=None
        self.pixmap=None
        self.motion=0.0
        self.frame_label=QLabel("FRAME 01")
        self.power_label=QLabel("POWER 94%")
        self.link_label=QLabel("LINK ONLINE")
        path=BASE_DIR/"assets"/"armor.gif"
        if path.exists():
            fmt=QImageReader(str(path)).format().data().decode(errors="ignore").lower()
            if fmt=="gif":
                self.movie=QMovie(str(path))
                self.movie.setCacheMode(QMovie.CacheAll)
                self.movie.frameChanged.connect(self._movie_frame)
                self.view.setMovie(self.movie)
                # The armor asset can be very tall. Fit the complete animation
                # inside the available ARMOR BAY area while preserving its
                # original aspect ratio. Never force a fixed 320x360 frame.
                self._fit_movie()
                self.movie.start()
            else:
                # The supplied "Gif.gif" is a single RGBA PNG. Keep it, but animate it as a hologram.
                self.pixmap=QPixmap(str(path))
                self.view.setText("")
                self._update_static_armor()
        else:
            self.view.setText("ARMOR ASSET OFFLINE\nassets/armor.gif")
        self.add(self.view,1)
        row=QHBoxLayout()
        for w in (self.frame_label,self.power_label,self.link_label):
            w.setObjectName("tiny"); row.addWidget(w)
        self.body.addLayout(row)
        self.motion_timer=QTimer(self)
        self.motion_timer.timeout.connect(self._animate_armor)
        self.motion_timer.start(35)

    def _movie_frame(self,frame):
        self.frame_label.setText(f"FRAME {frame+1:02d}")

    def _animate_armor(self):
        self.motion += .055
        power=92+int(3*(math.sin(self.motion*1.8)+1)/2)
        self.power_label.setText(f"POWER {power}%")
        if self.pixmap and self.movie is None:
            self._update_static_armor()

    def _update_static_armor(self):
        if not self.pixmap or self.pixmap.isNull(): return
        box=self.view.size()
        maxw=max(100,min(320,box.width()-18)); maxh=max(140,min(360,box.height()-18))
        scale=1.0+.035*math.sin(self.motion*2.0)
        w=max(80,int(maxw*scale)); h=max(120,int(maxh*scale))
        pm=self.pixmap.scaled(w,h,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        self.view.setPixmap(pm)

    def _fit_movie(self):
        if not self.movie:
            return
        box=self.view.size()
        if box.width() < 20 or box.height() < 20:
            return
        source=self.movie.currentPixmap().size()
        if source.isEmpty():
            source=QImageReader(str(BASE_DIR/"assets"/"armor.gif")).size()
        if source.isEmpty():
            return
        margin=18
        avail_w=max(80, box.width()-margin)
        avail_h=max(100, box.height()-margin)
        scale=min(avail_w/source.width(), avail_h/source.height())
        # Keep a sensible maximum so a large panel does not make the armor huge.
        scale=min(scale, 1.0)
        target=QSize(max(1,int(source.width()*scale)), max(1,int(source.height()*scale)))
        self.movie.setScaledSize(target)

    def resizeEvent(self,e):
        super().resizeEvent(e)
        if self.movie:
            self._fit_movie()
        elif self.pixmap:
            self._update_static_armor()


class CommandStream(QTextEdit):
    def __init__(self):
        super().__init__(); self.setReadOnly(True); self.setObjectName("commandStream"); self.setStyleSheet(f"background:#020a0f;border:1px solid #123e4c;color:{TEXT};font-size:10px;padding:10px;")
    def add(self,who,text):
        ts=time.strftime("%H:%M:%S"); color=CYAN if who=="JARVIS" else ICE if who=="YOU" else AMBER
        self.append(f'<span style="color:{MUTED}">[{ts}]</span> <b style="color:{color}">{who}</b><br>{str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace(chr(10),"<br>")}<br>')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("J.A.R.V.I.S // NEURAL COMMAND DECK"); self.resize(1600,960); self.setMinimumSize(1250,780); self.setStyleSheet(STYLE)
        self.profile=load_profile(); self.router=Orchestrator(); self.speaker=Speaker(); self.listener=Listener(); self.learning=get_learning_engine(); self.busy=False
        self.last_activity=time.monotonic(); self._proactive_busy=False; self._proactive_thread=None; self._proactive_worker=None
        self.speaker.configure(self.profile.get("voice", {}))
        self._build(); self._connect(); self._telemetry_timer=QTimer(self); self._telemetry_timer.timeout.connect(self.telemetry); self._telemetry_timer.start(1000); self.telemetry(); self._maintenance_timer=QTimer(self); self._maintenance_timer.timeout.connect(self.router.maintenance_async); self._maintenance_timer.start(300000); self._proactive_timer=QTimer(self); self._proactive_timer.timeout.connect(self._proactive_tick); self._proactive_timer.start(15000); QTimer.singleShot(3500,self.router.maintenance_async)
        self.append("SYSTEM","JARVIS CORE ONLINE. NEURAL MEMORY LINKED. SELF-REPAIR ENGINE ARMED.")
    def _build(self):
        root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); outer.setContentsMargins(10,10,10,8); outer.setSpacing(8)
        # top bar
        top=QFrame(); top.setObjectName("topbar"); tl=QHBoxLayout(top); tl.setContentsMargins(16,8,16,8)
        brand=QLabel("J.A.R.V.I.S"); brand.setObjectName("big"); tl.addWidget(brand)
        badge=QLabel("  NEURAL COMMAND DECK  //  V16  "); badge.setStyleSheet(f"color:{CYAN};font-size:10px;font-weight:700;background:#061b24;padding:7px;border:1px solid #12556b;"); tl.addWidget(badge); tl.addStretch()
        self.mode=QComboBox(); self.mode.addItems(["AUTO // ADAPTIVE","FAST // LOW LATENCY","DEEP // MAX REASONING"]); tl.addWidget(self.mode)
        self.status=QLabel("● ONLINE"); self.status.setStyleSheet(f"color:{GREEN};font-weight:800;padding:8px;"); tl.addWidget(self.status); self.clock=QLabel("00:00:00"); self.clock.setObjectName("value"); tl.addWidget(self.clock); outer.addWidget(top)
        # main split
        split=QSplitter(Qt.Horizontal); split.setHandleWidth(5); outer.addWidget(split,1)
        # nav
        nav=QFrame(); nav.setObjectName("nav"); nv=QVBoxLayout(nav); nv.setContentsMargins(10,12,10,10); nv.setSpacing(3)
        nl=QLabel("CONTROL MATRIX"); nl.setObjectName("section"); nv.addWidget(nl)
        self.nav_buttons={};
        for key,label in [("dashboard","⌂  COMMAND DECK"),("conversation","◈  CONVERSATION"),("workspace","▣  WORKSPACE"),("tools","⚒  TOOLS"),("system","◉  SYSTEM"),("aicore","◆  AI CORE"),("memory","◎  NEURAL MEMORY"),("personality","◇  PERSONALITY"),("voice","♫  VOICE"),("vision","◌  VISION"),("settings","⚙  SETTINGS"),("plugins","▦  PLUGIN MATRIX")]:
            b=QPushButton(label); b.setObjectName("nav"); b.setCheckable(True); self.nav_buttons[key]=b; nv.addWidget(b)
        nv.addStretch(); self.nav_diag=QLabel("CORE  ● ONLINE\nTOOLS  --\nMEMORY ● LINKED\nREPAIR ● ARMED\nDELETE ● BLOCKED"); self.nav_diag.setObjectName("tiny"); nv.addWidget(self.nav_diag); split.addWidget(nav)
        # pages
        self.pages=QStackedWidget(); split.addWidget(self.pages); split.setSizes([210,1390])
        self._build_dashboard(); self._build_conversation(); self._build_workspace(); self._build_tools(); self._build_system(); self._build_ai(); self._build_memory(); self._build_personality(); self._build_voice(); self._build_vision(); self._build_settings(); self._build_plugins()
        self.show_page("dashboard")
        # footer
        foot=QFrame(); foot.setObjectName("statusbar"); fl=QHBoxLayout(foot); fl.setContentsMargins(12,6,12,6); self.footer_state=QLabel("● READY"); self.footer_ai=QLabel("OLLAMA // QWEN"); self.footer_cpu=QLabel("CPU --"); self.footer_ram=QLabel("RAM --"); self.footer_tools=QLabel("TOOLS --"); self.footer_mem=QLabel("MEMORY --"); self.footer_repair=QLabel("REPAIR READY")
        for w in (self.footer_state,self.footer_ai,self.footer_cpu,self.footer_ram,self.footer_tools,self.footer_mem,self.footer_repair): fl.addWidget(w); fl.addSpacing(20)
        fl.addStretch(); fl.addWidget(QLabel("LOCAL CONTROL // DESTRUCTIVE DELETE BLOCKED")); outer.addWidget(foot)
    def _page(self,title,code):
        page=QWidget(); lay=QVBoxLayout(page); lay.setContentsMargins(12,12,12,12); lay.setSpacing(10); head=QHBoxLayout(); t=QLabel(title.upper()); t.setObjectName("big"); head.addWidget(t); head.addStretch(); c=QLabel(code); c.setObjectName("sub"); head.addWidget(c); lay.addLayout(head); self.pages.addWidget(page); return page,lay
    def _build_dashboard(self):
        page,lay=self._page("JARVIS // COMMAND DECK","DECK-01")
        top=QGridLayout(); top.setSpacing(8); self.cpu=Metric("CPU LOAD","TEL-01"); self.ram=Metric("RAM LOAD","TEL-02"); self.disk=Metric("DISK","TEL-03"); self.neural=Metric("NEURAL MEMORY","MEM-01"); top.addWidget(self.cpu,0,0); top.addWidget(self.ram,0,1); top.addWidget(self.disk,0,2); top.addWidget(self.neural,0,3); lay.addLayout(top)
        mid=QSplitter(Qt.Horizontal); mid.setHandleWidth(5)
        center=Panel("NEURAL CORE","CORE-01","ANIMATED")
        self.brain=NeuralBrain(); center.add(self.brain,1)
        armor=ArmorPanel(); mid.addWidget(center); mid.addWidget(armor); mid.setSizes([800,380]); lay.addWidget(mid,1)
        bottom=QHBoxLayout(); self.activity=Panel("LIVE ACTIVITY","ACT-01","STREAM"); self.activity_text=QLabel("SYSTEM READY\nWAITING FOR COMMANDS..."); self.activity_text.setObjectName("sub"); self.activity.add(self.activity_text); bottom.addWidget(self.activity,1)
        quick=Panel("MISSION CONSOLE","CMD-01","QUICK ACTIONS"); self.quick=QLineEdit(); self.quick.setPlaceholderText("Habla o escribe una orden para JARVIS..."); quick.add(self.quick)
        qr=QHBoxLayout(); self.quick_send=QPushButton("EXECUTE"); self.quick_listen=QPushButton("MIC / LISTEN"); self.quick_workspace=QPushButton("OPEN WORKSPACE"); qr.addWidget(self.quick_send); qr.addWidget(self.quick_listen); qr.addWidget(self.quick_workspace); quick.body.addLayout(qr); bottom.addWidget(quick,2); lay.addLayout(bottom)
    def _build_conversation(self):
        page,lay=self._page("CONVERSATION // ADAPTIVE JARVIS","CHAT-01")

        # Chat occupies the main area. The old "COMMAND INPUT" panel was redundant;
        # controls now describe useful session state while the input lives below the chat.
        row=QHBoxLayout()
        self.stream=CommandStream()
        row.addWidget(self.stream,4)

        side=Panel("JARVIS BEHAVIOR","AI-01","ADAPTIVE")
        personality=QLabel("ADAPTIVE PERSONALITY\n\nJARVIS ajusta tono, detalle, tecnicismo y ritmo según cómo hables en cada momento.\n\nNo copia errores de escritura ni infiere datos sensibles.")
        personality.setObjectName("sub")
        personality.setWordWrap(True)
        side.add(personality)

        self.adaptive_status=QLabel("● PERSONALITY // ADAPTIVE\n● MEMORY // ACTIVE\n● REASONING // AUTO")
        self.adaptive_status.setObjectName("tiny")
        side.add(self.adaptive_status)

        self.listen_btn=QPushButton("🎙 LISTEN")
        self.voice_check=QCheckBox("VOICE RESPONSE")
        self.voice_check.setChecked(True)
        side.add(self.listen_btn)
        side.add(self.voice_check)

        clear=QPushButton("CLEAR SESSION")
        clear.clicked.connect(lambda:(self.stream.clear(),self.router.reset(),self._touch_activity(),self.adaptive_status.setText("● PERSONALITY // ADAPTIVE\n● MEMORY // ACTIVE\n● SESSION // RESET")))
        side.add(clear)

        side_note=QLabel("La conversación se adapta automáticamente. No necesitas configurar un 'Command Input' separado.")
        side_note.setWordWrap(True); side_note.setObjectName("tiny"); side.add(side_note)
        row.addWidget(side,1)
        lay.addLayout(row,1)

        input_row=QHBoxLayout()
        self.input=QLineEdit()
        self.input.setPlaceholderText("Habla con JARVIS… escribe una pregunta, tarea o conversación")
        self.send=QPushButton("SEND")
        input_row.addWidget(self.input,1); input_row.addWidget(self.send)
        lay.addLayout(input_row)

    def _build_workspace(self):
        page,lay=self._page("WORKSPACE // PROJECT CONTROL","WORK-01"); bar=QHBoxLayout(); self.workspace_path=QLineEdit(str(WORKSPACE_DIR)); openb=QPushButton("OPEN IN EXPLORER"); refresh=QPushButton("REFRESH"); newfolder=QPushButton("NEW FOLDER"); importb=QPushButton("IMPORT FILES"); bar.addWidget(self.workspace_path,1); bar.addWidget(openb); bar.addWidget(refresh); bar.addWidget(newfolder); bar.addWidget(importb); lay.addLayout(bar)
        self.fs=QFileSystemModel(); self.fs.setRootPath(str(WORKSPACE_DIR)); self.tree=QTreeView(); self.tree.setModel(self.fs); self.tree.setRootIndex(self.fs.index(str(WORKSPACE_DIR))); self.tree.setColumnWidth(0,360); lay.addWidget(self.tree,1)
        info=QLabel("Importa archivos para que JARVIS pueda leerlos y trabajarlos. Documentos: PDF/DOCX/XLSX/PPTX. Los originales no se eliminan."); info.setObjectName("sub"); lay.addWidget(info)
        openb.clicked.connect(lambda: execute_tool("open_workspace")); importb.clicked.connect(self.import_files); refresh.clicked.connect(lambda:self.tree.setRootIndex(self.fs.index(str(WORKSPACE_DIR)))); newfolder.clicked.connect(self.new_folder)
    def _build_tools(self):
        page,lay=self._page("TOOL MATRIX // CAPABILITIES","TOOL-01")
        head=QHBoxLayout()
        self.tool_search=QLineEdit()
        self.tool_search.setPlaceholderText("Buscar herramienta por nombre, función o parámetro...")
        self.tool_category=QComboBox()
        self.tool_category.addItems(["ALL TOOLS","SYSTEM","FILES","DOCUMENTS","MEDIA","WEB","INPUT","AI / REPAIR"])
        refresh=QPushButton("REFRESH MATRIX")
        head.addWidget(self.tool_search,1); head.addWidget(self.tool_category); head.addWidget(refresh)
        lay.addLayout(head)

        info=Panel("TOOL FABRIC","TOOL-02","38 CAPABILITIES")
        self.tool_summary=QLabel()
        self.tool_summary.setObjectName("sub")
        self.tool_summary.setWordWrap(True)
        info.add(self.tool_summary)
        lay.addWidget(info)

        self.tool_scroll=QScrollArea()
        self.tool_scroll.setWidgetResizable(True)
        self.tool_scroll.setFrameShape(QFrame.NoFrame)
        self.tool_container=QWidget()
        self.tool_grid=QGridLayout(self.tool_container)
        self.tool_grid.setSpacing(8)
        self.tool_scroll.setWidget(self.tool_container)
        lay.addWidget(self.tool_scroll,1)

        self.tool_search.textChanged.connect(self.refresh_tools)
        self.tool_category.currentTextChanged.connect(self.refresh_tools)
        refresh.clicked.connect(self.refresh_tools)
        self.refresh_tools()

    def _tool_category(self,name):
        n=name.lower()
        if any(x in n for x in ("pdf","docx","xlsx","pptx","file","folder","archive","organize","workspace")): return "FILES" if not any(x in n for x in ("pdf","docx","xlsx","pptx")) else "DOCUMENTS"
        if "music" in n: return "MEDIA"
        if "google" in n or "url" in n: return "WEB"
        if any(x in n for x in ("mouse","keys","text")): return "INPUT"
        if any(x in n for x in ("repair","audit","inspect")): return "AI / REPAIR"
        return "SYSTEM"

    def refresh_tools(self):
        if not hasattr(self,"tool_grid"): return
        while self.tool_grid.count():
            item=self.tool_grid.takeAt(0)
            widget=item.widget()
            if widget: widget.deleteLater()
        query=self.tool_search.text().strip().lower()
        category=self.tool_category.currentText()
        tools=list_tools()
        visible=[]
        for name,data in tools.items():
            blob=(name+" "+data.get("description","")+" "+" ".join(data.get("parameters",{}))).lower()
            if query and query not in blob: continue
            if category!="ALL TOOLS" and self._tool_category(name)!=category: continue
            visible.append((name,data))
        self.tool_summary.setText(f"{len(visible)} herramientas visibles / {len(tools)} registradas. Cada herramienta se ejecuta mediante el mismo registro que utiliza el motor de JARVIS.")
        for i,(name,data) in enumerate(visible):
            box=Panel(name.replace('_',' '),f"T-{i+1:02d}","READY")
            d=QLabel(data["description"]); d.setWordWrap(True); d.setObjectName("sub"); box.add(d)
            params=list(data.get("parameters",{}))
            box.add(QLabel("PARAMETERS // "+(", ".join(params) if params else "NONE")))
            run=QPushButton("EXECUTE TOOL")
            run.clicked.connect(lambda checked=False,n=name:self.execute_tool_ui(n))
            box.add(run)
            self.tool_grid.addWidget(box,i//3,i%3)
        self.tool_grid.setRowStretch((len(visible)+2)//3,1)

    def execute_tool_ui(self,name):
        data=list_tools().get(name)
        if not data: return
        params=data.get("parameters",{})
        kwargs={}
        for key,spec in params.items():
            if isinstance(spec,dict):
                hint=spec.get("description",spec.get("type","value"))
            else: hint=str(spec)
            value,ok=QInputDialog.getText(self,"EXECUTE // "+name.upper(),f"{key}\n{hint}")
            if not ok: return
            if isinstance(spec,dict):
                typ=spec.get("type","string")
                try:
                    if typ=="integer": value=int(value)
                    elif typ=="number": value=float(value)
                    elif typ=="boolean": value=value.strip().lower() in {"1","true","yes","si","sí"}
                    elif typ=="array": value=json.loads(value)
                except Exception as exc:
                    QMessageBox.warning(self,"INVALID PARAMETER",f"{key}: {exc}"); return
            kwargs[key]=value
        try:
            result=execute_tool(name,**kwargs)
            self.append("SYSTEM",f"TOOL // {name}\n{result}")
            self.footer_state.setText(f"● TOOL // {name.upper()}")
        except Exception as exc:
            QMessageBox.critical(self,"TOOL ERROR",f"{name}\n\n{exc}")
            self.append("SYSTEM",f"TOOL ERROR // {name}: {exc}")

    def _build_system(self):
        page,lay=self._page("SYSTEM // TELEMETRY","SYS-01"); grid=QGridLayout(); self.sysinfo=QTextEdit(); self.sysinfo.setReadOnly(True); self.runtime=QTextEdit(); self.runtime.setReadOnly(True); self.services=QTextEdit(); self.services.setReadOnly(True); self.diag=QTextEdit(); self.diag.setReadOnly(True)
        for i,(title,w) in enumerate([("HARDWARE",self.sysinfo),("RUNTIME",self.runtime),("SERVICES",self.services),("DIAGNOSTICS",self.diag)]): box=Panel(title,f"SYS-{i+1:02d}"); box.add(w,1); grid.addWidget(box,i//2,i%2)
        lay.addLayout(grid,1)
    def _build_ai(self):
        page,lay=self._page("AI CORE // PROVIDERS + REASONING","AI-01"); grid=QGridLayout(); box=Panel("LOCAL PROVIDER","AI-02","OLLAMA"); self.model_edit=QLineEdit(self.router.provider.model); self.host_edit=QLineEdit(self.router.provider.host); box.add(QLabel("MODEL")); box.add(self.model_edit); box.add(QLabel("HOST")); box.add(self.host_edit); applyb=QPushButton("APPLY MODEL"); box.add(applyb); applyb.clicked.connect(self.apply_model); grid.addWidget(box,0,0)
        providers=Panel("CLOUD PROVIDERS","AI-03",".ENV LINKED"); self.ai_status_labels={};
        for pname, label in [("ChatGPT","OPENAI"),("Gemini","GEMINI"),("Claude","CLAUDE"),("Grok","GROK")]:
            lab=QLabel(f"{label:<8}  ○ CHECKING..."); providers.add(lab); self.ai_status_labels[pname]=lab
        providers.add(QLabel("Keys are loaded only from the local .env file. AUTO uses a cloud brain for normal dialogue and Ollama for registered tool execution.")); grid.addWidget(providers,0,1)
        reason=Panel("REASONING ENGINE","AI-04","ADAPTIVE"); reason.add(QLabel("AUTO chooses speed vs depth per task.")); reason.add(QLabel("DEEP enables extended tool loops and verification.")); reason.add(QLabel("LEARNING CONTEXT is retrieved from verified experiences.")); reason.add(QLabel("SELF-REPAIR activates only on detected code failures.")); grid.addWidget(reason,1,0,1,2); lay.addLayout(grid,1)
    def _build_memory(self):
        page,lay=self._page("NEURAL MEMORY // LEARNING","MEM-01"); top=QHBoxLayout(); self.mem_nodes=Metric("NODES","M-01"); self.mem_edges=Metric("SYNAPSES","M-02"); self.mem_errors=Metric("ERRORS","M-03"); self.mem_success=Metric("SUCCESSES","M-04");
        for x in (self.mem_nodes,self.mem_edges,self.mem_errors,self.mem_success): top.addWidget(x)
        lay.addLayout(top); row=QHBoxLayout(); self.memory_graph=QTextEdit(); self.memory_graph.setReadOnly(True); self.memory_recent=QTextEdit(); self.memory_recent.setReadOnly(True); a=Panel("NEURAL GRAPH","MEM-02","LIVE"); a.add(self.memory_graph,1); b=Panel("EXPERIENCE LOG","MEM-03","PERSISTENT"); b.add(self.memory_recent,1); row.addWidget(a,1); row.addWidget(b,1); lay.addLayout(row,1)
    def _build_personality(self):
        page,lay=self._page("PERSONALITY MATRIX","PER-01"); form=QFormLayout(); self.name=QLineEdit(self.profile.get('personality',{}).get('name','JARVIS')); self.tone=QLineEdit(self.profile.get('personality',{}).get('tone','Profesional')); self.style=QTextEdit(self.profile.get('personality',{}).get('style','Claro, directo y proactivo')); form.addRow("NAME",self.name); form.addRow("TONE",self.tone); form.addRow("STYLE",self.style); box=Panel("BEHAVIOR PARAMETERS","PER-02","USER CONFIGURED"); box.addLayout(form); self.personality_sliders={}
        for key,label in [("proactivity","PROACTIVITY"),("creativity","CREATIVITY"),("humor","HUMOR"),("verbosity","VERBOSITY")]:
            row=QHBoxLayout(); row.addWidget(QLabel(label)); s=QSlider(Qt.Horizontal); s.setRange(0,100); s.setValue(int(self.profile.get('personality',{}).get(key,70))); v=QLabel(str(s.value())); s.valueChanged.connect(lambda val,v=v:v.setText(str(val))); row.addWidget(s); row.addWidget(v); box.body.addLayout(row); self.personality_sliders[key]=s
        save=QPushButton("SAVE PERSONALITY"); box.add(save); save.clicked.connect(self.save_personality); lay.addWidget(box,1)
    def _build_voice(self):
        page,lay=self._page("VOICE // AUDIO MATRIX","VOX-01"); box=Panel("TEXT TO SPEECH","VOX-02","LOCAL"); self.voice_combo=QComboBox();
        try:
            import pyttsx3
            e=pyttsx3.init()
            for voice in e.getProperty('voices') or []: self.voice_combo.addItem(str(voice.name),str(voice.id))
            e.stop()
        except Exception: self.voice_combo.addItem("Default Windows Voice","")
        box.add(QLabel("VOICE")); box.add(self.voice_combo); self.rate=QSlider(Qt.Horizontal); self.rate.setRange(80,260); self.rate.setValue(int(self.profile.get('voice',{}).get('rate',185))); box.add(QLabel("SPEED")); box.add(self.rate); self.volume=QSlider(Qt.Horizontal); self.volume.setRange(0,100); self.volume.setValue(int(self.profile.get('voice',{}).get('volume',1)*100)); box.add(QLabel("VOLUME")); box.add(self.volume); save=QPushButton("SAVE + TEST VOICE"); box.add(save); save.clicked.connect(self.save_voice); lay.addWidget(box); lay.addStretch()
    def _build_vision(self):
        page,lay=self._page("VISION // PERCEPTION","VIS-01")
        row=QHBoxLayout()
        cam=Panel("LIVE CAMERA","VIS-02","OPTIONAL")
        self.camera_view=QLabel("CAMERA OFFLINE\\n\\nPulsa START CAMERA para iniciar la vista.")
        self.camera_view.setAlignment(Qt.AlignCenter); self.camera_view.setMinimumSize(520,360); self.camera_view.setStyleSheet("background:#01070b;border:1px solid #12556b;")
        cam.add(self.camera_view,1)
        cr=QHBoxLayout(); self.cam_start=QPushButton("START CAMERA"); self.cam_stop=QPushButton("STOP"); self.cam_snap=QPushButton("SNAPSHOT"); cr.addWidget(self.cam_start); cr.addWidget(self.cam_stop); cr.addWidget(self.cam_snap); cam.body.addLayout(cr)
        row.addWidget(cam,2)
        screen=Panel("PERCEPTION MATRIX","VIS-03","READY")
        screen.add(QLabel("CAMERA → FRAME BUFFER → VISION MODEL → JARVIS CORE"))
        self.vision_log=QPlainTextEdit(); self.vision_log.setReadOnly(True); self.vision_log.setPlainText("● Camera preview ready\\n● Snapshot pipeline ready\\n● File/image analysis tools ready\\n○ Vision model depends on a compatible local/cloud provider.")
        screen.add(self.vision_log,1); row.addWidget(screen,1); lay.addLayout(row,1)
        self.camera_timer=QTimer(self); self.camera_timer.timeout.connect(self._camera_tick)
        self.camera_engine=None
        self.cam_start.clicked.connect(self.start_camera); self.cam_stop.clicked.connect(self.stop_camera); self.cam_snap.clicked.connect(self.snapshot_camera)

    def start_camera(self):
        try:
            from plugins.camera.engine import CameraEngine
            self.camera_engine=CameraEngine()
            if self.camera_engine.start(0):
                self.camera_timer.start(33); self.vision_log.append("● CAMERA ONLINE // 30 FPS PREVIEW"); self.brain.set_mode("LISTENING")
            else: self.vision_log.append("ERROR // No se pudo abrir la cámara.")
        except Exception as exc: self.vision_log.append(f"CAMERA ERROR // {exc}")

    def _camera_tick(self):
        if not self.camera_engine: return
        frame=self.camera_engine.read()
        if frame is None: return
        try:
            import cv2
            frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            h,w,ch=frame.shape
            img=QImage(frame.data,w,h,ch*w,QImage.Format_RGB888)
            pix=QPixmap.fromImage(img).scaled(self.camera_view.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            self.camera_view.setPixmap(pix)
        except Exception as exc:
            self.vision_log.append(f"FRAME ERROR // {exc}"); self.stop_camera()

    def snapshot_camera(self):
        if not self.camera_engine: self.vision_log.append("CAMERA OFFLINE"); return
        path=WORKSPACE_DIR/"vision"/f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        saved=self.camera_engine.snapshot(path)
        if saved: self.vision_log.append(f"● SNAPSHOT SAVED // {saved}"); self.append("SYSTEM",f"Snapshot disponible para análisis: {saved}")
        else: self.vision_log.append("ERROR // No se pudo capturar.")

    def stop_camera(self):
        self.camera_timer.stop()
        if self.camera_engine: self.camera_engine.stop()
        self.camera_view.clear(); self.camera_view.setText("CAMERA OFFLINE\\n\\nSTART CAMERA")
        self.vision_log.append("○ CAMERA OFFLINE")

    def _build_settings(self):
        page,lay=self._page("SETTINGS // CONTROL","SET-01")
        box=Panel("LOCAL SAFETY POLICY","SET-02","ENFORCED"); box.add(QLabel("DESTRUCTIVE DELETE: BLOCKED")); box.add(QLabel("SHELL EXECUTION: NOT EXPOSED")); box.add(QLabel("SELF-REPAIR: BACKUP + VALIDATE + ROLLBACK")); box.add(QLabel(f"PROJECT ROOT: {BASE_DIR}")); lay.addWidget(box)
        learn=Panel("AUTONOMOUS LEARNING","SET-03","PERSISTENT")
        self.learning_check=QCheckBox("JARVIS puede hacer preguntas de aprendizaje cuando detecte inactividad")
        self.learning_check.setChecked(bool(self.profile.get("learning",{}).get("proactive_questions",True)))
        learn.add(self.learning_check)
        row=QHBoxLayout(); row.addWidget(QLabel("IDLE BEFORE QUESTION")); self.idle_spin=QSpinBox(); self.idle_spin.setRange(30,1800); self.idle_spin.setValue(int(self.profile.get("learning",{}).get("idle_seconds",120))); self.idle_spin.setSuffix(" s"); row.addWidget(self.idle_spin); row.addStretch(); learn.body.addLayout(row)
        learn.add(QLabel("Las respuestas se guardan en learning.db y las reflexiones en self_training.jsonl. JARVIS adapta su contexto, no modifica automáticamente los pesos de Qwen."))
        save=QPushButton("SAVE LEARNING POLICY"); learn.add(save); save.clicked.connect(self.save_learning_policy); lay.addWidget(learn)
        lay.addStretch()
    def _build_plugins(self):
        page,lay=self._page("PLUGIN MATRIX // EXTENSIONS","PLUG-01")
        pm=get_plugin_manager()
        intro=Panel("PLUGIN FABRIC","PLUG-02","DISCOVERED")
        intro.add(QLabel(f"{pm.count()} módulos detectados. Cada módulo se puede activar, diagnosticar y ampliar sin cambiar el núcleo de JARVIS."))
        intro.add(QLabel("FILE / PDF / OFFICE / CAMERA / VISION / SPEECH / WINDOWS / UNITY / GIT / MEMORY / SELF-REPAIR / SYSTEM / ARCHIVE / OCR / CLIPBOARD"))
        lay.addWidget(intro)
        grid=QGridLayout()
        for i,item in enumerate(pm.list()):
            box=Panel(item.get("name",item["id"]),f"PLUG-{i+3:02d}",item.get("status","UNKNOWN"))
            box.add(QLabel(item.get("description","")))
            box.add(QLabel(f"ID // {item['id']}"))
            grid.addWidget(box,i//4,i%4)
        lay.addLayout(grid,1)
        diag=QPushButton("REFRESH PLUGINS")
        diag.clicked.connect(lambda: (pm.discover(), self.append("SYSTEM",f"PLUGIN MATRIX // {pm.count()} módulos")))
        lay.addWidget(diag)

    def _connect(self):
        for key,b in self.nav_buttons.items(): b.clicked.connect(lambda checked=False,k=key:self.show_page(k))
        self.speaker.speaking_changed.connect(self.brain.set_speaking)
        self.send.clicked.connect(self.send_cmd); self.input.returnPressed.connect(self.send_cmd); self.listen_btn.clicked.connect(self.listen); self.voice_check.toggled.connect(self.set_voice); self.quick_send.clicked.connect(self.quick_send_cmd); self.quick.returnPressed.connect(self.quick_send_cmd); self.quick_listen.clicked.connect(self.listen); self.quick_workspace.clicked.connect(lambda: execute_tool("open_workspace"))
        self.listener.recognized.connect(self.on_voice); self.listener.failed.connect(lambda e:self.append("SYSTEM",f"VOICE ERROR: {e}"))
    def show_page(self,key):
        order=["dashboard","conversation","workspace","tools","system","aicore","memory","personality","voice","vision","settings","plugins"]; idx=order.index(key); self.pages.setCurrentIndex(idx)
        for k,b in self.nav_buttons.items(): b.setChecked(k==key)
    def append(self,who,text):
        if hasattr(self,'stream'): self.stream.add(who,text)
    def _touch_activity(self):
        self.last_activity = time.monotonic()

    def _proactive_tick(self):
        if self.busy or self._proactive_busy or not self.router.proactive_enabled():
            return
        idle_limit = int(self.profile.get("learning",{}).get("idle_seconds",120))
        if time.monotonic() - self.last_activity < idle_limit:
            return
        if self.learning.get_proactive_question():
            self._show_proactive_question(self.learning.get_proactive_question())
            return
        self._proactive_busy=True
        worker=ProactiveWorker(self.router)
        thread=threading.Thread(target=worker.run,daemon=True,name="jarvis-proactive-question")
        worker.done.connect(self._proactive_done)
        self._proactive_worker=worker; self._proactive_thread=thread
        thread.start()

    def _proactive_done(self, question):
        self._proactive_busy=False
        if not question:
            return
        if time.monotonic() - self.last_activity < int(self.profile.get("learning",{}).get("idle_seconds",120)):
            return
        self._show_proactive_question(question)

    def _show_proactive_question(self, question):
        if not question or self.busy:
            return
        self.append("JARVIS", "Tengo una pregunta para aprender a ayudarte mejor:\n" + question)
        self.activity_text.setText("PROACTIVE LEARNING\n" + question + "\n\nMEMORY // PERSISTENT")
        self.brain.set_mode("SPEAKING")
        if self.voice_check.isChecked():
            self.speaker.speak(question)
        self._touch_activity()

    def save_learning_policy(self):
        cfg=self.profile.setdefault("learning",{})
        cfg["proactive_questions"]=bool(self.learning_check.isChecked())
        cfg["idle_seconds"]=int(self.idle_spin.value())
        save_profile(self.profile)
        self.router.update_profile(self.profile)
        self.append("SYSTEM", f"AUTONOMOUS LEARNING // {'ON' if cfg['proactive_questions'] else 'OFF'} // IDLE {cfg['idle_seconds']}s")

    def send_cmd(self):
        text=self.input.text().strip()
        if text and not self.busy: self._touch_activity(); self.input.clear(); self.append("YOU",text); self.run_cmd(text)
    def quick_send_cmd(self):
        text=self.quick.text().strip()
        if text and not self.busy: self._touch_activity(); self.quick.clear(); self.append("YOU",text); self.run_cmd(text)
    def run_cmd(self,text):
        self.busy=True; self.brain.set_mode("THINKING"); self.footer_state.setText("● THINKING");
        idx=self.mode.currentIndex(); deep=True if idx==2 else False if idx==1 else None
        worker=Worker(self.router,text,deep); thread=threading.Thread(target=worker.run,daemon=True); worker.done.connect(self.reply); worker.busy.connect(self.set_busy); worker.mode.connect(self.brain.set_mode); self.worker=worker; self.thread=thread; thread.start()
    def set_busy(self,state): self.busy=state; self.brain.set_mode("EXECUTING" if state else "IDLE")
    def reply(self,text,elapsed):
        self._touch_activity(); self.brain.set_mode("SPEAKING"); self.append("JARVIS",f"{text}\n\n[{elapsed:.1f}s]"); self.activity_text.setText(f"LAST TASK\n{str(text)[:180]}\n\nLATENCY // {elapsed:.2f}s\nLEARNING // {self.router.last_learning_event or 'NONE'}\nMEMORY // PERSISTENT SQLITE"); self.footer_state.setText("● SPEAKING");
        if self.voice_check.isChecked(): self.speaker.speak(text)
        QTimer.singleShot(1200,lambda:self.brain.set_mode("IDLE")); QTimer.singleShot(300,self.telemetry)
    def listen(self):
        self._touch_activity()
        if self.busy:return
        self.brain.set_mode("LISTENING"); self.footer_state.setText("● LISTENING"); self.listener.listen_once()
    def on_voice(self,text): self._touch_activity(); self.append("YOU",text); self.run_cmd(text)
    def set_voice(self,on): self.speaker.enabled=bool(on); self.footer_state.setText("● VOICE ON" if on else "● VOICE OFF")
    def import_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,"IMPORT FILES","", "All files (*.*)")
        for path in paths:
            result=execute_tool("import_file",path=path,destination="imports")
            self.append("SYSTEM",result)
        self.fs.setRootPath(str(WORKSPACE_DIR)); self.tree.setRootIndex(self.fs.index(str(WORKSPACE_DIR)))

    def new_folder(self):
        from PySide6.QtWidgets import QInputDialog
        name,ok=QInputDialog.getText(self,"NEW WORKSPACE FOLDER","Folder name:")
        if ok and name.strip(): self.router.handle(f"crea una carpeta {name.strip()}",deep=False); self.fs.setRootPath(str(WORKSPACE_DIR)); self.tree.setRootIndex(self.fs.index(str(WORKSPACE_DIR)))
    def save_personality(self):
        p=self.profile.setdefault('personality',{}); p.update({'name':self.name.text().strip() or 'JARVIS','tone':self.tone.text().strip(),'style':self.style.toPlainText().strip()}); p.update({k:s.value() for k,s in self.personality_sliders.items()}); save_profile(self.profile); self.router.update_profile(self.profile); self.append("SYSTEM","PERSONALITY MATRIX SAVED + APPLIED")
    def save_voice(self):
        cfg=self.profile.setdefault('voice',{}); cfg.update({'rate':self.rate.value(),'volume':self.volume.value()/100,'voice_id':self.voice_combo.currentData() or ''}); save_profile(self.profile); self.speaker.configure(cfg); self.speaker.speak("Voz de JARVIS configurada."); self.append("SYSTEM","VOICE MATRIX SAVED + APPLIED")
    def apply_model(self):
        if self.model_edit.text().strip(): self.router.provider.set_model(self.model_edit.text().strip()); self.append("SYSTEM",f"MODEL SET // {self.router.provider.model}")
    def telemetry(self):
        self.clock.setText(time.strftime('%H:%M:%S')); stats=self.learning.stats(); self.brain.set_stats(stats)
        for obj,key in [(self.cpu,'cpu'),(self.ram,'ram'),(self.disk,'disk')]: pass
        try:
            import psutil
            cpu=psutil.cpu_percent(interval=None); ram=psutil.virtual_memory(); disk=psutil.disk_usage(os.environ.get('SystemDrive','C:')+'\\').percent
            self.cpu.set_value(f"{cpu:.0f}%"); self.ram.set_value(f"{ram.percent:.0f}%"); self.disk.set_value(f"{disk:.0f}%")
            self.neural.set_value(f"{stats['nodes']} NODES")
            self.mem_nodes.set_value(stats['nodes']); self.mem_edges.set_value(stats['edges']); self.mem_errors.set_value(stats['errors']); self.mem_success.set_value(stats['successes'])
            self.footer_cpu.setText(f"CPU {cpu:.0f}%"); self.footer_ram.setText(f"RAM {ram.percent:.0f}%"); self.footer_tools.setText(f"TOOLS {len(list_tools())}"); self.footer_mem.setText(f"MEM {stats['nodes']}N/{stats['edges']}S // PERSISTENT"); self.footer_repair.setText(f"REPAIR {self.router.repair.last_event}")
            self.nav_diag.setText(f"CORE  ● ONLINE\nTOOLS  {len(list_tools())} READY\nMEMORY {stats['nodes']} NODES\nREPAIR {self.router.repair.last_event}\nDELETE ● BLOCKED")
            self.sysinfo.setPlainText(f"OS: {os.name}\nCPU: {cpu:.0f}%\nRAM: {ram.percent:.0f}% ({ram.used/2**30:.1f}/{ram.total/2**30:.1f} GB)\nDISK: {disk:.0f}%\nMODEL: {self.router.provider.model}\nOLLAMA: {self.router.provider.host}")
            self.runtime.setPlainText(f"PYTHON: {sys.version.split()[0]}\nQT: PySide6\nUI: NEURAL COMMAND DECK\nREASONING: {self.mode.currentText()}\nUPTIME: {time.strftime('%H:%M:%S')}")
            statuses=self.router.ai_manager.statuses()
            for pname, lab in getattr(self, "ai_status_labels", {}).items():
                state=statuses.get(pname, "UNKNOWN")
                symbol="●" if state == "READY" else "○"
                lab.setText(f"{pname.upper():<8}  {symbol} {state}")
            self.services.setPlainText(f"OLLAMA // {statuses.get("Ollama", "UNKNOWN")}\nCHATGPT // {statuses.get("ChatGPT", "UNKNOWN")}\nCLAUDE // {statuses.get("Claude", "UNKNOWN")}\nGEMINI // {statuses.get("Gemini", "UNKNOWN")}\nGROK // {statuses.get("Grok", "UNKNOWN")}\nACTIVE BRAIN // {self.router.ai_manager.last_provider}\nTTS // {'READY' if self.speaker.available else 'OFFLINE'}\nVOICE INPUT // READY\nWORKSPACE // READY\nSELF-REPAIR // {self.router.repair.last_event}\nDELETE // BLOCKED")
            self.diag.setPlainText(f"CORE // ONLINE\nTOOLS // {len(list_tools())}\nLEARNING // {stats['experiences']} EXPERIENCES\nERRORS // {stats['errors']}\nCORRECTIONS // {stats['corrections']}\nREPAIRS // {self.router.repair.last_event}")
            nodes,edges=self.learning.graph(); self.memory_graph.setPlainText("NEURAL GRAPH\n====================\n"+"\n".join(f"{n['node_type'].upper():10} {n['label'][:60]}  HITS={n['hits']} ERR={n['errors']}" for n in nodes[:35]))
            recent=self.learning.recent(16); self.memory_recent.setPlainText("\n\n".join(f"[{('OK' if x['success'] else 'ERROR')}] {x['kind'].upper()}\n{x['task']}\n→ {x['detail']}" for x in recent) or "NO EXPERIENCES")
        except Exception as exc: self.diag.setPlainText(f"TELEMETRY ERROR\n{exc}")


def run_app():
    app=QApplication.instance() or QApplication(sys.argv); w=MainWindow(); w.show(); return app.exec()
