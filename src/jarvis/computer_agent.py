from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from .agent_protocol import AgentProtocol, RiskLevel
from .computer_use import ComputerUse


@dataclass
class ComputerAction:
    action: str
    x: int | None = None
    y: int | None = None
    text: str = ""
    keys: list[str] | None = None
    button: str = "left"
    reason: str = ""


class ComputerAgent:
    """Agente visual acotado: observa la pantalla, decide una acción y vuelve a observar.

    No registra teclas ni ejecuta shell. Las acciones de comunicación o destructivas
    se detienen antes de ejecutarse y requieren confirmación explícita.
    """

    ACTIONS = {"click", "move", "type", "hotkey", "wait", "done", "ask_confirmation"}

    def __init__(self, brain, computer: ComputerUse, protocol: AgentProtocol, event: Callable[[str], None] | None = None) -> None:
        self.brain = brain
        self.computer = computer
        self.protocol = protocol
        self.event = event or (lambda _message: None)

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None

    def _decide(self, task: str, image_base64: str, history: list[str]) -> ComputerAction | None:
        prompt = f"""Actúa como controlador visual de Windows. Tienes una captura de pantalla y una tarea del usuario.
No muestres razonamiento. Devuelve SOLO JSON válido con esta forma:
{{"action":"click|move|type|hotkey|wait|done|ask_confirmation","x":0,"y":0,"text":"","keys":[],"button":"left","reason":"breve"}}
Reglas:
- Usa coordenadas de la imagen, no inventes coordenadas.
- Ejecuta una sola acción por ciclo.
- Si la tarea ya terminó, usa done.
- Si para terminar habría que enviar/publicar/comprar/eliminar algo, usa ask_confirmation antes de hacerlo.
- Para escribir texto normal usa type. Para teclas usa hotkey.
- No pidas credenciales ni copies contraseñas.
TAREA: {task}
ACCIONES PREVIAS: {history[-6:]}
"""
        try:
            response = self.brain.analyze_screen(image_base64, prompt)
            data = self._extract_json(response)
            if not data:
                return None
            action = str(data.get("action", "")).lower().strip()
            if action not in self.ACTIONS:
                return None
            return ComputerAction(
                action=action,
                x=int(data["x"]) if data.get("x") is not None else None,
                y=int(data["y"]) if data.get("y") is not None else None,
                text=str(data.get("text", "")),
                keys=[str(k) for k in (data.get("keys") or [])],
                button=str(data.get("button", "left")),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:
            self.event(f"VISION ERROR: {exc}")
            return None

    def run(self, task: str, max_steps: int = 10) -> str:
        task = task.strip()
        if not task:
            return "No recibí una tarea visual."
        history: list[str] = []
        for step in range(1, max_steps + 1):
            observation = self.computer.observe()
            if not observation.image_base64:
                return observation.note
            self.event(f"OODA {step}/{max_steps} • OBSERVE {observation.width}x{observation.height}")
            action = self._decide(task, observation.image_base64, history)
            if action is None:
                return "No pude obtener una acción visual válida. La tarea quedó detenida para evitar un clic a ciegas."
            policy = self.protocol.classify(action.action + " " + action.text)
            if action.action == "ask_confirmation" or policy.risk == RiskLevel.CONFIRM:
                return f"CONFIRMACIÓN NECESARIA: {action.reason or 'la siguiente acción afecta un servicio externo.'}"
            self.event(f"OODA {step}/{max_steps} • ACT {action.action} {action.reason}".strip())
            if action.action == "done":
                return action.reason or "Tarea completada."
            if action.action == "click" and action.x is not None and action.y is not None:
                result = self.computer.click(action.x, action.y, action.button)
            elif action.action == "move" and action.x is not None and action.y is not None:
                result = self.computer.move(action.x, action.y)
            elif action.action == "type":
                result = self.computer.type_text(action.text)
            elif action.action == "hotkey":
                result = self.computer.hotkey(*(action.keys or []))
            elif action.action == "wait":
                time.sleep(min(3.0, max(0.2, float(action.text or 1))))
                result = "Esperé y volveré a observar."
            else:
                return "Acción visual no soportada."
            history.append(f"{action.action}: {result}")
            self.event(f"OODA {step}/{max_steps} • RESULT {result}")
            time.sleep(0.25)
        return "Alcancé el límite de ciclos visuales sin confirmar que la tarea terminara."
