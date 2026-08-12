from __future__ import annotations

import math
import os
import sys
import time
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPointF, Signal, QObject
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFrame, QProgressBar, QStackedWidget,
    QSplitter, QFileDialog, QScrollArea, QListWidget, QListWidgetItem, QCheckBox,
    QSpinBox, QComboBox, QFormLayout, QMessageBox
)

from config.settings import BASE_DIR, WORKSPACE_DIR
from config.user_profile import load_profile, save_profile
from core.orchestrator import Orchestrator
from memory.learning import get_learning_engine
from tools.registry import list_tools
from ui.voice import Speaker, Listener

CYAN = "#16e7ff"
ICE = "#d9fbff"
BG = "#02070b"
PANEL = "#06131a"
PANEL2 = "#081b24"
BORDER = "#12556b"
MUTED = "#6c9aaa"
GREEN = "#24efaa"
AMBER = "#ffd166"
RED = "#ff526b"

STYLE = f"""
* {{ font-family: 'Segoe UI'; color:{ICE}; }}
QMainWindow, QWidget {{ background:{BG}; }}
QFrame#top, QFrame#side, QFrame#panel, QFrame#footer {{
    background:{PANEL}; border:1px solid {BORDER}; border-radius:10px;
}}
QFrame#panel2 {{ background:{PANEL2}; border:1px solid #103f50; border-radius:8px; }}
QLabel#brand {{ color:{ICE}; font-size:25px; font-weight:900; letter-spacing:6px; }}
QLabel#pageTitle {{ color:{ICE}; font-size:24px; font-weight:900; letter-spacing:3px; }}
QLabel#section {{ color:{CYAN}; font-size:11px; font-weight:900; letter-spacing:2px; }}
QLabel#muted {{ color:{MUTED}; font-size:10px; }}
QLabel#metric {{ color:{ICE}; font-size:20px; font-weight:800; }}
QLabel#state {{ color:{GREEN}; font-size:11px; font-weight:900; }}
QPushButton {{ background:#071923; border:1px solid #15586b; border-radius:6px; padding:9px 12px; font-weight:800; font-size:10px; }}
QPushButton:hover {{ background:#0b2d3b; border-color:{CYAN}; }}
QPushButton:checked {{ background:#092f3b; border-color:{CYAN}; color:{CYAN}; }}
QPushButton#nav {{ text-align:left; background:transparent; border-color:transparent; padding:12px; }}
QPushButton#nav:hover, QPushButton#nav:checked {{ background:#082a35; border-color:#0d728c; color:{CYAN}; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox {{ background:#030c12; border:1px solid #14495a; border-radius:6px; padding:9px; color:{ICE}; }}
QTextEdit {{ selection-background-color:#0e6175; }}
QProgressBar {{ background:#020a0f; border:1px solid #123d4a; height:7px; border-radius:3px; }}
QProgressBar::chunk {{ background:{CYAN}; border-radius:3px; }}
QListWidget {{ background:#030c12; border:1px solid #14495a; border-radius:6px; padding:4px; }}
QListWidget::item {{ padding:9px; border-bottom:1px solid #0c2934; }}
QListWidget::item:selected {{ background:#0b4656; }}
QCheckBox {{ color:{ICE}; spacing:8px; }}
QScrollArea {{ border:0; }}
"""


def alpha(color: str, value: int) -> QColor:
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(value))))
    return c


