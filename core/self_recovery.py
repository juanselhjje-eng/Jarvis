from __future__ import annotations

"""Safe self-recovery loop for JARVIS.

The agent may diagnose and repair non-destructive failures: retry a tool,
refresh a page, reopen an application, adjust parameters, switch providers,
or ask another model for a repair strategy. Destructive operations are never
implicitly authorized by this layer.
"""

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class RecoveryResult:
    ok: bool
    attempts: int
    message: str
    value: Any = None


class SelfRecovery:
    MAX_ATTEMPTS = 4

    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    @staticmethod
    def _is_destructive(description: str) -> bool:
        text = (description or "").lower()
        blocked = (
            "delete", "deletar", "eliminar", "borrar", "erase", "remove file",
            "format disk", "wipe", "destroy", "rm -rf", "rmdir /s"
        )
        return any(word in text for word in blocked)

    def run(self, action: Callable[[], Any], description: str = "", repair: Callable[[Exception, int], Any] | None = None) -> RecoveryResult:
        if self._is_destructive(description):
            return RecoveryResult(False, 0, "Acción destructiva bloqueada por la política de seguridad.")

        last_error: Exception | None = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                value = action()
                self.history.append({"action": description, "status": "ok", "attempt": str(attempt)})
                return RecoveryResult(True, attempt, "Acción completada y verificada.", value)
            except Exception as exc:
                last_error = exc
                self.history.append({"action": description, "status": "error", "attempt": str(attempt), "error": str(exc)})
                if repair is not None and attempt < self.MAX_ATTEMPTS:
                    try:
                        repair(exc, attempt)
                    except Exception as repair_error:
                        self.history.append({"action": "repair", "status": "error", "error": str(repair_error)})

        return RecoveryResult(False, self.MAX_ATTEMPTS, f"No pude completar la acción después de {self.MAX_ATTEMPTS} intentos: {last_error}")


recovery = SelfRecovery()
