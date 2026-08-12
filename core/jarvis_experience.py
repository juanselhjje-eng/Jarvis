from __future__ import annotations

"""JARVIS experience layer.

Provides the cinematic desktop-assistant behavior: concise progress narration,
context-aware task continuity, adaptive tone, and a clear separation between
planning and user-facing speech. It does not expose private chain-of-thought.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskPhase(str, Enum):
    UNDERSTAND = "understand"
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    RECOVER = "recover"
    COMPLETE = "complete"


@dataclass
class TaskState:
    objective: str
    phase: TaskPhase = TaskPhase.UNDERSTAND
    step: str = ""
    progress: float = 0.0
    history: list[str] = field(default_factory=list)
    result: Any = None


class JarvisExperience:
    """High-level behavior used by the agent/UI/voice layers."""

    def __init__(self) -> None:
        self.current: TaskState | None = None
        self.recent_context: list[str] = []

    def begin(self, objective: str) -> TaskState:
        self.current = TaskState(objective=str(objective or "").strip())
        self.remember(str(objective or ""))
        return self.current

    def remember(self, text: str) -> None:
        if text:
            self.recent_context.append(text)
            self.recent_context = self.recent_context[-30:]

    def update(self, phase: TaskPhase, step: str, progress: float | None = None) -> TaskState | None:
        if not self.current:
            return None
        self.current.phase = phase
        self.current.step = step
        if progress is not None:
            self.current.progress = max(0.0, min(1.0, float(progress)))
        if step:
            self.current.history.append(step)
        return self.current

    def status_line(self) -> str:
        if not self.current:
            return "En espera."
        if self.current.phase is TaskPhase.COMPLETE:
            return "Tarea completada y verificada."
        if self.current.step:
            return self.current.step
        return "Analizando la solicitud."

    def should_ask(self, missing_critical_information: bool, already_in_context: bool = False) -> bool:
        return bool(missing_critical_information and not already_in_context)

    def progress_message(self, phase: TaskPhase, detail: str = "") -> str:
        prefixes = {
            TaskPhase.UNDERSTAND: "Estoy analizando el objetivo",
            TaskPhase.PLAN: "Estoy preparando el plan",
            TaskPhase.ACT: "Voy a ejecutar el siguiente paso",
            TaskPhase.VERIFY: "Estoy comprobando el resultado",
            TaskPhase.RECOVER: "Encontré un problema; estoy buscando otra forma de resolverlo",
            TaskPhase.COMPLETE: "He terminado y comprobado el resultado",
        }
        base = prefixes[phase]
        return f"{base}. {detail}".strip()

    def compact_context(self) -> str:
        return "\n".join(f"- {x}" for x in self.recent_context[-12:])


experience = JarvisExperience()
