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
    from google import genai
except ImportError:  # pragma: no cover
    genai = None

if load_dotenv:
    load_dotenv()


SYSTEM_PROMPT = """
Eres J.A.R.V.I.S., el asistente personal de un usuario de Windows.

IDENTIDAD
- Eres un único agente de IA. No crees subagentes ni delegues el razonamiento a otros modelos.
- Entiende la intención, divide tareas complejas en pasos y utiliza las herramientas disponibles cuando corresponda.
- Habla en español si el usuario habla español.
- Sé natural, preciso y breve cuando una respuesta breve sea suficiente.

PLANIFICACIÓN
- Para una tarea compleja, piensa en una secuencia: objetivo -> criterios -> herramientas -> ejecución -> verificación -> resultado.
- No inventes una herramienta. Si una capacidad todavía no está implementada, dilo y continúa con las partes que sí puedas realizar.
- Si una tarea requiere navegar, buscar, filtrar resultados y después contactar a alguien, trata cada fase como un paso independiente y verifica el resultado antes de continuar.
- No afirmes que una página, contacto, cita o resultado fue encontrado hasta que exista evidencia real.

MEMORIA
- Puedes recibir contexto de memoria local. Úsalo para mantener preferencias y proyectos entre sesiones.
- No inventes recuerdos ni guardes secretos, contraseñas, claves API o credenciales.

CONTROL DEL EQUIPO
- Puedes trabajar con herramientas locales autorizadas para abrir aplicaciones, consultar el sistema y realizar acciones visibles.
- Nunca ejecutes comandos de shell arbitrarios generados por texto del usuario.
- Nunca hagas vigilancia oculta, keylogging, robo de cookies, robo de credenciales ni persistencia encubierta.

ACCIONES EXTERNAS
- Antes de enviar mensajes, correos, formularios, solicitudes o citas a terceros, muestra lo que se va a enviar y pide confirmación.
- Una confirmación solo autoriza la acción concreta que se mostró; no autoriza otras acciones.

VERIFICACIÓN
- Nunca afirmes haber ejecutado una acción si la herramienta no confirmó que se ejecutó.
- No inventes archivos, programas, resultados ni información del sistema.
""".strip()


@dataclass
class BrainConfig:
    provider: str = os.getenv("JARVIS_PROVIDER", "gemini").strip().lower()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    timeout: int = int(os.getenv("JARVIS_AI_TIMEOUT", "120"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    max_history_messages: int = int(os.getenv("JARVIS_MAX_HISTORY_MESSAGES", "12"))


class JarvisBrain:
    """Único cerebro de JARVIS; Gemini y Ollama son proveedores, no agentes."""

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self.conversation: list[dict[str, str]] = []
        self.session = requests.Session()
        self._gemini = None

    @property
    def provider(self) -> str:
        return self.config.provider

    def _gemini_client(self):
        if self._gemini is not None:
            return self._gemini
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        if genai is None:
            raise RuntimeError("Falta instalar el paquete google-genai.")
        self._gemini = genai.Client(api_key=api_key)
        return self._gemini

    def gemini_available(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY", "").strip()) and genai is not None

    def ollama_available(self) -> bool:
        try:
            response = self.session.get(self.config.ollama_host, timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def is_available(self) -> bool:
        if self.provider == "gemini":
            return self.gemini_available() or self.ollama_available()
        return self.ollama_available()

    def set_provider(self, provider: str) -> str:
        provider = provider.strip().lower()
        if provider not in {"ollama", "gemini"}:
            raise ValueError("Proveedor no válido. Usa gemini u ollama.")
        if provider == "gemini" and not self.gemini_available():
            raise RuntimeError("Gemini no está configurado. Añade GEMINI_API_KEY al archivo .env.")
        if provider == "ollama" and not self.ollama_available():
            raise RuntimeError("Ollama no está disponible.")
        self.config.provider = provider
        return provider

    def reset_conversation(self) -> None:
        self.conversation.clear()

    def _history_text(self) -> str:
        return "\n".join(
            f"{'Usuario' if m['role'] == 'user' else 'J.A.R.V.I.S.'}: {m['content']}"
            for m in self.conversation
        )

    def _ask_gemini(self) -> str:
        client = self._gemini_client()
        if client is None:
            raise RuntimeError("Gemini no está configurado.")
        prompt = f"{SYSTEM_PROMPT}\n\nHISTORIAL:\n{self._history_text()}"
        response = client.models.generate_content(
            model=self.config.gemini_model,
            contents=prompt,
        )
        return str(getattr(response, "text", "") or "").strip()

    def _ask_ollama(self) -> str:
        payload = {
            "model": self.config.ollama_model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *self.conversation],
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

    def ask(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "No recibí ninguna orden."

        self.conversation.append({"role": "user", "content": user_message})
        self.conversation = self.conversation[-self.config.max_history_messages :]

        try:
            if self.provider == "gemini":
                try:
                    answer = self._ask_gemini()
                except Exception as exc:
                    print(f"[BRAIN] Gemini no pudo responder: {exc}")
                    if self.ollama_available():
                        print("[BRAIN] Fallback automático: Ollama local.")
                        answer = self._ask_ollama()
                    else:
                        return "Gemini no pudo responder y Ollama tampoco está disponible."
            else:
                if not self.ollama_available():
                    return "Ollama no está disponible. Inícialo o cambia el proveedor a Gemini."
                answer = self._ask_ollama()

            if not answer:
                answer = "El proveedor no devolvió una respuesta válida."
            self.conversation.append({"role": "assistant", "content": answer})
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
