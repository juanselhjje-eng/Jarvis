from __future__ import annotations

import threading
import time

from brain import JarvisBrain
from command_router import CommandRouter
from voice_engine import VoiceEngine


class Jarvis:
    """Runtime de JARVIS: un solo cerebro y herramientas deterministas."""

    def __init__(self) -> None:
        self.running = True
        self.brain = JarvisBrain()
        self.tools = CommandRouter()
        self.voice = VoiceEngine()
        self._command_lock = threading.Lock()

    def start(self) -> None:
        print("=" * 64)
        print("                 J.A.R.V.I.S. LOCAL")
        print("=" * 64)
        print(f"[SYSTEM] Proveedor: {self.brain.provider}")
        print(f"[SYSTEM] Ollama: {self.brain.config.ollama_model}")
        print(f"[SYSTEM] Claude: {self.brain.config.claude_model}")

        if not self.brain.is_available():
            message = "El proveedor configurado no está disponible. Revisa Ollama o Claude."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return

        self.voice.speak("Sistemas principales iniciados. Te escucho.")
        print("[SYSTEM] Modo conversación activo. Di 'Jarvis' o 'Viernes' seguido de tu orden.")
        print("[SYSTEM] Ctrl+C para detener.")
        self.run_voice_loop()

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command:
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
            tool_result = self.tools.handle(command)

            if isinstance(tool_result, dict):
                if tool_result.get("provider"):
                    try:
                        provider = self.brain.set_provider(str(tool_result["provider"]))
                        self.respond(f"Entendido. Ahora usaré {provider}.")
                    except (ValueError, RuntimeError) as exc:
                        self.respond(str(exc))
                    return

                if tool_result.get("communication"):
                    message = str(tool_result.get("message", "Abrí la aplicación."))
                    self.respond(message)
                    print("[ACTION] No envío mensajes automáticamente: el envío necesita confirmación explícita.")
                    return

            if isinstance(tool_result, str):
                self.respond(tool_result)
                return

            answer = self.brain.ask(command)
            self.respond(answer)

    def respond(self, text: str) -> None:
        print(f"[JARVIS] {text}\n")
        self.voice.speak(text)

    def run_voice_loop(self) -> None:
        while self.running:
            try:
                command = self.voice.listen_for_command(seconds=7)
                if command:
                    self.process_command(command)
            except KeyboardInterrupt:
                self.shutdown()
            except Exception as exc:
                print(f"[VOICE] Error: {exc}")
                self.voice.speak("Tuve un problema con el sistema de voz. Intentaré de nuevo.")
                time.sleep(1)

    def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        self.voice.speak("Sistemas apagados.")
        self.voice.shutdown()
        print("[SYSTEM] JARVIS detenido.")


def main() -> int:
    jarvis = Jarvis()
    try:
        jarvis.start()
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
