from __future__ import annotations

"""General-purpose agent runtime primitives.

This module provides the state machine used by higher layers: a goal has
observable steps, progress messages, retries, and verification hooks. It does
not execute arbitrary commands by itself; concrete tools remain responsible
for permissions and side effects.
"""

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable


@dataclass
class AgentStep:
    name: str
    action: Callable[[], Any] | None = None
    verify: Callable[[Any], bool] | None = None
    retries: int = 1
    status: str = "PENDING"
    result: Any = None
    error: str = ""


@dataclass
class AgentGoal:
    request: str
    steps: list[AgentStep] = field(default_factory=list)
    status: str = "PLANNED"
    started_at: float = field(default_factory=monotonic)
    finished_at: float | None = None

    def add(self, name: str, action: Callable[[], Any] | None = None,
            verify: Callable[[Any], bool] | None = None, retries: int = 1) -> "AgentGoal":
        self.steps.append(AgentStep(name, action, verify, max(0, retries)))
        return self


class AgentRuntime:
    """Execute already-approved steps with verification and bounded recovery."""

    def __init__(self, narrator: Callable[[str], None] | None = None):
        self.narrator = narrator or (lambda _message: None)

    def _say(self, message: str) -> None:
        try:
            self.narrator(message)
        except Exception:
            pass

    def run(self, goal: AgentGoal) -> AgentGoal:
        goal.status = "RUNNING"
        for step in goal.steps:
            if step.action is None:
                step.status = "SKIPPED"
                continue
            attempts = step.retries + 1
            for attempt in range(attempts):
                try:
                    step.status = "RUNNING"
                    self._say(f"Estoy trabajando en: {step.name}.")
                    step.result = step.action()
                    if step.verify is not None and not step.verify(step.result):
                        raise RuntimeError("La verificación no confirmó el resultado.")
                    step.status = "DONE"
                    self._say(f"Listo: {step.name} quedó verificado.")
                    break
                except Exception as exc:
                    step.error = str(exc)
                    if attempt + 1 >= attempts:
                        step.status = "FAILED"
                        self._say(f"Tuve un problema con: {step.name}. No voy a fingir que quedó hecho.")
                    else:
                        self._say(f"El primer intento de {step.name} falló; voy a recuperarlo.")
            if step.status == "FAILED":
                goal.status = "BLOCKED"
                goal.finished_at = monotonic()
                return goal
        goal.status = "COMPLETED"
        goal.finished_at = monotonic()
        return goal
