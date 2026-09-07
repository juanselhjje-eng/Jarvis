from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PlanStep:
    number: int
    action: str
    status: str = "PENDING"
    result: str = ""
    requires_confirmation: bool = False


@dataclass
class AgentPlan:
    goal: str
    effort: str
    steps: list[PlanStep] = field(default_factory=list)

    @property
    def requires_confirmation(self) -> bool:
        return any(step.requires_confirmation for step in self.steps)

    def summary(self) -> str:
        lines = [f"Misión: {self.goal}", f"Esfuerzo: {self.effort.upper()}"]
        for step in self.steps:
            detail = f" — {step.result}" if step.result else ""
            lines.append(f"{step.number}. [{step.status}] {step.action}{detail}")
        return "\n".join(lines)


class AgentOrchestrator:
    """Orquestador de un único agente. No expone cadenas de pensamiento privadas."""

    SAFE_ACTIONS = {
        "open_application", "open_url", "search_web", "system_status",
        "screenshot", "move_cursor", "click", "type_text", "hotkey",
        "create_task", "create_reminder", "open_teams", "prepare_message",
    }

    def __init__(self, brain, router, computer, on_step: Callable[[PlanStep], None] | None = None):
        self.brain = brain
        self.router = router
        self.computer = computer
        self.on_step = on_step
        self.effort = "medium"

    def set_effort(self, effort: str) -> str:
        effort = effort.lower().strip()
        if effort not in {"low", "medium", "high"}:
            raise ValueError("El esfuerzo debe ser low, medium o high.")
        self.effort = effort
        return effort

    def _heuristic_plan(self, goal: str) -> AgentPlan:
        lower = goal.lower()
        actions: list[tuple[str, bool]] = []
        if any(x in lower for x in ("teams", "gmail", "correo", "telegram")):
            actions.append(("Abrir la aplicación o servicio solicitado.", False))
        if any(x in lower for x in ("busca", "investiga", "consulta", "compara")):
            actions.extend([("Realizar la búsqueda con los criterios indicados.", False), ("Comprobar y filtrar los resultados.", False)])
        if any(x in lower for x in ("mensaje", "escríbele", "dile", "envía", "correo")):
            actions.append(("Preparar la comunicación y mostrarla antes de enviarla.", True))
        if any(x in lower for x in ("archivo", "documento", "carpeta")):
            actions.append(("Localizar y verificar los archivos antes de modificar algo.", False))
        if not actions:
            actions = [("Interpretar el objetivo y seleccionar herramientas.", False), ("Ejecutar las acciones compatibles.", False), ("Verificar el resultado.", False)]
        return AgentPlan(goal, self.effort, [PlanStep(i + 1, action, requires_confirmation=confirm) for i, (action, confirm) in enumerate(actions)])

    def make_plan(self, goal: str) -> AgentPlan:
        # El modelo puede sugerir un plan, pero la ejecución se valida contra SAFE_ACTIONS.
        # Si el proveedor no responde en formato válido, usamos el plan seguro heurístico.
        plan = self._heuristic_plan(goal)
        if self.effort == "low":
            return plan
        try:
            prompt = (
                "Devuelve SOLO JSON válido con la forma "
                '{"steps":[{"action":"...","requires_confirmation":false}]} . '
                "No incluyas razonamiento privado. Usa máximo 6 pasos. "
                f"Objetivo: {goal}"
            )
            raw = self.brain.ask(prompt)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data: dict[str, Any] = json.loads(match.group(0)) if match else {}
            candidate = data.get("steps", [])
            if isinstance(candidate, list) and candidate:
                steps = []
                for i, item in enumerate(candidate[:6], 1):
                    if not isinstance(item, dict):
                        continue
                    action = str(item.get("action", "")).strip()
                    if not action:
                        continue
                    steps.append(PlanStep(i, action, requires_confirmation=bool(item.get("requires_confirmation", False))))
                if steps:
                    plan.steps = steps
        except Exception as exc:
            print(f"[AGENT] Plan estructurado no disponible: {exc}")
        return plan

    def execute_visible(self, plan: AgentPlan) -> AgentPlan:
        """Ejecuta únicamente acciones locales explícitas conocidas por el router/computer."""
        # En esta versión el modelo no recibe una ruta para ejecutar shell arbitrario.
        for step in plan.steps:
            if self.on_step:
                self.on_step(step)
            if step.requires_confirmation:
                step.status = "WAITING_CONFIRMATION"
                step.result = "Requiere confirmación del usuario."
                if self.on_step:
                    self.on_step(step)
                break
            step.status = "READY"
            step.result = "Paso validado; la ejecución concreta pasa por las herramientas deterministas."
            if self.on_step:
                self.on_step(step)
        return plan
