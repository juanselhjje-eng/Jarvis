from __future__ import annotations

import sys
import threading

from brain import JarvisBrain
from voice_engine import VoiceEngine


class Jarvis:
    """Main orchestrator for the local J.A.R.V.I.S. assistant."""

    def __init__(self) -> None:
        self.running = True
        self.brain = JarvisBrain()
        self.voice = VoiceEngine()
        self._command_lock = threading.Lock()

    def start(self) -> None:
        print("=" * 64)
        print("                 J.A.R.V.I.S. LOCAL")
        print("=" * 64)
        print(f"[SYSTEM] Ollama: {self.brain.host}")
        print(f"[SYSTEM] Modelo: {self.brain.model}")

        if not self.brain.is_available():
            message = "Ollama no está disponible. Inicia Ollama y vuelve a ejecutar JARVIS."
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return

        self.voice.speak("Sistemas principales iniciados.")
        print("[SYSTEM] Listo. Escribe una orden o usa el modo de voz.")
        print("[SYSTEM] Comandos: /voz, /limpiar, /salir")
        self.run_console()

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command:
            return

        lowered = command.lower()
        if lowered in {"salir", "exit", "quit", "/salir"}:
            self.shutdown()
            return

        if lowered in {"/limpiar", "limpiar conversación"}:
            self.brain.reset_conversation()
            self.voice.speak("Conversación limpiada.")
            print("[SYSTEM] Historial eliminado.")
            return

        if lowered in {"/voz", "voz", "modo voz"}:
            self.run_voice_once()
            return

        with self._command_lock:
            print(f"[USER] {command}")
            answer = self.brain.ask(command)
            print(f"[JARVIS] {answer}\n")
            # Regla de salida: toda respuesta principal también se pronuncia.
            self.voice.speak(answer)

    def run_console(self) -> None:
        while self.running:
            try:
                command = input("Tú > ")
                self.process_command(command)
            except (KeyboardInterrupt, EOFError):
                self.shutdown()
            except Exception as exc:
                print(f"[SYSTEM] Error: {exc}")
                self.voice.speak("Se produjo un error al procesar la orden.")

    def run_voice_once(self) -> None:
        try:
            command = self.voice.listen_for_command(seconds=7)
            if command:
                self.process_command(command)
            else:
                print("[VOICE] No se detectó una orden con Jarvis o Viernes.")
        except Exception as exc:
            print(f"[VOICE] Error: {exc}")
            self.voice.speak("No pude procesar la entrada de voz.")

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
