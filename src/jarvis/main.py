from __future__ import annotations

import threading
import time

from .brain import JarvisBrain
from .command_router import CommandRouter
from .evidence import EvidenceBoard
from .execution import ExecutionTracker, TaskState
from .hud_hrz import JarvisHRZHUD
from .task_planner import TaskPlanner
from .voice_engine import VoiceEngine


class Jarvis:
    """Runtime de JARVIS: un solo cerebro, herramientas, misión, planificación y verificación."""

    def __init__(self) -> None:
        self.running = True
        self.brain = JarvisBrain()
        self.tools = CommandRouter()
        self.planner = TaskPlanner()
        self.execution = ExecutionTracker()
        self.evidence = EvidenceBoard()
        self.voice = VoiceEngine()
        self.hud: JarvisHRZHUD | None = None
        self._command_lock = threading.Lock()
        self._voice_command_lock = threading.Lock()

    def start(self) -> None:
        if not self.brain.is_available():
            message = "El cerebro Gemini no está configurado y Ollama no está disponible."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return

        self.hud = JarvisHRZHUD(
            brain=self.brain,
            voice=self.voice,
            process_command=self.process_command,
            shutdown=self.shutdown,
            evidence=self.evidence,
            execution=self.execution,
        )
        self.hud.add_message("SYSTEM", f"JARVIS-HRZ ONLINE. Cerebro: {self.brain.provider.upper()}. Voz, memoria, planificación, tareas, recordatorios y control activos.")

        self.hud.set_state("HABLANDO")
        self.voice.speak("JARVIS-HRZ iniciado. Te escucho.")
        if not self.running:
            return
        self.hud.set_state("ESCUCHANDO")
        threading.Thread(target=self.run_voice_loop, daemon=True, name="jarvis-voice-loop").start()
        self.hud.run()

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
            self.execution.start(command)
            self.execution.set_state(TaskState.INTENT)
            if self.hud:
                self.hud.set_state("ANALIZANDO")

            investigation = lowered.startswith(("investiga ", "investiga:", "investigar "))
            if investigation:
                self.evidence.start(title=command, query=command)
                self.evidence.update(self.evidence.latest(), status="RESEARCHING")

            complex_task = len(command.split()) >= 10 or any(
                marker in lowered for marker in ("paso a paso", "encárgate de", "encargate de", "haz todo", "busca y", "revisa y")
            )
            if complex_task:
                plan = self.planner.plan(command)
                plan_text = "PLAN DE MISIÓN\n" + plan.summary()
                print(f"[PLAN]\n{plan_text}\n")
                if self.hud:
                    self.hud.add_message("PLAN", plan_text)
                self.execution.set_state(TaskState.PLANNING)

            tool_result = self.tools.handle(command)

            if isinstance(tool_result, dict):
                if tool_result.get("provider"):
                    try:
                        self.execution.set_state(TaskState.EXECUTING)
                        provider = self.brain.set_provider(str(tool_result["provider"]))
                        if self.hud:
                            self.hud.update_provider()
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
                if investigation and self.evidence.latest():
                    status = "COLLECTING" if verified else "FAILED"
                    self.evidence.update(self.evidence.latest(), status=status, findings=[response])
                self.execution.finish(response, verified=verified)
                self.respond(response)
                return

            self.execution.set_state(TaskState.PLANNING)
            if self.hud:
                self.hud.set_state("PENSANDO")
            answer = self.brain.ask(command)
            self.execution.set_state(TaskState.VERIFYING)
            if investigation and self.evidence.latest():
                self.evidence.update(self.evidence.latest(), status="ANALYSIS", findings=[answer], conclusion=answer)
            self.execution.finish(answer, verified=True)
            self.respond(answer)

    def respond(self, text: str) -> None:
        print(f"[JARVIS] {text}\n")
        if self.hud:
            self.hud.set_response(text)
        threading.Thread(target=self.voice.speak, args=(text,), daemon=True, name="jarvis-tts").start()

    def run_voice_loop(self) -> None:
        while self.running:
            if not self._voice_command_lock.acquire(blocking=False):
                time.sleep(0.15)
                continue
            try:
                if self.voice.is_speaking:
                    time.sleep(0.25)
                    continue
                if self.hud:
                    self.hud.set_state("ESCUCHANDO")
                command = self.voice.listen_for_command(seconds=5)
                if command and self.running:
                    if self.hud:
                        self.hud.add_message("TÚ", command)
                        self.hud.set_state("PROCESANDO")
                    self.process_command(command)
                elif self.hud and self.running:
                    self.hud.set_state("ESCUCHANDO")
            except KeyboardInterrupt:
                self.shutdown()
                return
            except Exception as exc:
                print(f"[VOICE] Error: {exc}")
                if self.hud:
                    self.hud.show_alert(f"Error de reconocimiento: {exc}", "#ed6375")
                    self.hud.set_state("ESCUCHANDO")
                time.sleep(1)
            finally:
                self._voice_command_lock.release()

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