class BrainWidget(QWidget):
    """Compact animated holographic neural sphere with safe QColor handling."""
    def __init__(self):
        super().__init__()
        self.mode = "IDLE"
        self.phase = 0.0
        self.stats = {}
        self.speaking = False
        self.setMinimumSize(260, 260)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_mode(self, mode: str):
        self.mode = str(mode or "IDLE").upper()
        self.update()

    def set_speaking(self, value: bool):
        self.speaking = bool(value)
        if value:
            self.mode = "SPEAKING"
        elif self.mode == "SPEAKING":
            self.mode = "IDLE"
        self.update()

    def set_stats(self, stats):
        self.stats = dict(stats or {})
        self.update()

    def _tick(self):
        speed = {"IDLE": .018, "LISTENING": .055, "THINKING": .10, "EXECUTING": .14, "SPEAKING": .18}.get(self.mode, .025)
        self.phase += speed
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            r = self.rect()
            p.fillRect(r, QColor(BG))
            cx = r.center().x()
            cy = r.center().y() - 5
            sphere = min(r.width(), r.height()) * .285
            active = self.mode != "IDLE"
            intensity = 1.0 if self.speaking else .75 if active else .42

            p.setPen(QPen(alpha("#0a2935", 1), 1))
            for x in range(0, r.width(), 22):
                p.drawLine(x, 0, x, r.height())
            for y in range(0, r.height(), 22):
                p.drawLine(0, y, r.width(), y)

            # Outer holographic rings.
            for i in range(7):
                rr = sphere * (1.0 + i * .065)
                p.setPen(QPen(alpha(CYAN, 28 + i * 8), 1 if i else 2))
                p.drawEllipse(QPointF(cx, cy), rr, rr)

            # Rotating longitude bands create depth without a large frame.
            rot = self.phase * .72
            for i in range(9):
                a = rot + i * math.pi / 9
                rx = max(2.0, abs(math.sin(a)) * sphere)
                p.setPen(QPen(alpha(CYAN, 45 if i % 2 else 95), 1))
                p.drawEllipse(QPointF(cx, cy), rx, sphere)

            # Latitude bands.
            for i in range(-4, 5):
                lat = i / 5
                rx = sphere * math.sqrt(max(.08, 1 - lat * lat))
                ry = sphere * math.sqrt(max(.08, 1 - lat * lat)) * .22
                yy = cy + lat * sphere * .72
                p.setPen(QPen(alpha(ICE, 50 if i else 105), 1))
                p.drawEllipse(QPointF(cx, yy), rx, ry)

            # Nodes + synapses.
            nodes = []
            for ring in range(8):
                phi = -math.pi / 2 + (ring + 1) * math.pi / 9
                rr = sphere * math.cos(phi)
                yy = cy + sphere * math.sin(phi)
                count = 9 + ring * 2
                for j in range(count):
                    a = rot * .9 + j * math.tau / count + ring * .23
                    nodes.append(QPointF(cx + rr * math.cos(a), yy + rr * .20 * math.sin(a)))
            p.setPen(QPen(alpha(CYAN, 38), 1))
            for i, a in enumerate(nodes):
                for j in (1, 2, 5):
                    if i + j < len(nodes):
                        b = nodes[i + j]
                        if (a.x() - b.x()) ** 2 + (a.y() - b.y()) ** 2 < (sphere * .42) ** 2:
                            p.drawLine(a, b)
            for i, node in enumerate(nodes):
                wave = (math.sin(self.phase * (8 if active else 3) + i * .37) + 1) / 2
                radius = 1.1 + wave * (3.5 if active else 2.0)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(alpha(ICE, 50 + int(wave * 170 * intensity))))
                p.drawEllipse(node, radius, radius)

            # Core glow.
            pulse = 29 + (13 if self.speaking else 7) * math.sin(self.phase * (8 if active else 4))
            glow = QRadialGradient(QPointF(cx, cy), sphere * .72)
            glow.setColorAt(0, alpha(ICE, 215))
            glow.setColorAt(.16, alpha(CYAN, 150))
            glow.setColorAt(.55, alpha(CYAN, 45))
            glow.setColorAt(1, alpha(CYAN, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(cx, cy), sphere * .72, sphere * .72)
            p.setBrush(QBrush(alpha("#03131b", 245)))
            p.setPen(QPen(alpha(ICE, 230), 2))
            p.drawEllipse(QPointF(cx, cy), pulse, pulse)
            p.setPen(QPen(alpha(CYAN, 230), 2))
            p.drawEllipse(QPointF(cx, cy), pulse * .63, pulse * .63)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(alpha(CYAN, 145)))
            p.drawEllipse(QPointF(cx, cy), pulse * .25, pulse * .25)

            # Rotating arcs.
            for j in range(3):
                rr = sphere * (1.10 + j * .07)
                p.setPen(QPen(alpha(CYAN, 110 - j * 25), 2))
                p.drawArc(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2), int((self.phase * 95 + j * 70) % 360) * 16, 165 * 16)

            # Voice waveform at bottom.
            base_y = r.height() - 24
            amp = 12 if self.speaking else 7 if self.mode == "IDLE" else 17
            p.setPen(QPen(alpha(CYAN, 180), 1.5))
            prev = None
            for x in range(20, r.width() - 20, 4):
                y = base_y + math.sin(x * .055 + self.phase * 10) * amp
                pt = QPointF(x, y)
                if prev:
                    p.drawLine(prev, pt)
                prev = pt

            p.setPen(QPen(alpha(MUTED, 220), 1))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(18, 18, "NEURAL CORE // 3D")
            p.drawText(18, r.height() - 6, f"NODES {self.stats.get('nodes', 0)}  SYN {self.stats.get('edges', 0)}  ERR {self.stats.get('errors', 0)}")
            p.drawText(r.width() - 112, 18, self.mode)
        finally:
            p.end()


