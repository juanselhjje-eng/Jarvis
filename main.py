from __future__ import annotations

import re
import threading
import time

from src.jarvis.brain import JarvisBrain
from src.jarvis.command_router import CommandRouter
from src.jarvis.hud_v4 import JarvisHUDv4
from src.jarvis.voice_engine import VoiceEngine
from src.jarvis.agent_orchestrator import AgentOrchestrator
from src.jarvis.reasoning_layer import ReasoningLayer
from src.jarvis.agent_protocol import AgentProtocol


class Jarvis:
    """Entrada principal: un solo agente, control visible, visión puntual y Mission Control."""

    def __init__(self) -> None:
        self.running = True
        self.brain = JarvisBrain()
        self.tools = CommandRouter()
        self.voice = VoiceEngine()
        self.hud: JarvisHUDv4 | None = None
        self.reasoning = ReasoningLayer(self.brain)
        self.agent = AgentOrchestrator(self.brain, self.tools, self.tools.computer, self._agent_step)
        self.protocol = AgentProtocol()
        self._command_lock = threading.Lock()

    def start(self) -> None:
        if not self.brain.is_available():
            message = "El proveedor configurado no está disponible. Revisa Gemini u Ollama."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return
        self.hud = JarvisHUDv4(self.brain, self.voice, self.process_command, self.shutdown)
        self.hud.add_message("SYSTEM", f"JARVIS ONLINE // CORE {self.brain.provider.upper()} // COMPUTER USE + VISION + OODA")
        self.hud.update_provider()
        threading.Thread(target=self.voice.speak, args=("JARVIS iniciado. Te escucho.",), daemon=True).start()
        threading.Thread(target=self.run_voice_loop, daemon=True, name="jarvis-voice-loop").start()
        self.hud.run()

    def _agent_step(self, step) -> None:
        print(f"[MISSION] {step.number}: {step.status} — {step.action} {step.result}")
        if self.hud:
            try:
                self.hud.set_state("PENSANDO" if step.status == "PENDING" else step.status)
            except Exception:
                pass

    @staticmethod
    def _is_planning_request(command: str) -> bool:
        lower = command.lower()
        markers = ("planifica", "planea", "haz una misión", "haz una mision", "ejecuta esta misión", "ejecuta esta mision", "hazlo por pasos", "encárgate de", "encargate de")
        complex_markers = (" y luego ", " después ", " despues ", " y también ", " y tambien ", "varios pasos", "paso a paso")
        return any(x in lower for x in markers) or any(x in lower for x in complex_markers)

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command or not self.running:
            return
        lowered = command.lower().strip()
        if lowered in {"salir", "exit", "quit", "jarvis apágate", "jarvis apagarte", "cierrate", "ciérrate"}:
            self.shutdown()
            return
        if lowered in {"limpiar conversación", "limpia la conversación", "borra la conversación", "olvida esta conversación"}:
            self.brain.reset_conversation()
            self.respond("Conversación limpiada.")
            return

        with self._command_lock:
            print(f"[USER] {command}")
            effort_match = re.search(r"\b(?:esfuerzo|nivel de razonamiento|nivel cognitivo)\s+(bajo|medio|alto|low|medium|high)\b", lowered)
            if effort_match:
                value = {"bajo": "low", "medio": "medium", "alto": "high"}.get(effort_match.group(1), effort_match.group(1))
                self.reasoning.set_effort(value)
                self.agent.set_effort(value)
                self.respond(f"Esfuerzo cognitivo configurado en {value}.")
                return

            provider_match = re.search(r"\b(?:usa|usar|cambia a|cámbiate a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?(gemini|ollama)\b", lowered)
            if provider_match:
                try:
                    provider = self.brain.set_provider(provider_match.group(1))
                    if self.hud:
                        self.hud.update_provider()
                    self.respond(f"Entendido. Ahora usaré {provider}.")
                except (ValueError, RuntimeError) as exc:
                    self.respond(str(exc))
                return

            if lowered in {"mira la pantalla", "observa la pantalla", "captura la pantalla", "analiza la pantalla", "qué hay en mi pantalla", "que hay en mi pantalla"}:
                if self.hud:
                    self.hud.set_state("OBSERVANDO")
                observation = self.tools.computer.observe()
                if observation.image_base64:
                    result = self.brain.analyze_screen(observation.image_base64, command)
                else:
                    result = observation.note
                self.respond(result)
                return

            if self._is_planning_request(command):
                plan = self.agent.make_plan(command)
                self.agent.execute_visible(plan)
                self.respond(plan.summary())
                return

            tool_result = self.tools.handle(command)
            if isinstance(tool_result, dict):
                if tool_result.get("provider"):
                    try:
                        self.respond(f"Entendido. Ahora usaré {self.brain.set_provider(str(tool_result['provider']))}.")
                    except (ValueError, RuntimeError) as exc:
                        self.respond(str(exc))
                    return
                if tool_result.get("send_message") == "teams":
                    self.respond(self.tools.teams.send_draft())
                    return
                if tool_result.get("communication"):
                    action = tool_result.get("action")
                    educational = str(tool_result.get("educational", "False")).lower() == "true"
                    if action == "open":
                        self.respond(self.tools.teams.open(educational=educational))
                        return
                    if action == "open_contact":
                        self.respond(self.tools.teams.open_contact(str(tool_result.get("person", "")), educational=educational))
                        return
                    self.respond(str(tool_result.get("message", "Abrí la aplicación.")))
                    return
            if isinstance(tool_result, str):
                self.respond(tool_result)
                return

            result = self.reasoning.answer(command)
            if self.reasoning.effort == "high":
                verification = self.agent.verify_result(command, result)
                if verification != "Resultado verificado.":
                    result = result + "\n\n[VERIFICACIÓN] " + verification
            self.respond(result)

    def respond(self, text: str) -> None:
        print(f"[JARVIS] {text}\n")
        if self.hud:
            self.hud.set_response(text)
        threading.Thread(target=self.voice.speak, args=(text,), daemon=True).start()

    def run_voice_loop(self) -> None:
        while self.running:
            try:
                command = self.voice.listen_for_command(seconds=7)
                if command:
                    self.process_command(command)
            except KeyboardInterrupt:
                self.shutdown()
                return
            except Exception as exc:
                print(f"[VOICE] Error: {exc}")
                time.sleep(1)

    def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        try:
            self.voice.speak("Sistemas apagados.")
        finally:
            self.voice.shutdown()
        print("[SYSTEM] JARVIS detenido.")


def main() -> int:
    jarvis = Jarvis()
    try:
        jarvis.start()
        return 0
    except KeyboardInterrupt:
        jarvis.shutdown()
        return 0
    except Exception as exc:
        print(f"[FATAL] {exc}")
        try:
            jarvis.voice.speak("Se produjo un error crítico.")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
