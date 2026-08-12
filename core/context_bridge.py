from __future__ import annotations

"""Conversation continuity patch for JARVIS.

Keeps short follow-up answers attached to the task/question that produced them.
It does not replace the LLM's reasoning; it supplies explicit conversational state
so replies such as "en el escritorio", "el segundo", "sí" or "ese" are not treated
as unrelated new conversations.
"""

import re
import threading
import weakref
from dataclasses import dataclass


@dataclass
class PendingContext:
    question: str
    assistant_message: str
    created_at: float


_states: "weakref.WeakKeyDictionary[object, PendingContext]" = weakref.WeakKeyDictionary()
_lock = threading.RLock()
_installed = False


def _looks_like_question(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    low = value.lower()
    if "?" in value or "¿" in value:
        return True
    return bool(re.search(r"\b(dónde|donde|cuál|cual|qué|que|cómo|como|cuándo|cuando|quieres|quieres que|prefieres|elige|indica)\b", low))


def _is_short_followup(text: str) -> bool:
    value = str(text or "").strip().lower()
    if not value or len(value) > 180:
        return False
    if value in {"hola", "buenas", "gracias", "cancelar", "cancela", "salir", "adiós", "adios"}:
        return False
    # Common elliptical answers/references that depend strongly on prior context.
    markers = (
        "sí", "si", "no", "ahí", "ahi", "ese", "esa", "eso", "este", "esta",
        "el primero", "el segundo", "el tercero", "la primera", "la segunda",
        "en el escritorio", "en documentos", "en descargas", "en mi pc",
        "en la carpeta", "en esa carpeta", "allí", "alli", "aquí", "aqui",
        "en windows", "en chrome", "en edge", "en google drive",
    )
    return any(value == marker or value.startswith(marker + " ") for marker in markers)


def install() -> None:
    global _installed
    if _installed:
        return

    # Import here so app.py can install the bridge before MainWindow constructs
    # its Orchestrator instance.
    from core.orchestrator import Orchestrator

    original_handle = Orchestrator.handle
    if getattr(original_handle, "_jarvis_context_bridge", False):
        _installed = True
        return

    def handle_with_context(self, text: str, deep=None):
        user_text = str(text or "").strip()
        pending = _states.get(self)
        injected = False

        if pending and _is_short_followup(user_text):
            context_note = (
                "CONTINUIDAD DE CONVERSACIÓN — RESPUESTA A UNA PREGUNTA PENDIENTE:\n"
                f"JARVIS preguntó: {pending.question}\n"
                f"Contexto de la respuesta anterior: {pending.assistant_message[-1800:]}\n"
                f"El usuario acaba de responder: {user_text}\n\n"
                "INTERPRETACIÓN OBLIGATORIA:\n"
                "Trata este mensaje como respuesta a la pregunta/tarea pendiente. "
                "No cambies de tema ni inicies una tarea independiente. Si la respuesta "
                "completa un parámetro (ruta, nombre, opción, archivo, etc.), continúa la "
                "acción usando las herramientas reales y verifica el resultado."
            )
            try:
                self.history.insert(1, {"role": "system", "content": context_note})
                injected = True
            except Exception:
                injected = False

        try:
            result = original_handle(self, text, deep=deep)
        finally:
            if injected:
                try:
                    # Remove only the bridge message; preserve the real conversation.
                    for i in range(1, min(4, len(self.history))):
                        item = self.history[i]
                        if item.get("role") == "system" and str(item.get("content", "")).startswith("CONTINUIDAD DE CONVERSACIÓN"):
                            self.history.pop(i)
                            break
                except Exception:
                    pass

        answer = str(result or "").strip()
        if _looks_like_question(answer):
            with _lock:
                _states[self] = PendingContext(
                    question=answer[:700],
                    assistant_message=answer[:2200],
                    created_at=__import__("time").time(),
                )
        elif pending and _is_short_followup(user_text):
            # The follow-up was consumed unless JARVIS immediately asked another question.
            with _lock:
                _states.pop(self, None)
        return result

    handle_with_context._jarvis_context_bridge = True
    Orchestrator.handle = handle_with_context
    _installed = True
