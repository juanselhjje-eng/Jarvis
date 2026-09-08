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
    x2: int | None = None
    y2: int | None = None
    amount: int = 0
    text: str = ""
    keys: list[str] | None = None
    button: str = "left"
    target: str = ""
    reason: str = ""


class ComputerAgent:
    """Controlador visual OODA para tareas dentro de aplicaciones y webs."""

    ACTIONS = {"click", "double_click", "move", "scroll", "drag", "type", "hotkey", "wait", "done", "ask_confirmation"}

    def __init__(self, brain, computer: ComputerUse, protocol: AgentProtocol, event: Callable[[str], None] | None = None) -> None:
        self.brain = brain
        self.computer = computer
        self.protocol = protocol
        self.event = event or (lambda _message: None)
        self.pending_task: str | None = None
        self.pending_reason: str = ""

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

    def _decide(self, task: str, image_base64: str, history: list[str], approval_granted: bool) -> ComputerAction | None:
        prompt = f"""Actúa como controlador visual de Windows. Tienes una captura actual y una tarea del usuario.
Devuelve SOLO JSON válido:
{{"action":"click|double_click|move|scroll|drag|type|hotkey|wait|done|ask_confirmation","x":0,"y":0,"x2":0,"y2":0,"amount":0,"text":"","keys":[],"button":"left","target":"texto visible del objetivo","reason":"breve"}}
Reglas estrictas:
- Usa coordenadas de la captura; nunca inventes coordenadas.
- Una acción por ciclo y después vuelve a observar.
- target describe el control visible que vas a tocar/escribir.
- Usa scroll para desplazarte, drag para mover objetos, double_click para abrir elementos.
- Si necesitas enviar, publicar, comprar, confirmar una operación externa, eliminar datos o realizar una acción irreversible, usa ask_confirmation ANTES de esa acción.
- Si approval_granted=true, puedes ejecutar la acción externa que acabas de pedir confirmar, pero no inventes una acción diferente.
- No pidas ni copies contraseñas, códigos de autenticación, cookies o claves.
- No ejecutes comandos de terminal.
TAREA: {task}
APROBACIÓN EXPLÍCITA: {approval_granted}
ACCIONES PREVIAS: {history[-8:]}
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
                x2=int(data["x2"]) if data.get("x2") is not None else None,
                y2=int(data["y2"]) if data.get("y2") is not None else None,
                amount=int(data.get("amount", 0) or 0),
                text=str(data.get("text", "")),
                keys=[str(k) for k in (data.get("keys") or [])],
                button=str(data.get("button", "left")),
                target=str(data.get("target", "")),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:
            self.event(f"VISION ERROR: {exc}")
            return None

    def _needs_confirmation(self, task: str, action: ComputerAction) -> bool:
        if action.action == "ask_confirmation":
            return True
        risk_text = f"{task} {action.target} {action.text}".lower()
        return self.protocol.classify(risk_text).risk == RiskLevel.CONFIRM

    def run(self, task: str, max_steps: int = 12, approval_granted: bool = False) -> str:
        task = task.strip()
        if not task:
            return "No recibí una tarea visual."
        history: list[str] = []
        for step in range(1, max_steps + 1):
            observation = self.computer.observe()
            if not observation.image_base64:
                return observation.note
            self.event(f"OODA {step}/{max_steps} • OBSERVE {observation.width}x{observation.height}")
            action = self._decide(task, observation.image_base64, history, approval_granted)
            if action is None:
                return "La decisión visual no fue válida. Detuve la misión para evitar una acción a ciegas."
            if self._needs_confirmation(task, action) and not approval_granted:
                self.pending_task = task
                self.pending_reason = action.reason or action.target or "acción externa"
                self.event(f"HUMAN GATE • {self.pending_reason}")
                return f"CONFIRMACIÓN NECESARIA: {self.pending_reason}. Di 'sí, envíalo' para continuar o 'no' para cancelar."

            self.event(f"OODA {step}/{max_steps} • ACT {action.action} {action.target or action.reason}".strip())
            if action.action == "done":
                self.pending_task = None
                self.pending_reason = ""
                return action.reason or "Tarea completada y verificada."
            if action.action == "click" and action.x is not None and action.y is not None:
                result = self.computer.click(action.x, action.y, action.button)
            elif action.action == "double_click" and action.x is not None and action.y is not None:
                result = self.computer.double_click(action.x, action.y)
            elif action.action == "move" and action.x is not None and action.y is not None:
                result = self.computer.move(action.x, action.y)
            elif action.action == "scroll":
                result = self.computer.scroll(action.amount or 1)
            elif action.action == "drag" and None not in (action.x, action.y, action.x2, action.y2):
                result = self.computer.drag(action.x, action.y, action.x2, action.y2)
            elif action.action == "type":
                result = self.computer.type_text(action.text)
            elif action.action == "hotkey":
                result = self.computer.hotkey(*(action.keys or []))
            elif action.action == "wait":
                time.sleep(min(3.0, max(0.2, float(action.text or 1))))
                result = "Esperé y volveré a observar."
            elif action.action == "ask_confirmation":
                self.pending_task = task
                self.pending_reason = action.reason or action.target or "acción externa"
                return f"CONFIRMACIÓN NECESARIA: {self.pending_reason}. Di 'sí, envíalo' para continuar o 'no' para cancelar."
            else:
                return "Acción visual no soportada."
            history.append(f"{action.action} [{action.target}]: {result}")
            self.event(f"OODA {step}/{max_steps} • RESULT {result}")
            time.sleep(0.25)
        return "Alcancé el límite de ciclos visuales sin confirmar que la tarea terminara."

    def confirm(self, accepted: bool) -> str:
        task = self.pending_task
        self.pending_task = None
        reason = self.pending_reason
        self.pending_reason = ""
        if not accepted:
            return "Misión cancelada. No ejecuté la acción pendiente."
        if not task:
            return "No hay ninguna acción visual pendiente de confirmación."
        self.event(f"HUMAN GATE • APPROVED • {reason}")
        return self.run(task, max_steps=8, approval_granted=True)

    @property
    def has_pending(self) -> bool:
        return bool(self.pending_task)
