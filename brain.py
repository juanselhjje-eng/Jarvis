from __future__ import annotations

import requests


OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2"
OLLAMA_TIMEOUT = 120

SYSTEM_PROMPT = """
Eres J.A.R.V.I.S., un asistente virtual local para Windows.
Responde en español si el usuario habla español.
Sé preciso y conciso. No inventes acciones realizadas en el sistema.
En esta fase solo conversas mediante Ollama; las herramientas del sistema
se incorporarán en módulos independientes en fases posteriores.
""".strip()


class JarvisBrain:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.conversation: list[dict[str, str]] = []
        self.session = requests.Session()

    def is_available(self) -> bool:
        try:
            response = self.session.get(self.host, timeout=5)
            return response.ok
        except requests.RequestException:
            return False

    def reset_conversation(self) -> None:
        self.conversation.clear()

    def ask(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "No recibí ninguna orden."

        if not self.is_available():
            return "No puedo conectarme con Ollama. Comprueba que Ollama esté ejecutándose."

        self.conversation.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.conversation]

        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
            if not answer:
                answer = "Ollama no devolvió una respuesta válida."
            self.conversation.append({"role": "assistant", "content": answer})
            return answer
        except requests.Timeout:
            return "La respuesta de Ollama tardó demasiado."
        except requests.RequestException as exc:
            print(f"[BRAIN] Error Ollama: {exc}")
            return "Se produjo un error al comunicarme con el cerebro local."
        except (ValueError, TypeError):
            return "Ollama devolvió una respuesta que no pude interpretar."
