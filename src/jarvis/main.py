from __future__ import annotations

import threading
import time

from .brain import JarvisBrain
from .command_router import CommandRouter
from .evidence import EvidenceBoard
from .execution import ExecutionTracker, TaskState
from .hud_futuristic import JarvisHUD
from .voice_engine import VoiceEngine


class Jarvis:
    """Runtime de JARVIS: un solo cerebro, herramientas, misión y verificación."""

    def __init__(self) -> None:
        self.running = True
        self.brain = JarvisBrain()
        self.tools = CommandRouter()
        self.execution = ExecutionTracker()
        self.evidence = EvidenceBoard()
        self.voice = VoiceEngine()
        self.hud: JarvisHUD | None = None
        self._command_lock = threading.Lock()

    def start(self) -> None:
        if not self.brain.is_available():
            message = "El proveedor configurado no está disponible. Revisa Ollama o Claude."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return
        self.hud = JarvisHUD(
            brain=self.brain,
            voice=self.voice,
            process_command=self.process_command,
            shutdown=self.shutdown,
            evidence=self.evidence,
            execution=self.execution,
        )
        self.hud.add_message("SYSTEM", f"MISSION CONTROL ONLINE. Cerebro: {self.brain.provider.upper()}. Voz, texto, memoria y herramientas activas.")
        threading.Thread(target=self.run_voice_loop, daemon=True, name="jarvis-voice-loop").start()
        threading.Thread(target=self.voice.speak, args=("Mission Control iniciado. Te escucho.",), daemon=True).start()
        self.hud.run()

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command or not self.running:
            return
        lowered = command.lower().strip()
        if lowered in {"salir", "exit", "quit", "jarvis apágate", "jarvis apagarte"}:
            self.shutdown()
            return
        if lowered in {"limpiar conversación", "limpia la conversación", "borra la conversación", "olvida esta conversación"}:
            self.brain.reset_conversation()
            self.respond("Conversación limpiada.")
            return

        with self._command_lock:
            print(f"[USER] {command}")
            self.execution.start(command)
            self.execution.set_state(TaskState.INTENT)
            if self.hud:
                self.hud.set_state("ANALYZING COMMAND")

            tool_result = self.tools.handle(command)

            if isinstance(tool_result, dict):
                if tool_result.get("provider"):
                    try:
                        self.execution.set_state(TaskState.EXECUTING)
                        provider = self.brain.set_provider(str(tool_result["provider"]))
                        response = f"Entendido. Ahora usaré {provider}."
                        self.execution.finish(response, verified=True)
                        self.respond(response)
                    except (ValueError, RuntimeError) as exc:
                        self.execution.finish(str(exc), verified=False, success=False)
                        self.respond(str(exc))
                    return

                if tool_result.get("send_message") == "teams":
                    self.execution.set_state(TaskState.EXECUTING)
                    response = self.tools.teams.send_draft()
                    self.execution.set_state(TaskState.VERIFYING)
                    verified = "enviado" in response.lower() and "no pude" not in response.lower()
                    self.execution.finish(response, verified=verified, success=verified)
                    self.respond(response)
                    return

                if tool_result.get("communication") == "teams":
                    educational = tool_result.get("educational") == "True"
                    action = tool_result.get("action")
                    self.execution.set_state(TaskState.EXECUTING)
                    if action == "open":
                        response = self.tools.teams.open(educational)
                    elif action == "open_contact":
                        response = self.tools.teams.open_contact(tool_result.get("person", ""), educational)
                    else:
                        response = str(tool_result.get("message", "Procesando Teams."))
                    self.execution.set_state(TaskState.VERIFYING)
                    verified = bool(response.strip()) and "no pude" not in response.lower()
                    self.execution.finish(response, verified=verified, success=verified)
                    self.respond(response)
                    return

                if tool_result.get("communication"):
                    response = str(tool_result.get("message", "Abrí la aplicación."))
                    self.execution.finish(response, verified=True)
                    self.respond(response)
                    return

            if isinstance(tool_result, str):
                self.execution.set_state(TaskState.VERIFYING)
                response = tool_result
                verified = not any(marker in response.lower() for marker in ("no pude", "error", "falló", "fallo", "no disponible"))
                self.execution.finish(response, verified=verified, success=verified)
                self.respond(response)
                return

            self.execution.set_state(TaskState.PLANNING)
            if self.hud:
                self.hud.set_state("THINKING")
            answer = self.brain.ask(command)
            self.execution.set_state(TaskState.VERIFYING)
            self.execution.finish(answer, verified=True)
            self.respond(answer)

    def respond(self, text: str) -> None:
        print(f"[JARVIS] {text}\n")
        if self.hud:
            self.hud.set_response(text)
        threading.Thread(target=self.voice.speak, args=(text,), daemon=True, name="jarvis-tts").start()

    def run_voice_loop(self) -> None:
        while self.running:
            try:
                if self.voice.is_speaking:
                    time.sleep(0.25)
                    continue
                if self.hud:
                    self.hud.set_state("LISTENING")
                command = self.voice.listen_for_command(seconds=5)
                if command:
                    if self.hud:
                        self.hud.add_message("USER", command)
                        self.hud.set_state("PROCESSING COMMAND")
                    self.process_command(command)
                elif self.hud:
                    self.hud.set_state("SYSTEM READY")
            except KeyboardInterrupt:
                self.shutdown()
                return
            except Exception as exc:
                print(f"[VOICE] Error: {exc}")
                if self.hud:
                    self.hud.add_message("VOICE", f"Error: {exc}")
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
