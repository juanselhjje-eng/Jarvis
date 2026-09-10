from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from .agent_protocol import AgentProtocol, RiskLevel
from .computer_use import ComputerUse, ScreenObservation
from .neural_lab import NeuralLab


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
    """Agente visual OODA para controlar el escritorio de forma visible.

    Cada ciclo observa, decide una sola acción, la ejecuta y vuelve a observar. Además,
    la observación alimenta un grafo neuronal visual local para que el laboratorio pueda
    representar cómo cambia la pantalla durante la misión.
    """

    ACTIONS = {"click", "double_click", "move", "scroll", "drag", "type", "hotkey", "wait", "done", "ask_confirmation"}

    def __init__(
        self,
        brain,
        computer: ComputerUse,
        protocol: AgentProtocol,
        event: Callable[[str], None] | None = None,
        observation: Callable[[ScreenObservation], None] | None = None,
    ) -> None:
        self.brain = brain
        self.computer = computer
        self.protocol = protocol
        self.event = event or (lambda _message: None)
        self.observation_callback = observation or (lambda _observation: None)
        self.neural_lab = NeuralLab()
        self.pending_task: str | None = None
        self.pending_reason: str = ""
        self._stop_event = threading.Event()
        self._running = threading.Event()
        self._last_observation_hash: str | None = None
        self._last_action_signature: str | None = None

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

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower().strip())

    @classmethod
    def _requested_contact(cls, task: str) -> str | None:
        """Extrae un contacto explícito de órdenes tipo 'a la que se llama Majo G'."""
        patterns = (
            r"(?:a la que se llama|al que se llama|que se llama|se llama)\s+([\wáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+[\wáéíóúüñÁÉÍÓÚÜÑ]+){0,3})",
            r"(?:contacto|persona)\s+(?:llamad[oa]\s+)?([\wáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+[\wáéíóúüñÁÉÍÓÚÜÑ]+){0,3})",
        )
        for pattern in patterns:
            match = re.search(pattern, task, flags=re.IGNORECASE)
            if match:
                value = re.split(r"\s+(?:y|para|dile|escribe|envía|enviale|mándale|mandale)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,.;:")
                if value:
                    return value
        return None

    def _decide(self, task: str, image_base64: str, history: list[str], approval_granted: bool) -> ComputerAction | None:
        requested_contact = self._requested_contact(task)
        contact_rule = (
            f"- CONTACTO OBJETIVO EXACTO: {requested_contact}. Si vas a seleccionar un chat, target debe contener este nombre exacto (ignorando mayúsculas/minúsculas). Nunca selecciones otro contacto parecido. Si no aparece, NO hagas clic en otro nombre; usa búsqueda/scroll o done explicando que no está visible."
            if requested_contact
            else "- Si la tarea menciona un contacto, respeta exactamente ese nombre y no lo sustituyas por otro parecido."
        )
        prompt = f"""Actúa como controlador visual de Windows. Tienes una captura actual y una tarea del usuario.
Devuelve SOLO JSON válido:
{{"action":"click|double_click|move|scroll|drag|type|hotkey|wait|done|ask_confirmation","x":0,"y":0,"x2":0,"y2":0,"amount":0,"text":"","keys":[],"button":"left","target":"texto visible del objetivo","reason":"breve"}}

REGLAS:
- Las coordenadas deben corresponder a la captura actual. Nunca inventes coordenadas.
- Haz UNA acción por ciclo y después vuelve a observar.
- target debe identificar el control visible que vas a usar.
{contact_rule}
- Después de seleccionar un contacto, verifica en la siguiente captura que el chat abierto corresponde al contacto exacto antes de considerar la navegación completada.
- Si la captura actual ya muestra el contacto exacto abierto, NO vuelvas a hacer clic sobre el mismo chat: usa done si la parte de navegación está terminada o continúa con el siguiente paso.
- Si una operación envía/publica/compra/confirma algo externamente o elimina datos, usa ask_confirmation ANTES.
- Si approval_granted=true, ejecuta únicamente la operación externa que acabas de solicitar.
- No solicites ni copies contraseñas, códigos de autenticación, cookies, tokens ni claves API.
- No uses terminal ni comandos de shell.
- Si la pantalla no contiene lo necesario, usa scroll, espera o done con una explicación; no adivines.

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
                amount=max(-12, min(12, int(data.get("amount", 0) or 0))),
                text=str(data.get("text", "")),
                keys=[str(k) for k in (data.get("keys") or [])],
                button=str(data.get("button", "left")),
                target=str(data.get("target", "")),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:
            self.event(f"VISION ERROR: {exc}")
            return None

    def _validate_contact_action(self, task: str, action: ComputerAction) -> bool:
        """Bloquea clics sobre otro nombre cuando la orden tiene un contacto explícito."""
        if action.action not in {"click", "double_click"}:
            return True
        contact = self._requested_contact(task)
        if not contact:
            return True
        target = self._normalize(action.target)
        wanted = self._normalize(contact)
        if wanted not in target:
            self.event(f"CONTACT GUARD • BLOQUEADO • objetivo '{action.target}' no coincide con '{contact}'")
            return False
        return True

    def _is_duplicate_click(self, observation: ScreenObservation, action: ComputerAction) -> bool:
        if action.action not in {"click", "double_click"}:
            return False
        signature = f"{action.action}:{action.x}:{action.y}:{self._normalize(action.target)}"
        screen_hash = hashlib.sha256(observation.image_base64.encode("utf-8")).hexdigest() if observation.image_base64 else None
        duplicate = screen_hash == self._last_observation_hash and signature == self._last_action_signature
        if duplicate:
            self.event("VISION GUARD • BLOQUEADO • mismo clic sobre la misma pantalla")
        return duplicate

    def _remember_action(self, observation: ScreenObservation, action: ComputerAction) -> None:
        self._last_observation_hash = hashlib.sha256(observation.image_base64.encode("utf-8")).hexdigest() if observation.image_base64 else None
        self._last_action_signature = f"{action.action}:{action.x}:{action.y}:{self._normalize(action.target)}" if action.action in {"click", "double_click"} else None

    def _needs_confirmation(self, task: str, action: ComputerAction) -> bool:
        if action.action == "ask_confirmation":
            return True
        risk_text = f"{task} {action.target} {action.text}".lower()
        return self.protocol.classify(risk_text).risk == RiskLevel.CONFIRM

    def _observe_and_learn(self, task: str) -> ScreenObservation:
        observation = self.computer.observe()
        self.observation_callback(observation)
        if observation.image_base64:
            try:
                graph = self.neural_lab.observe_screen(observation.image_base64, observation.width, observation.height, task)
                self.event(f"NEURAL VISION • {graph['nodes']} nodos / {graph['edges']} conexiones")
            except Exception as exc:
                self.event(f"NEURAL LAB • no se pudo actualizar la topología visual: {exc}")
        return observation

    def run(self, task: str, max_steps: int = 12, approval_granted: bool = False) -> str:
        task = task.strip()
        if not task:
            return "No recibí una tarea visual."
        self._stop_event.clear()
        self._running.set()
        self._last_observation_hash = None
        self._last_action_signature = None
        history: list[str] = []
        try:
            for step in range(1, max_steps + 1):
                if self._stop_event.is_set():
                    return "Misión detenida por el usuario."

                observation = self._observe_and_learn(task)
                if not observation.image_base64:
                    return observation.note
                self.event(f"OODA {step}/{max_steps} • OBSERVE {observation.width}x{observation.height}")

                if self._stop_event.is_set():
                    return "Misión detenida por el usuario."
                action = self._decide(task, observation.image_base64, history, approval_granted)
                if action is None:
                    return "La decisión visual no fue válida. Detuve la misión para evitar una acción a ciegas."

                if not self._validate_contact_action(task, action):
                    history.append(f"GUARD: bloqueé {action.action} hacia '{action.target}' porque no coincide con el contacto solicitado.")
                    continue
                if self._is_duplicate_click(observation, action):
                    history.append(f"GUARD: bloqueé clic repetido sobre '{action.target}'.")
                    continue

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

                self._remember_action(observation, action)
                history.append(f"{action.action} [{action.target}]: {result}")
                self.event(f"OODA {step}/{max_steps} • RESULT {result}")
                time.sleep(0.20)
            return "Alcancé el límite de ciclos visuales sin confirmar que la tarea terminara."
        finally:
            self._running.clear()

    def stop(self) -> None:
        """Solicita detener el ciclo actual; es seguro llamarlo desde otro hilo."""
        self._stop_event.set()
        self.event("MISSION STOP • solicitud de parada recibida")

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

    @property
    def is_running(self) -> bool:
        return self._running.is_set()
