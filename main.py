from __future__ import annotations

import re
import threading
import time

from src.jarvis.agent_protocol import AgentProtocol
from src.jarvis.brain import JarvisBrain
from src.jarvis.command_router import CommandRouter
from src.jarvis.computer_agent import ComputerAgent
from src.jarvis.hud_v5 import JarvisHUDv5
from src.jarvis.neural_lab import NeuralLab
from src.jarvis.reasoning_layer import ReasoningLayer
from src.jarvis.voice_engine import VoiceEngine


class Jarvis:
    """Runtime único de JARVIS: cerebro + planificación + Computer Use + aprendizaje local."""

    OPENABLE = r"chrome|google chrome|edge|microsoft edge|firefox|teams|microsoft teams|notepad|bloc de notas|explorer|explorador|calculadora|calculator|settings|configuración|discord|spotify|github|youtube|gmail"

    def __init__(self) -> None:
        self.running = True
        self.busy = False
        self.brain = JarvisBrain()
        self.tools = CommandRouter()
        self.voice = VoiceEngine()
        self.protocol = AgentProtocol()
        self.reasoning = ReasoningLayer(self.brain)
        self.neural = NeuralLab()
        self.hud: JarvisHUDv5 | None = None
        self._command_lock = threading.Lock()
        self.computer_agent = ComputerAgent(self.brain, self.tools.computer, self.protocol, self._agent_event)

    def start(self) -> None:
        if not self.brain.is_available():
            message = "No hay cerebro disponible. Revisa GEMINI_API_KEY o inicia Ollama."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return
        self.hud = JarvisHUDv5(self.brain, self.voice, self.process_command, self.shutdown, neural=self.neural)
        self._hud_message("SYSTEM", f"JARVIS ONLINE // CORE {self.brain.provider.upper()} // COMPUTER USE + OODA + NEURAL LAB")
        self._hud_state("ONLINE")
        threading.Thread(target=self.voice.speak, args=("JARVIS iniciado. Te escucho.",), daemon=True).start()
        threading.Thread(target=self.run_voice_loop, daemon=True, name="jarvis-voice-loop").start()
        self.hud.run()

    def _hud_message(self, sender: str, text: str) -> None:
        if self.hud:
            try:
                self.hud.add_message(sender, text)
            except Exception:
                pass

    def _hud_state(self, state: str) -> None:
        if self.hud:
            try:
                self.hud.set_state(state)
            except Exception:
                pass

    def _agent_event(self, message: str) -> None:
        print(f"[AGENT] {message}")
        self._hud_message("AGENT", message)
        if self.hud and "HUMAN GATE" in message:
            self._hud_state("VERIFICANDO")

    @staticmethod
    def _effort(command: str) -> str | None:
        match = re.search(r"\b(?:esfuerzo|nivel de razonamiento|nivel cognitivo)\s+(bajo|medio|alto|low|medium|high)\b", command.lower())
        return {"bajo": "low", "medio": "medium", "alto": "high"}.get(match.group(1), match.group(1)) if match else None

    @staticmethod
    def _provider(command: str) -> str | None:
        match = re.search(r"\b(?:usa|usar|cambia a|cámbiate a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?(gemini|ollama)\b", command.lower())
        return match.group(1) if match else None

    @staticmethod
    def _confirmation(command: str) -> bool:
        value = re.sub(r"[^a-záéíóúüñ ]", "", command.lower()).strip()
        return value in {"sí", "si", "envíalo", "envialo", "envia", "envía", "sí envíalo", "si envialo", "hazlo", "confirmo", "dale", "adelante", "procede", "proceder", "mándalo", "mandalo"}

    @staticmethod
    def _rejection(command: str) -> bool:
        value = re.sub(r"[^a-záéíóúüñ ]", "", command.lower()).strip()
        return value in {"no", "cancela", "cancelar", "detente", "para", "parar", "no lo hagas"}

    @staticmethod
    def _needs_visual_agent(command: str) -> bool:
        text = command.lower()
        markers = (
            "dentro de", "dentro del", "en la aplicación", "en la app", "en la pagina", "en la página",
            "en la web", "en el sitio", "haz clic", "haz click", "clica", "pulsa", "presiona",
            "rellena", "escribe en", "selecciona", "busca dentro", "abre esto y", "entra y", "ve y",
            "hazlo en", "házlo en", "automatiza", "automatiza esto", "haz esto en", "clic en",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def _screen_request(command: str) -> bool:
        return command.lower().strip() in {
            "mira la pantalla", "observa la pantalla", "captura la pantalla", "analiza la pantalla",
            "qué hay en mi pantalla", "que hay en mi pantalla",
        }

    @classmethod
    def _open_prefix(cls, command: str) -> str | None:
        match = re.match(rf"^\s*(?:abre|abrir|inicia|iniciar|entra(?:r)?\s+a)\s+(?:la\s+|el\s+)?(?P<app>{cls.OPENABLE})(?=\s*(?:,|\s+y\s+|\s+para\s+|$))", command, flags=re.IGNORECASE)
        return match.group("app") if match else None

    def _run_visual_task(self, command: str) -> None:
        self._hud_state("OODA")
        self._hud_message("MISSION", command)
        if self.hud:
            try:
                self.hud.set_mission(command)
            except Exception:
                pass
        result = self.computer_agent.run(command, max_steps=12)
        self.respond(result)

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command or not self.running:
            return
        threading.Thread(target=self._process_command, args=(command,), daemon=True, name="jarvis-command").start()

    def _process_command(self, command: str) -> None:
        with self._command_lock:
            self.busy = True
            try:
                self._process_command_locked(command)
            finally:
                self.busy = False

    def _process_command_locked(self, command: str) -> None:
        lowered = command.lower().strip()
        if lowered in {"salir", "exit", "quit", "cierrate", "ciérrate", "jarvis apágate", "jarvis apagarte"}:
            self.shutdown()
            return

        if self.computer_agent.has_pending and (self._confirmation(command) or self._rejection(command)):
            self._hud_state("EJECUTANDO" if self._confirmation(command) else "VERIFICANDO")
            self.respond(self.computer_agent.confirm(self._confirmation(command)))
            return

        if lowered in {"limpiar conversación", "limpia la conversación", "olvida esta conversación"}:
            self.brain.reset_conversation()
            self.respond("Conversación limpiada.")
            return

        neural_markers = ("crea una red neuronal", "crea una red neural", "entrena una red neuronal", "haz una red neuronal", "prueba una red neuronal")
        if any(marker in lowered for marker in neural_markers):
            self._hud_state("APRENDIENDO")
            result = self.neural.create_and_train()
            response = f"Neural Lab completado. Arquitectura {result['architecture']}, accuracy {result['accuracy']:.0%}, loss {result['loss']}. Modelo guardado en {result['path']}."
            self.respond(response)
            return
        if lowered in {"estado del neural lab", "estado del aprendizaje", "qué has aprendido", "que has aprendido"}:
            self.respond(self.neural.status())
            return

        effort = self._effort(command)
        if effort:
            self.reasoning.set_effort(effort)
            self.respond(f"Esfuerzo cognitivo configurado en {effort}.")
            return

        provider = self._provider(command)
        if provider:
            try:
                selected = self.brain.set_provider(provider)
                if self.hud:
                    self.hud.update_provider()
                self.respond(f"Entendido. Ahora usaré {selected}.")
            except (ValueError, RuntimeError) as exc:
                self.respond(str(exc))
            return

        if self._screen_request(command):
            self._hud_state("OBSERVANDO")
            observation = self.tools.computer.observe()
            result = self.brain.analyze_screen(observation.image_base64, command) if observation.image_base64 else observation.note
            self.respond(result)
            return

        if self._needs_visual_agent(command):
            app = self._open_prefix(command)
            if app:
                self._hud_message("SYSTEM", f"Preflight: abriendo {app} antes de la misión visual.")
                try:
                    opened = self.tools.system.open_application(app)
                    self._hud_message("SYSTEM", str(opened))
                    time.sleep(1.0)
                except Exception as exc:
                    self.respond(f"No pude abrir {app} antes de la misión visual: {exc}")
                    return
            self._run_visual_task(command)
            return

        tool_result = self.tools.handle(command)
        if isinstance(tool_result, dict):
            if tool_result.get("provider"):
                try:
                    selected = self.brain.set_provider(str(tool_result["provider"]))
                    if self.hud:
                        self.hud.update_provider()
                    self.respond(f"Entendido. Ahora usaré {selected}.")
                except (ValueError, RuntimeError) as exc:
                    self.respond(str(exc))
                return
            if tool_result.get("send_message") == "teams":
                self.respond(self.tools.teams.send_draft())
                return
            if tool_result.get("communication") == "teams":
                educational = str(tool_result.get("educational", "False")).lower() == "true"
                action = tool_result.get("action")
                if action == "open":
                    self.respond(self.tools.teams.open(educational=educational))
                elif action == "open_contact":
                    self.respond(self.tools.teams.open_contact(str(tool_result.get("person", "")), educational=educational))
                else:
                    self.respond(str(tool_result.get("message", "Procesando Teams.")))
                return
            if tool_result.get("communication"):
                self.respond(str(tool_result.get("message", "Acción preparada.")))
                return

        if isinstance(tool_result, str):
            self.respond(tool_result)
            return

        self._hud_state("PENSANDO")
        result = self.reasoning.answer(command)
        self.respond(result)

    def respond(self, text: str) -> None:
        print(f"[JARVIS] {text}\n")
        self._hud_state("RESPONDIENDO")
        if self.hud:
            try:
                self.hud.set_response(text)
            except Exception:
                pass
        threading.Thread(target=self.voice.speak, args=(text,), daemon=True, name="jarvis-tts").start()

    def run_voice_loop(self) -> None:
        while self.running:
            try:
                if self.busy:
                    time.sleep(0.25)
                    continue
                self._hud_state("ESCUCHANDO")
                command = self.voice.listen_for_command(seconds=7)
                if command and self.running:
                    self._hud_message("TÚ", command)
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
