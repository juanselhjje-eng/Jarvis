from __future__ import annotations

"""Latency-aware AI gateway for JARVIS.

The existing multi-model council is valuable for difficult work, but it should
never be invoked for a greeting, a short conversational turn, or background
reflection. This wrapper keeps the full council available while routing simple
messages through a single fast provider.
"""

import re
from providers.ai_gateway_manager import AIGatewayManager


_SIMPLE_RE = re.compile(
    r"^(?:hola|holi|hey|buenas|buenos dias|buenas tardes|buenas noches|que tal|cómo estás|como estas|gracias|ok|vale|perfecto|entendido|quién eres|quien eres|qué haces|que haces|estás ahí|estas ahi)[!,.?¿¡ ]*$",
    re.IGNORECASE,
)

_COMPLEX_MARKERS = (
    "analiza", "compara", "investiga", "planifica", "planea", "diseña", "arquitectura",
    "programa", "programación", "codigo", "código", "proyecto", "razona", "explica en detalle",
    "profund", "varias opciones", "mejor opción", "mejor opcion", "revisa", "audita", "estudia",
    "resume este", "documento", "estrategia", "problema complejo", "consejo multi",
)

_BACKGROUND_MARKERS = (
    "analiza esta interacción real de jarvis",
    "módulo de reflexión y aprendizaje persistente",
    "generador de aprendizaje proactivo",
)


def _last_user_text(messages) -> str:
    for message in reversed(messages or []):
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content", ""))[:4000].strip()
    return ""


class LatencyAIGatewayManager(AIGatewayManager):
    """AIGatewayManager with an adaptive latency policy."""

    def chat(self, messages, tools=None, **kwargs):
        text = _last_user_text(messages)
        lowered = text.casefold().strip()

        # Background reflection must not occupy the conversation lock for a
        # multi-round council. It only needs a concise classification/lesson.
        if any(marker in lowered for marker in _BACKGROUND_MARKERS):
            kwargs["think"] = False
            kwargs.setdefault("max_tokens", 900)
            return super().chat(messages, tools=None, **kwargs)

        # Greetings and tiny conversational turns are always single-pass.
        if not tools and (_SIMPLE_RE.fullmatch(lowered) or len(text) <= 55):
            kwargs["think"] = False
            kwargs.setdefault("temperature", 0.25)
            kwargs.setdefault("max_tokens", 500)
            return super().chat(messages, tools=None, **kwargs)

        # Normal text stays fast unless the user clearly asks for substantial
        # reasoning. Explicit think=True still enables the existing council.
        if not tools and kwargs.get("think") and not any(m in lowered for m in _COMPLEX_MARKERS):
            kwargs["think"] = False
            kwargs.setdefault("max_tokens", 1200)
            return super().chat(messages, tools=None, **kwargs)

        return super().chat(messages, tools=tools, **kwargs)