class Worker(QObject):
    done = Signal(str, float)
    failed = Signal(str)

    def __init__(self, router, text, deep):
        super().__init__()
        self.router = router
        self.text = text
        self.deep = deep

    def run(self):
        started = time.perf_counter()
        try:
            self.done.emit(str(self.router.handle(self.text, deep=self.deep)), time.perf_counter() - started)
        except Exception as exc:
            self.failed.emit(str(exc))


class ModernWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S // NEURAL COMMAND DECK")
        self.resize(1550, 930)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(STYLE)
        self.profile = load_profile()
        self.router = Orchestrator()
        self.learning = get_learning_engine()
        self.speaker = Speaker()
        self.listener = Listener()
        self.speaker.configure(self.profile.get("voice", {}))
        self.busy = False
        self.last_user_activity = time.monotonic()
        self._build()
        self._wire()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.telemetry)
        self._timer.start(1000)
        self._learn_timer = QTimer(self)
        self._learn_timer.timeout.connect(self._autonomous_learning_tick)
        self._learn_timer.start(45000)
        QTimer.singleShot(5000, self._autonomous_learning_tick)
        self.telemetry()
        self.log("SYSTEM", "NÚCLEO JARVIS ONLINE // MEMORIA PERSISTENTE // CONSEJO MULTI-IA ARMADO")

    def panel(self, title, subtitle=""):
        f = QFrame(); f.setObjectName("panel")
        lay = QVBoxLayout(f); lay.setContentsMargins(14, 12, 14, 14); lay.setSpacing(9)
        head = QHBoxLayout(); lab = QLabel(title.upper()); lab.setObjectName("section"); head.addWidget(lab)
        if subtitle:
            sub = QLabel(subtitle.upper()); sub.setObjectName("muted"); head.addWidget(sub)
        head.addStretch(); lay.addLayout(head)
        return f, lay

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(9, 9, 9, 7); outer.setSpacing(7)

        top = QFrame(); top.setObjectName("top"); tl = QHBoxLayout(top); tl.setContentsMargins(15, 8, 15, 8)
        brand = QLabel("J.A.R.V.I.S"); brand.setObjectName("brand"); tl.addWidget(brand)
        tag = QLabel("NEURAL COMMAND DECK // V26"); tag.setObjectName("section"); tl.addWidget(tag); tl.addStretch()
        self.ai_state = QLabel("● COUNCIL READY"); self.ai_state.setObjectName("state"); tl.addWidget(self.ai_state)
        self.clock = QLabel("00:00:00"); self.clock.setObjectName("metric"); tl.addWidget(self.clock)
        outer.addWidget(top)

        split = QSplitter(Qt.Horizontal); split.setHandleWidth(4); outer.addWidget(split, 1)
        side = QFrame(); side.setObjectName("side"); sv = QVBoxLayout(side); sv.setContentsMargins(9, 12, 9, 9); sv.setSpacing(3)
        nav_title = QLabel("CONTROL MATRIX"); nav_title.setObjectName("section"); sv.addWidget(nav_title)
        self.nav = {}
        labels = [
            ("dashboard", "◆  COMMAND DECK"), ("conversation", "◈  CONVERSACIÓN"),
            ("workspace", "▣  WORKSPACE"), ("tools", "⚒  TOOLS"), ("council", "◇  CONSEJO IA"),
            ("memory", "◎  MEMORIA NEURAL"), ("voice", "♫  VOZ"), ("vision", "◌  VISIÓN"),
            ("settings", "⚙  CONFIGURACIÓN"),
        ]
        for key, text in labels:
            b = QPushButton(text); b.setObjectName("nav"); b.setCheckable(True); b.clicked.connect(lambda checked, k=key: self.show_page(k)); self.nav[key] = b; sv.addWidget(b)
        sv.addStretch()
        self.side_diag = QLabel("CORE ●\nMEMORY --\nNODES --\nCOUNCIL --\nREPAIR --\nDELETE BLOCKED"); self.side_diag.setObjectName("muted"); sv.addWidget(self.side_diag)
        split.addWidget(side)

        self.pages = QStackedWidget(); split.addWidget(self.pages); split.setSizes([215, 1335])
        self._dashboard(); self._conversation(); self._workspace(); self._tools(); self._council(); self._memory(); self._voice(); self._vision(); self._settings()

        foot = QFrame(); foot.setObjectName("footer"); fl = QHBoxLayout(foot); fl.setContentsMargins(10, 5, 10, 5)
        self.footer = QLabel("● READY"); self.footer.setObjectName("state"); fl.addWidget(self.footer)
        self.footer_mem = QLabel("MEMORY --"); fl.addWidget(self.footer_mem); self.footer_ai = QLabel("AI --"); fl.addWidget(self.footer_ai)
        fl.addStretch(); fl.addWidget(QLabel("LOCAL CONTROL // DELETE OPERATIONS BLOCKED")); outer.addWidget(foot)

        self.show_page("dashboard")

    def page(self, title, code):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(10)
        h = QHBoxLayout(); t = QLabel(title); t.setObjectName("pageTitle"); h.addWidget(t); h.addStretch(); c = QLabel(code); c.setObjectName("muted"); h.addWidget(c); lay.addLayout(h)
        self.pages.addWidget(w); return w, lay

    def _dashboard(self):
        page, lay = self.page("COMMAND DECK", "DECK-26")
        cards = QGridLayout(); cards.setSpacing(8)
        self.metrics = {}
        for i, key in enumerate(("CPU", "RAM", "DISK", "NODES")):
            f, v = self.panel(key + " TELEMETRY", "LIVE"); lab = QLabel("--"); lab.setObjectName("metric"); v.addWidget(lab)
            if key != "NODES":
                bar = QProgressBar(); bar.setRange(0, 100); bar.setTextVisible(False); v.addWidget(bar); self.metrics[key] = (lab, bar)
            else:
                self.metrics[key] = (lab, None)
            cards.addWidget(f, 0, i)
        lay.addLayout(cards)

        mid = QSplitter(Qt.Horizontal); mid.setHandleWidth(4)
        brain_panel, bp = self.panel("NEURAL CORE", "LIVE 3D CORTEX"); self.brain = BrainWidget(); bp.addWidget(self.brain, 1); mid.addWidget(brain_panel)
        info, il = self.panel("MISSION STATUS", "LIVE")
        self.activity = QLabel("JARVIS está listo.\n\nLas IAs disponibles alimentan el aprendizaje autónomo en segundo plano."); self.activity.setWordWrap(True); self.activity.setObjectName("muted"); il.addWidget(self.activity)
        self.council_list = QListWidget(); il.addWidget(self.council_list, 1)
        mid.addWidget(info); mid.setSizes([850, 420]); lay.addWidget(mid, 1)

        bottom, bl = self.panel("MISSION CONSOLE", "NATURAL LANGUAGE")
        row = QHBoxLayout(); self.quick = QLineEdit(); self.quick.setPlaceholderText("Escribe una orden, pregunta o tarea para JARVIS..."); row.addWidget(self.quick, 1)
        self.send = QPushButton("EXECUTE"); self.listen_btn = QPushButton("MIC / LISTEN"); row.addWidget(self.send); row.addWidget(self.listen_btn); bl.addLayout(row); lay.addWidget(bottom)

    def _conversation(self):
        page, lay = self.page("CONVERSACIÓN", "CHAT-26")
        self.chat = QTextEdit(); self.chat.setReadOnly(True); lay.addWidget(self.chat, 1)
        row = QHBoxLayout(); self.input = QLineEdit(); self.input.setPlaceholderText("Habla con JARVIS... Mantendrá el contexto de la tarea pendiente."); row.addWidget(self.input, 1)
        self.send2 = QPushButton("ENVIAR"); row.addWidget(self.send2); lay.addLayout(row)
        self.voice_reply = QCheckBox("JARVIS HABLA EN VOZ ALTA"); self.voice_reply.setChecked(True); lay.addWidget(self.voice_reply)

    def _workspace(self):
        page, lay = self.page("WORKSPACE", "FILES-26")
        top = QHBoxLayout(); imp = QPushButton("IMPORTAR ARCHIVOS"); openw = QPushButton("ABRIR WORKSPACE"); top.addWidget(imp); top.addWidget(openw); top.addStretch(); lay.addLayout(top)
        self.files = QListWidget(); lay.addWidget(self.files, 1); self._refresh_files()
        imp.clicked.connect(self.import_files); openw.clicked.connect(lambda: os.startfile(str(WORKSPACE_DIR)) if os.name == "nt" else None)

    def _tools(self):
        page, lay = self.page("TOOLS", "TOOL-MATRIX-26")
        f, fl = self.panel("AVAILABLE CAPABILITIES", "READ ONLY")
        self.tools_list = QListWidget(); fl.addWidget(self.tools_list, 1)
        try:
            tools = list_tools()
            for item in tools:
                name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else str(item))
                self.tools_list.addItem(str(name))
        except Exception as exc:
            self.tools_list.addItem("TOOL REGISTRY ERROR: " + str(exc))
        lay.addWidget(f, 1)
        note, nl = self.panel("HOW JARVIS USES TOOLS", "SAFE EXECUTION")
        txt = QLabel("JARVIS selecciona herramientas desde el orquestador. Las operaciones destructivas de borrado permanecen bloqueadas. Si una herramienta falla, el error entra en memoria y el motor de recuperación busca otra ruta.")
        txt.setWordWrap(True); txt.setObjectName("muted"); nl.addWidget(txt); lay.addWidget(note)

    def _council(self):
        page, lay = self.page("CONSEJO MULTI-IA", "AI-COUNCIL-26")
        status, sl = self.panel("PROVEEDORES", "LIVE")
        self.provider_labels = {}
        for name in ("Ollama", "ChatGPT", "Claude", "Gemini", "Grok"):
            lab = QLabel(name.upper() + " // CHECKING"); lab.setObjectName("muted"); self.provider_labels[name] = lab; sl.addWidget(lab)
        lay.addWidget(status)
        dossier, dl = self.panel("APRENDIZAJE AUTÓNOMO", "MULTI-TEACHER")
        self.learn_status = QLabel("Esperando el siguiente ciclo de aprendizaje..."); self.learn_status.setWordWrap(True); self.learn_status.setObjectName("muted"); dl.addWidget(self.learn_status)
        self.learn_topic = QLabel("TEMA: --"); self.learn_topic.setWordWrap(True); dl.addWidget(self.learn_topic)
        lay.addWidget(dossier)
        self.council_log = QTextEdit(); self.council_log.setReadOnly(True); lay.addWidget(self.council_log, 1)

    def _memory(self):
        page, lay = self.page("MEMORIA NEURAL", "MEM-26")
        cards = QGridLayout(); self.mem_labels = {}
        for i, key in enumerate(("experiences", "nodes", "edges", "errors", "successes", "corrections")):
            f, fl = self.panel(key.upper(), "PERSISTENT"); lab = QLabel("0"); lab.setObjectName("metric"); fl.addWidget(lab); self.mem_labels[key] = lab; cards.addWidget(f, 0, i)
        lay.addLayout(cards)
        self.memory_text = QTextEdit(); self.memory_text.setReadOnly(True); lay.addWidget(self.memory_text, 1)

    def _voice(self):
        page, lay = self.page("VOICE MATRIX", "VOICE-26")
        f, fl = self.panel("VOICE OUTPUT", "PYTTSX3")
        self.voice_toggle = QCheckBox("VOICE ENABLED"); self.voice_toggle.setChecked(True); fl.addWidget(self.voice_toggle)
        self.voice_test = QPushButton("PROBAR VOZ"); fl.addWidget(self.voice_test); lay.addWidget(f)
        g, gl = self.panel("VOICE INPUT", "SPEECH RECOGNITION")
        gl.addWidget(QLabel("El micrófono usa reconocimiento de voz en español (es-CO) cuando speech_recognition y el micrófono están disponibles."))
        lay.addWidget(g)

    def _vision(self):
        page, lay = self.page("VISIÓN", "VISION-26")
        f, fl = self.panel("CAMERA / PERCEPTION", "SAFE")
        b = QPushButton("ABRIR CÁMARA / CAPTURA"); fl.addWidget(b); b.clicked.connect(lambda: self.submit("abre la cámara y toma una captura"))
        info = QLabel("La captura se procesa mediante las herramientas de visión disponibles. JARVIS no afirma ver contenido que el proveedor no haya entregado."); info.setWordWrap(True); info.setObjectName("muted"); fl.addWidget(info); lay.addWidget(f)

    def _settings(self):
        page, lay = self.page("CONFIGURACIÓN", "SYS-26")
        f, fl = self.panel("LEARNING POLICY", "PERSISTENT")
        self.proactive = QCheckBox("APRENDIZAJE AUTÓNOMO"); self.proactive.setChecked(bool(self.profile.get("learning", {}).get("proactive_questions", True))); fl.addWidget(self.proactive)
        row = QHBoxLayout(); row.addWidget(QLabel("Idle para preguntar (s):")); self.idle = QSpinBox(); self.idle.setRange(30, 3600); self.idle.setValue(int(self.profile.get("learning", {}).get("idle_seconds", 120))); row.addWidget(self.idle); save = QPushButton("GUARDAR"); row.addWidget(save); fl.addLayout(row); save.clicked.connect(self.save_settings)
        lay.addWidget(f)
        about, al = self.panel("SYSTEM CONTRACT", "SAFE LOCAL CONTROL")
        txt = QLabel("JARVIS puede crear, leer, editar, copiar, mover y organizar. Las eliminaciones destructivas permanecen bloqueadas. El aprendizaje persistente guarda experiencias, correcciones, recuperaciones y conocimiento del consejo en SQLite."); txt.setWordWrap(True); txt.setObjectName("muted"); al.addWidget(txt); lay.addWidget(about)

    def _wire(self):
        self.send.clicked.connect(lambda: self.submit(self.quick.text()))
        self.quick.returnPressed.connect(lambda: self.submit(self.quick.text()))
        self.send2.clicked.connect(lambda: self.submit(self.input.text()))
        self.input.returnPressed.connect(lambda: self.submit(self.input.text()))
        self.listen_btn.clicked.connect(self.listen)
        self.voice_toggle.stateChanged.connect(lambda s: setattr(self.speaker, "enabled", bool(s)))
        self.voice_test.clicked.connect(lambda: self.speaker.speak("JARVIS está operativo y la matriz de voz funciona correctamente."))
        self.listener.recognized.connect(self._voice_result)
        self.listener.failed.connect(lambda e: self.log("SYSTEM", "MICRÓFONO: " + e))
        self.speaker.speaking_changed.connect(self.brain.set_speaking)

    def show_page(self, key):
        keys = list(self.nav.keys())
        if key not in keys: return
        self.pages.setCurrentIndex(keys.index(key))
        for k, b in self.nav.items(): b.setChecked(k == key)

    def log(self, who, text):
        stamp = time.strftime("%H:%M:%S")
        color = CYAN if who == "JARVIS" else ICE if who == "YOU" else AMBER
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.chat.append(f'<span style="color:{MUTED}">[{stamp}]</span> <b style="color:{color}">{who}</b><br>{safe}<br>')
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _touch(self):
        self.last_user_activity = time.monotonic()

    def submit(self, text):
        text = str(text or "").strip()
        if not text or self.busy: return
        self._touch()
        self.quick.clear(); self.input.clear(); self.log("YOU", text)
        self.busy = True; self.brain.set_mode("THINKING"); self.footer.setText("● THINKING")
        worker = Worker(self.router, text, None)
        worker.done.connect(self.reply)
        worker.failed.connect(self.failed)
        threading.Thread(target=worker.run, daemon=True, name="jarvis-ui-worker").start()

    def reply(self, text, elapsed):
        self.busy = False; self._touch(); self.brain.set_mode("SPEAKING")
        self.log("JARVIS", f"{text}\n\n[{elapsed:.1f}s]")
        self.activity.setText(f"ÚLTIMA TAREA\n{text[:500]}\n\nLATENCIA {elapsed:.2f}s\nAPRENDIZAJE {self.router.last_learning_event or 'EN ESPERA'}")
        self.footer.setText("● SPEAKING")
        if self.voice_reply.isChecked() if hasattr(self, "voice_reply") else True:
            self.speaker.speak(text)
        QTimer.singleShot(1600, lambda: self.brain.set_mode("IDLE") if not self.speaker._queue.qsize() else None)
        self.telemetry()

    def failed(self, error):
        self.busy = False; self.brain.set_mode("IDLE"); self.footer.setText("● ERROR")
        self.log("SYSTEM", "ERROR DE EJECUCIÓN: " + error)

    def listen(self):
        if self.busy: return
        self._touch(); self.brain.set_mode("LISTENING"); self.footer.setText("● LISTENING")
        self.listener.listen_once()

    def _voice_result(self, text):
        self.brain.set_mode("IDLE"); self.submit(text)

    def import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "IMPORTAR ARCHIVOS")
        if not paths: return
        from tools.registry import execute_tool
        for path in paths:
            try: self.log("SYSTEM", execute_tool("import_file", path=path, destination="imports"))
            except Exception as exc: self.log("SYSTEM", str(exc))
        self._refresh_files()

    def _refresh_files(self):
        self.files.clear()
        try:
            for p in sorted(WORKSPACE_DIR.rglob("*")):
                if p.is_file(): self.files.addItem(str(p.relative_to(WORKSPACE_DIR)))
        except Exception: pass

    def save_settings(self):
        cfg = self.profile.setdefault("learning", {})
        cfg["proactive_questions"] = self.proactive.isChecked()
        cfg["idle_seconds"] = self.idle.value()
        save_profile(self.profile); self.router.update_profile(self.profile)
        self.log("SYSTEM", "POLÍTICA DE APRENDIZAJE GUARDADA")

    def _autonomous_learning_tick(self):
        if not self.proactive.isChecked() or self.busy: return
        if time.monotonic() - self.last_user_activity < 45: return
        self.router.autonomous_learning_async()
        self.learn_status.setText("EL CONSEJO ESTÁ TRABAJANDO: selecciona un tema, consulta las IAs, compara aportes y guarda conocimiento verificado.")
        self.activity.setText("AUTONOMOUS LEARNING // MULTI-IA\nLas IAs están enseñando al grafo persistente de JARVIS...")
        self.council_log.append("[LEARNING] ciclo iniciado")

    def telemetry(self):
        self.clock.setText(time.strftime("%H:%M:%S"))
        try:
            import psutil
            cpu = psutil.cpu_percent(None); ram = psutil.virtual_memory(); disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\").percent
            stats = self.learning.stats(); self.brain.set_stats(stats)
            for key, value in (("CPU", cpu), ("RAM", ram.percent), ("DISK", disk)):
                lab, bar = self.metrics[key]; lab.setText(f"{value:.0f}%"); bar.setValue(int(value))
            self.metrics["NODES"][0].setText(str(stats["nodes"]) + " NODES")
            for k, lab in self.mem_labels.items(): lab.setText(str(stats.get(k, 0)))
            self.memory_text.setPlainText("\n\n".join(f"[{x['kind'].upper()}] {x['task']}\n→ {x['detail']}" for x in self.learning.recent(20)) or "SIN EXPERIENCIAS")
            statuses = self.router.ai_manager.statuses()
            for name, lab in self.provider_labels.items(): lab.setText(f"{name.upper()} // {statuses.get(name, 'UNKNOWN')}")
            available = self.router.ai_manager.available()
            self.ai_state.setText("● COUNCIL " + ("READY" if len(available) >= 2 else "LIMITED"))
            self.footer_mem.setText(f"MEMORY {stats['nodes']}N/{stats['edges']}S")
            self.footer_ai.setText("AI " + ", ".join(available))
            self.side_diag.setText(f"CORE ● ONLINE\nMEMORY {stats['nodes']} NODES\nSYNAPSES {stats['edges']}\nCOUNCIL {len(available)} BRAINS\nREPAIR {self.router.repair.last_event}\nDELETE BLOCKED")
            self.council_list.clear()
            for name in available: self.council_list.addItem("● " + name + " // READY")
            self.council_list.addItem("● Persistent graph // ACTIVE")
            self.council_list.addItem("● Self-reflection // ACTIVE")
            self.council_list.addItem("● Recovery learning // ACTIVE")
        except Exception as exc:
            self.activity.setText("TELEMETRY ERROR\n" + str(exc))


def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModernWindow(); window.show()
    return app.exec()
