from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "memory" / "learning.db"


class AutonomousLearning:
    """Continuous multi-IA teacher for JARVIS.

    This is persistent behavioral/knowledge learning, not fake weight training.
    Every available provider gets an independent teaching turn. Their contributions
    are stored as source-specific nodes, then a lead provider consolidates them.
    Nothing is written to source code automatically.
    """

    def __init__(self, learning_engine, ai_manager):
        self.learning = learning_engine
        self.ai = ai_manager
        self._lock = threading.RLock()
        self.last_run = 0.0
        self.last_topic = ""
        self.last_status = "IDLE"
        self.last_teachers: list[str] = []
        self.last_contributions: dict[str, str] = {}

    def _store(self, topic: str, synthesis: str, confidence: float, sources: list[str], contributions: dict[str, str]):
        topic = str(topic).strip()[:700]
        synthesis = str(synthesis).strip()[:2500]
        if not topic or not synthesis:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        detail = (
            f"TEMA: {topic} | CONOCIMIENTO: {synthesis} | "
            f"CONFIDENCE={confidence:.2f} | FUENTES={', '.join(sources)}"
        )
        self.learning.record("autonomous:" + topic, "autonomous_learning", detail, success=True)

        # Store the consolidated lesson as durable adaptive knowledge.
        self.learning.record_reflection("autonomous:" + topic, synthesis, synthesis, confidence)
        self.learning.record_knowledge_graph(
            topic, synthesis, confidence, sources, contributions
        )

        # Also preserve each teacher's verified contribution as its own experience.
        # This makes the UI graph show who taught what instead of only one final blob.
        for provider, contribution in contributions.items():
            self.learning.record(
                f"teacher:{provider}:{topic}",
                "ai_teaching",
                str(contribution)[:2200],
                success=True,
                tool=f"AI::{provider}",
                error=False,
            )

    def run_once(self, force: bool = False) -> str:
        with self._lock:
            now = time.time()
            # Prevent runaway API calls while still allowing continuous background learning.
            if not force and now - self.last_run < 45:
                return ""
            self.last_run = now
            self.last_status = "THINKING // SELECTING TOPIC"

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
            r = self.ai.chat(
                [{"role": "system", "content": "Eres el selector de temas del aprendizaje autónomo de JARVIS."},
                 {"role": "user", "content": prompt}],
                tools=None, think=True, temperature=0.25, max_tokens=700,
            )
            raw = str(getattr(getattr(r, "message", None), "content", "") or "")
            m = re.search(r"\{.*\}", raw, re.S)
            if not m:
                raise RuntimeError("El selector no devolvió JSON.")
            data = json.loads(m.group(0))
            topic = str(data.get("topic", "")).strip()
            if not topic:
                raise RuntimeError("Tema vacío.")
            self.last_topic = topic
            self.last_status = f"TEACHING // {topic[:90]}"

            # Every available brain teaches independently. MultiAIManager.learn_topic
            # uses parallel calls, then a lead model compares the contributions.
            synthesis, confidence, contributions = self.ai.learn_topic(topic, context=context)
            self.last_contributions = dict(contributions or {})
            self.last_teachers = list(self.last_contributions.keys())
            if not synthesis:
                raise RuntimeError("El consejo no produjo conocimiento.")

            if confidence >= 0.60:
                self._store(topic, synthesis, confidence, self.last_teachers, self.last_contributions)
                self.last_status = (
                    f"LEARNED // {topic[:65]} // "
                    f"TEACHERS={len(self.last_teachers)} // GRAPH+{len(self.last_teachers) + 4}"
                )
                return self.last_status

            self.last_status = f"REJECTED LOW CONFIDENCE // {topic[:70]} // NO KNOWLEDGE SAVED"
            return self.last_status
        except Exception as exc:
            self.last_status = f"LEARNING ERROR // {exc}"
            return self.last_status
