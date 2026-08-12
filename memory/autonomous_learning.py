from __future__ import annotations
import json
import re
import sqlite3
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / 'memory' / 'learning.db'

class AutonomousLearning:
    """Autonomous, non-destructive knowledge acquisition.

    It asks the available JARVIS council to choose a useful topic, answer it,
    cross-check the answers and store a compact verified lesson. It does not
    change model weights and never modifies source files.
    """
    def __init__(self, learning_engine, ai_manager):
        self.learning = learning_engine
        self.ai = ai_manager
        self._lock = threading.RLock()
        self.last_run = 0.0
        self.last_topic = ''
        self.last_status = 'IDLE'

    def _store(self, topic: str, synthesis: str, confidence: float, sources: list[str]):
        topic = str(topic).strip()[:700]
        synthesis = str(synthesis).strip()[:2500]
        if not topic or not synthesis:
            return
        detail = (
            f'TEMA: {topic} | CONOCIMIENTO: {synthesis} | '
            f'CONFIDENCE={max(0,min(1,float(confidence))):.2f} | '
            f'FUENTES={", ".join(sources)}'
        )
        self.learning.record('autonomous:' + topic, 'autonomous_learning', detail, success=True)
        # Also feed the existing training corpus without pretending to retrain weights.
        self.learning.record_reflection('autonomous:' + topic, synthesis, synthesis, confidence)

    def run_once(self, force: bool = False) -> str:
        with self._lock:
            now = time.time()
            if not force and now - self.last_run < 90:
                return ''
            self.last_run = now
            self.last_status = 'THINKING'

        try:
            context = self.learning.adaptive_context(limit=12)
            recent = self.learning.recent_proactive_questions(limit=20)
            prompt = f"""Elige UN tema pequeño y útil que JARVIS pueda aprender de forma autónoma.
No preguntes al usuario. Debe ser una capacidad práctica para Windows, programación,
razonamiento, uso de herramientas, archivos, automatización, IA, depuración o mejora
segura del propio asistente.

CONOCIMIENTO YA APRENDIDO:
{context[:5000]}

TEMAS/PREGUNTAS RECIENTES:
{recent[:20]}

Devuelve JSON válido solamente: {{"topic":"pregunta concreta","reason":"por qué es útil"}}
No repitas un tema reciente y no solicites secretos ni datos personales."""
            r = self.ai.chat([{'role':'system','content':'Eres el selector de temas del aprendizaje autónomo de JARVIS.'},
                              {'role':'user','content':prompt}], tools=None, think=True,
                             temperature=0.25, max_tokens=700)
            raw = str(getattr(getattr(r,'message',None),'content','') or '')
            m = re.search(r'\{.*\}', raw, re.S)
            if not m:
                raise RuntimeError('El selector no devolvió JSON.')
            data = json.loads(m.group(0))
            topic = str(data.get('topic','')).strip()
            if not topic:
                raise RuntimeError('Tema vacío.')
            self.last_topic = topic

            # Todas las IAs disponibles enseñan de forma independiente y luego un
            # coordinador consolida la lección. Cada aporte se convierte en nodos y
            # conexiones del grafo de conocimiento persistente de JARVIS.
            synthesis, confidence, contributions = self.ai.learn_topic(topic, context=context)
            if not synthesis:
                raise RuntimeError('El consejo no produjo conocimiento.')
            if confidence >= 0.60:
                sources = list(contributions.keys())
                self._store(topic, synthesis, confidence, sources)
                self.learning.record_knowledge_graph(topic, synthesis, confidence, sources, contributions)
                self.last_status = f'LEARNED // {topic[:70]} // NODES+{len(contributions)+2}'
                return self.last_status
            self.last_status = f'REJECTED LOW CONFIDENCE // {topic[:70]}'
            return self.last_status
        except Exception as exc:
            self.last_status = f'LEARNING ERROR // {exc}'
            return self.last_status
