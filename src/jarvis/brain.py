from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

if load_dotenv:
    load_dotenv()


SYSTEM_PROMPT = """
Eres J.A.R.V.I.S., el asistente personal de un usuario de Windows.

IDENTIDAD
- Eres un único agente de IA. No crees subagentes ni delegues el razonamiento a otros modelos.
- Tu trabajo es entender la intención, planificar con seguridad y utilizar herramientas disponibles cuando corresponda.
- Habla en español si el usuario habla español.
- Sé natural, preciso y breve cuando una respuesta breve sea suficiente.

REGLAS
- Nunca afirmes haber ejecutado una acción si la herramienta no confirmó que se ejecutó.
- Si una acción necesita confirmación del usuario, solicítala antes de ejecutarla.
- No inventes archivos, programas, resultados ni información del sistema.
- Respeta la privacidad: no hagas vigilancia oculta ni registres contenido de teclado de forma encubierta.
- Si no tienes una herramienta para realizar algo, dilo claramente.
""".strip()


@dataclass
class BrainConfig:
    # Claude is the default provider. Ollama remains available as an optional local provider.
    provider: str = os.getenv("JARVIS_PROVIDER", "claude").strip().lower()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    timeout: int = int(os.getenv("JARVIS_AI_TIMEOUT", "120"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    max_history_messages: int = int(os.getenv("JARVIS_MAX_HISTORY_MESSAGES", "12"))


class JarvisBrain:
    """Único cerebro de JARVIS; Claude y Ollama son proveedores, no agentes."""

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self.conversation: list[dict[str, str]] = []
        self.session = requests.Session()
        self._claude = None

    @property
    def provider(self) -> str:
        return self.config.provider

    def _claude_client(self):
        if self._claude is not None:
            return self._claude
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            return None
        if anthropic is None:
            raise RuntimeError("Falta instalar el paquete anthropic.")
        self._claude = anthropic.Anthropic(api_key=api_key)
        return self._claude

    def claude_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY", "").strip()) and anthropic is not None

    def ollama_available(self) -> bool:
        try:
            response = self.session.get(self.config.ollama_host, timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def is_available(self) -> bool:
        if self.provider == "claude":
            return self.claude_available()
        return self.ollama_available()

    def set_provider(self, provider: str) -> str:
        provider = provider.strip().lower()
        if provider not in {"ollama", "claude"}:
            raise ValueError("Proveedor no válido. Usa ollama o claude.")
        if provider == "claude" and not self.claude_available():
            raise RuntimeError("Claude no está configurado. Añade ANTHROPIC_API_KEY al archivo .env.")
        if provider == "ollama" and not self.ollama_available():
            raise RuntimeError("Ollama no está disponible.")
        self.config.provider = provider
        return provider

    def reset_conversation(self) -> None:
        self.conversation.clear()

    def _ask_ollama(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.config.ollama_keep_alive,
            "options": {"temperature": 0.2},
        }
        response = self.session.post(
            f"{self.config.ollama_host}/api/chat",
            json=payload,
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return str(data.get("message", {}).get("content", "")).strip()

    def _ask_claude(self, messages: list[dict[str, str]]) -> str:
        client = self._claude_client()
        if client is None:
            raise RuntimeError("Claude no está configurado.")
        user_messages = [m for m in messages if m["role"] != "system"]
        response = client.messages.create(
            model=self.config.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=user_messages,
        )
        texts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "\n".join(texts).strip()

    def ask(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "No recibí ninguna orden."

        self.conversation.append({"role": "user", "content": user_message})
        if len(self.conversation) > self.config.max_history_messages:
            self.conversation = self.conversation[-self.config.max_history_messages :]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.conversation]

        try:
            if self.provider == "claude":
                answer = self._ask_claude(messages)
            else:
                if not self.ollama_available():
                    return "Ollama no está disponible. Inícialo o cambia el proveedor a Claude."
                answer = self._ask_ollama(messages)

            if not answer:
                answer = "El proveedor no devolvió una respuesta válida."
            self.conversation.append({"role": "assistant", "content": answer})
            if len(self.conversation) > self.config.max_history_messages:
                self.conversation = self.conversation[-self.config.max_history_messages :]
            return answer
        except requests.Timeout:
            return "La respuesta de Ollama tardó demasiado."
        except requests.RequestException as exc:
            print(f"[BRAIN] Error Ollama: {exc}")
            return "Se produjo un error al comunicarme con Ollama."
        except Exception as exc:
            print(f"[BRAIN] Error: {exc}")
            return "Se produjo un error al procesar la solicitud."
