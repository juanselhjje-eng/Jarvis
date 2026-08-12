from __future__ import annotations

import json
import os
import re
import threading
import time


class AutonomousLearning:
    """Motor de aprendizaje continuo y multidominio de JARVIS.

    Aprende conocimiento conductual persistente a partir de experiencias y de las
    IAs disponibles. No modifica pesos de modelos ni escribe código automáticamente.
    El ciclo continúa en segundo plano mientras JARVIS esté encendido.
    """

    TOPIC_DOMAINS = (
        "Windows y sistema operativo",
        "programación y depuración",
        "Python y automatización",
        "web, navegadores y aplicaciones",
        "archivos, documentos y productividad",
        "matemáticas y ciencia",
        "historia, geografía y cultura general",
        "inglés, español y aprendizaje de idiomas",
        "Minecraft, videojuegos y creación de contenido",
        "IA, modelos, prompts y agentes",
        "seguridad informática defensiva y privacidad",
        "multimedia, audio, vídeo e imágenes",
        "redes e internet",
        "bases de datos y organización de información",
        "electrónica y tecnología",
        "estudio, planificación y hábitos de productividad",
        "conocimientos cotidianos y resolución de problemas",
    )

    def __init__(self, learning_engine, ai_manager):
        self.learning = learning_engine
        self.ai = ai_manager
        self._lock = threading.RLock()
        self.last_run = 0.0
        self.last_topic = ""
        self.last_status = "IDLE"
        self.last_teachers: list[str] = []
        self.last_contributions: dict[str, str] = {}
        self._stop = threading.Event()
        self.interval = max(30, int(os.getenv("JARVIS_LEARNING_INTERVAL", "90")))
        self._domain_index = 0
        self._worker = threading.Thread(target=self._continuous_loop, daemon=True, name="JARVIS-CONTINUOUS-LEARNING")
        self._worker.start()

    def _store(self, topic, synthesis, confidence, sources, contributions):
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
        self.learning.record_reflection("autonomous:" + topic, synthesis, synthesis, confidence)
        self.learning.record_knowledge_graph(topic, synthesis, confidence, sources, contributions)
        for provider, contribution in contributions.items():
            self.learning.record(
                f"teacher:{provider}:{topic}", "ai_teaching", str(contribution)[:2200],
                success=True, tool=f"AI::{provider}", error=False,
            )

    def _choose_topic(self):
        domain = self.TOPIC_DOMAINS[self._domain_index % len(self.TOPIC_DOMAINS)]
        self._domain_index += 1
        context = self.learning.adaptive_context(limit=12)
        recent = self.learning.recent(limit=40)
        recent_text = "\n".join(f"{x.get('kind')}: {x.get('task')}" for x in recent[-25:])
        prompt = f"""Selecciona UN microtema nuevo que JARVIS pueda aprender.
Dominio prioritario: {domain}
No te limites al dominio si existe una necesidad evidente en otra área.
JARVIS debe aprender TODO tipo de conocimiento general útil, no solo programación o Windows.
Evita repetir temas recientes y evita secretos o datos personales.

CONOCIMIENTO EXISTENTE:
{context[:5000]}

TEMAS RECIENTES:
{recent_text[:5000]}

Devuelve SOLO JSON válido:
{{"topic":"tema concreto y enseñable","reason":"utilidad"}}"""
        response = self.ai.chat(
            [{"role": "system", "content": "Selector de temas del aprendizaje continuo de JARVIS."},
             {"role": "user", "content": prompt}],
            tools=None, think=True, temperature=0.35, max_tokens=500,
        )
        raw = str(getattr(getattr(response, "message", None), "content", "") or "")
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise RuntimeError("El selector no devolvió JSON válido")
        data = json.loads(match.group(0))
        topic = str(data.get("topic", "")).strip()
        if not topic:
            raise RuntimeError("Tema vacío")
        return topic

    def run_once(self, force: bool = False) -> str:
        with self._lock:
            now = time.time()
            if not force and now - self.last_run < self.interval:
                return ""
            self.last_run = now
            self.last_status = "THINKING // SELECTING TOPIC"

        try:
            context = self.learning.adaptive_context(limit=16)
            topic = self._choose_topic()
            self.last_topic = topic
            self.last_status = f"TEACHING // {topic[:90]}"

            # MultiAIManager consulta en paralelo a todas las IAs configuradas.
            synthesis, confidence, contributions = self.ai.learn_topic(topic, context=context)
            self.last_contributions = dict(contributions or {})
            self.last_teachers = list(self.last_contributions.keys())

            if not synthesis:
                raise RuntimeError("El consejo no produjo conocimiento")

            # No se guarda como conocimiento firme si las IAs no alcanzan suficiente consenso.
            if confidence >= 0.60:
                self._store(topic, synthesis, confidence, self.last_teachers, self.last_contributions)
                self.last_status = (
                    f"LEARNED // {topic[:65]} // TEACHERS={len(self.last_teachers)} // "
                    f"GRAPH+{len(self.last_teachers) + 4}"
                )
                return self.last_status

            self.last_status = f"REVIEW REQUIRED // {topic[:70]} // confidence={confidence:.2f}"
            return self.last_status
        except Exception as exc:
            self.last_status = f"LEARNING ERROR // {exc}"
            return self.last_status

    def _continuous_loop(self):
        # Primera ejecución con retraso para no competir con el arranque de JARVIS.
        self._stop.wait(20)
        while not self._stop.is_set():
            try:
                self.run_once(force=True)
            except Exception as exc:
                self.last_status = f"LEARNING ERROR // {exc}"
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
