from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subagent:
    name: str
    role: str
    focus: str
    color: str


class SubagentTeam:
    """Equipo local de especialistas coordinado por el único agente JARVIS.

    Los subagentes no son identidades independientes ni crean cuentas externas: son
    roles especializados que el agente principal activa según la misión. El resultado
    siempre vuelve al agente principal para decidir y ejecutar.
    """

    CATALOG = (
        Subagent("ORCHESTRATOR", "Coordinador", "objetivo, prioridades y reparto de trabajo", "#25d9ff"),
        Subagent("VISION", "Percepción", "pantalla, UI visible y estado actual", "#55a7ff"),
        Subagent("PLANNER", "Planificador", "descomposición y secuencia de pasos", "#a77cff"),
        Subagent("DESKTOP", "Operador", "mouse, teclado, ventanas y aplicaciones", "#3ee5a1"),
        Subagent("RESEARCH", "Investigador", "búsqueda, fuentes y comparación", "#ffad4a"),
        Subagent("MEMORY", "Memoria", "preferencias, contexto y lecciones", "#f36cff"),
        Subagent("VERIFY", "Verificador", "resultado, evidencia y corrección", "#ff5f73"),
    )

    def __init__(self) -> None:
        self.active: list[Subagent] = [self.CATALOG[0]]
        self.mission = ""

    def activate_for(self, mission: str) -> list[Subagent]:
        text = mission.lower()
        selected = [self.CATALOG[0]]
        if any(x in text for x in ("pantalla", "pulsa", "clic", "click", "entra", "abre", "selecciona", "escribe", "teams", "navegador")):
            selected.extend([self.CATALOG[1], self.CATALOG[3]])
        if len(text.split()) >= 8 or any(x in text for x in ("paso a paso", "plan", "haz todo", "busca y", "encárgate")):
            selected.append(self.CATALOG[2])
        if any(x in text for x in ("busca", "investiga", "compara", "fuentes", "web")):
            selected.append(self.CATALOG[4])
        if any(x in text for x in ("recuerda", "memoria", "prefiero", "aprende")):
            selected.append(self.CATALOG[5])
        selected.append(self.CATALOG[6])

        unique: list[Subagent] = []
        seen = set()
        for agent in selected:
            if agent.name not in seen:
                unique.append(agent)
                seen.add(agent.name)
        self.active = unique
        self.mission = mission
        return list(self.active)

    def roster(self) -> list[Subagent]:
        return list(self.CATALOG)

    def status_text(self) -> str:
        return " · ".join(agent.name for agent in self.active)

    def event_text(self) -> str:
        return f"SUBAGENTS ACTIVE // {self.status_text()}"
