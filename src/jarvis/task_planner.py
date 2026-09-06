from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskStep:
    number: int
    action: str
    status: str = "PENDING"


@dataclass
class TaskPlan:
    goal: str
    steps: list[TaskStep] = field(default_factory=list)
    requires_confirmation: bool = False

    def summary(self) -> str:
        lines = [f"Objetivo: {self.goal}"]
        for step in self.steps:
            lines.append(f"{step.number}. [{step.status}] {step.action}")
        if self.requires_confirmation:
            lines.append("Confirmación necesaria antes de una acción externa.")
        return "\n".join(lines)


class TaskPlanner:
    """Planificador explícito. El plan se muestra antes de acciones externas."""

    def plan(self, goal: str) -> TaskPlan:
        text = goal.strip()
        lower = text.lower()
        steps: list[TaskStep] = []

        if any(word in lower for word in ("apartamento", "casa", "inmueble", "arriendo", "alquiler")):
            steps = [
                TaskStep(1, "Abrir el navegador y buscar el inmueble con las condiciones indicadas."),
                TaskStep(2, "Revisar resultados y descartar los que no cumplan las condiciones."),
                TaskStep(3, "Abrir los candidatos restantes y comprobar los datos disponibles."),
                TaskStep(4, "Preparar una solicitud o mensaje de contacto, sin enviarlo todavía."),
                TaskStep(5, "Mostrar el mensaje y pedir confirmación antes de enviarlo o agendar una cita."),
            ]
            return TaskPlan(text, steps, requires_confirmation=True)

        if any(word in lower for word in ("busca", "investiga", "revisa", "compara")):
            steps = [
                TaskStep(1, "Interpretar el objetivo y separar los criterios."),
                TaskStep(2, "Recopilar información relevante."),
                TaskStep(3, "Descartar resultados que no cumplan los criterios."),
                TaskStep(4, "Verificar los datos importantes."),
                TaskStep(5, "Presentar el resultado y las siguientes acciones disponibles."),
            ]
            return TaskPlan(text, steps)

        steps = [
            TaskStep(1, "Interpretar la intención."),
            TaskStep(2, "Elegir las herramientas disponibles y seguras."),
            TaskStep(3, "Ejecutar una acción verificable cuando exista una herramienta compatible."),
            TaskStep(4, "Comprobar el resultado y reportarlo."),
        ]
        return TaskPlan(text, steps)
