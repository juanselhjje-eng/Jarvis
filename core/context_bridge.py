from __future__ import annotations

"""Conversation continuity, capability awareness and agent-policy bridge."""

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
    return bool(re.search(r"\b(dónde|donde|cuál|cual|qué|que|cómo|como|cuándo|cuando|quieres|prefieres|elige|indica)\b", low))


def _is_short_followup(text: str) -> bool:
    value = str(text or "").strip().lower()
    if not value or len(value) > 180:
        return False
    if value in {"hola", "buenas", "gracias", "cancelar", "cancela", "salir", "adiós", "adios"}:
        return False
    markers = (
        "sí", "si", "no", "ahí", "ahi", "ese", "esa", "eso", "este", "esta",
        "el primero", "el segundo", "el tercero", "la primera", "la segunda",
        "en el escritorio", "en documentos", "en descargas", "en mi pc",
        "en la carpeta", "en esa carpeta", "allí", "alli", "aquí", "aqui",
        "en windows", "en chrome", "en edge", "en google drive",
    )
    return any(value == marker or value.startswith(marker + " ") for marker in markers)


def _capability_context() -> str:
    try:
        from plugins.registry import capability_registry
        return capability_registry.prompt_summary()
    except Exception:
        return "CAPACIDADES DISPONIBLES: usa las herramientas registradas en el orquestador."


def install() -> None:
    global _installed
    if _installed:
        return

    from core.orchestrator import Orchestrator
    from core.agent_brain import system_extension

    original_handle = Orchestrator.handle
    if getattr(original_handle, "_jarvis_context_bridge", False):
        _installed = True
        return

    def handle_with_context(self, text: str, deep=None):
        user_text = str(text or "").strip()
        pending = _states.get(self)
        injected = False
        policy_injected = False
        capabilities_injected = False

        try:
            policy_marker = "ARQUITECTURA DE AGENTE JARVIS"
            if self.history and not any(policy_marker in str(x.get("content", "")) for x in self.history if x.get("role") == "system"):
                self.history.insert(1, {"role": "system", "content": system_extension()})
                policy_injected = True
            cap_marker = "CAPACIDADES DISPONIBLES:"
            if self.history and not any(cap_marker in str(x.get("content", "")) for x in self.history if x.get("role") == "system"):
                self.history.insert(2 if policy_injected else 1, {"role": "system", "content": _capability_context()})
                capabilities_injected = True
        except Exception:
            pass

        if pending and _is_short_followup(user_text):
            context_note = (
                "CONTINUIDAD DE CONVERSACIÓN — RESPUESTA A UNA PREGUNTA PENDIENTE:\n"
                f"JARVIS preguntó: {pending.question}\n"
                f"Contexto anterior: {pending.assistant_message[-1800:]}\n"
                f"El usuario acaba de responder: {user_text}\n\n"
                "Trata este mensaje como respuesta a la tarea pendiente. No cambies de tema. "
                "Completa el parámetro y continúa con las herramientas reales; después verifica el resultado."
            )
            try:
                self.history.insert(3 if (policy_injected or capabilities_injected) else 1, {"role": "system", "content": context_note})
                injected = True
            except Exception:
                pass

        try:
            result = original_handle(self, text, deep=deep)
        finally:
            for marker in ("CONTINUIDAD DE CONVERSACIÓN", "ARQUITECTURA DE AGENTE JARVIS", "CAPACIDADES DISPONIBLES:"):
                try:
                    for i, item in enumerate(list(self.history)):
                        if item.get("role") == "system" and marker in str(item.get("content", "")):
                            self.history.pop(i)
                            break
                except Exception:
                    pass

        answer = str(result or "").strip()
        if _looks_like_question(answer):
            with _lock:
                _states[self] = PendingContext(answer[:700], answer[:2200], __import__("time").time())
        elif pending and _is_short_followup(user_text):
            with _lock:
                _states.pop(self, None)
        return result

    handle_with_context._jarvis_context_bridge = True
    Orchestrator.handle = handle_with_context
    _installed = True
