from __future__ import annotations

import threading

from brain import JarvisBrain
from command_router import CommandRouter
from voice_engine import VoiceEngine


class Jarvis:
    """Runtime principal: un solo cerebro + herramientas deterministas."""

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
            message = (
                "El proveedor configurado no está disponible. "
                "Revisa Ollama o la configuración de Claude."
            )
            print(f"[ERROR] {message}")
            self.voice.speak(message)
            return

        self.voice.speak("Sistemas principales iniciados.")
        print("[SYSTEM] Listo. Háblame o escribe normalmente. Por ejemplo: Jarvis, abre Google.")
        print("[SYSTEM] Voz: escribe 'voz' para escuchar durante unos segundos.")
        self.run_console()

    def process_command(self, command: str) -> None:
        command = command.strip()
        if not command:
            return

        lowered = command.lower().strip()
        if lowered in {"salir", "exit", "quit", "/salir", "jarvis apágate", "jarvis apagarte"}:
            self.shutdown()
            return

        if lowered in {
            "/limpiar",
            "limpiar conversación",
            "limpia la conversación",
            "borra la conversación",
            "olvida esta conversación",
        }:
            self.brain.reset_conversation()
            self.voice.speak("Conversación limpiada.")
            print("[SYSTEM] Historial eliminado.")
            return

        if lowered in {"/voz", "voz", "modo voz", "escúchame", "escuchame"}:
            self.run_voice_once()
            return

        with self._command_lock:
            print(f"[USER] {command}")

            # El router solo detecta herramientas deterministas; no es otro agente.
            tool_result = self.tools.handle(command)

            if isinstance(tool_result, dict) and tool_result.get("provider"):
                try:
                    provider = self.brain.set_provider(str(tool_result["provider"]))
                    answer = f"Entendido. Ahora usaré {provider}."
                except (ValueError, RuntimeError) as exc:
                    answer = str(exc)
                print(f"[JARVIS] {answer}\n")
                self.voice.speak(answer)
                return

            if isinstance(tool_result, str):
                answer = tool_result
            else:
                answer = self.brain.ask(command)

            print(f"[JARVIS] {answer}\n")
            self.voice.speak(answer)

    def run_console(self) -> None:
        while self.running:
            try:
                self.process_command(input("Tú > "))
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
