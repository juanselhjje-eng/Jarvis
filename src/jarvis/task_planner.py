from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskStep:
    number: int
    action: str
    status: str = "PENDING"
    detail: str = ""


@dataclass
class TaskPlan:
    goal: str
    steps: list[TaskStep] = field(default_factory=list)
    requires_confirmation: bool = False

    def summary(self) -> str:
        lines = [f"Objetivo: {self.goal}"]
        for step in self.steps:
            suffix = f" — {step.detail}" if step.detail else ""
            lines.append(f"{step.number}. [{step.status}] {step.action}{suffix}")
        if self.requires_confirmation:
            lines.append("Confirmación necesaria antes de una acción externa.")
        return "\n".join(lines)

    def mark(self, number: int, status: str, detail: str = "") -> None:
        for step in self.steps:
            if step.number == number:
                step.status = status
                step.detail = detail
                return


class TaskPlanner:
    """Planificador explícito para tareas de varios pasos."""

    def plan(self, goal: str) -> TaskPlan:
        text = goal.strip()
        lower = text.lower()
        if any(word in lower for word in ("apartamento", "casa", "inmueble", "arriendo", "alquiler")):
            steps = [
                "Abrir el navegador y buscar con las condiciones indicadas.",
                "Revisar resultados y descartar los que no cumplan.",
                "Abrir candidatos y comprobar sus datos.",
                "Preparar contacto sin enviarlo.",
                "Mostrarlo y pedir confirmación antes de enviar o agendar.",
            ]
            return TaskPlan(text, [TaskStep(i + 1, a) for i, a in enumerate(steps)], True)
        if any(word in lower for word in ("busca", "investiga", "revisa", "compara")):
            steps = ["Interpretar criterios.", "Recopilar información.", "Filtrar resultados.", "Verificar datos.", "Presentar resultados."]
            return TaskPlan(text, [TaskStep(i + 1, a) for i, a in enumerate(steps)])
        steps = ["Interpretar intención.", "Elegir herramientas.", "Ejecutar acciones compatibles.", "Comprobar resultado."]
        return TaskPlan(text, [TaskStep(i + 1, a) for i, a in enumerate(steps)])
