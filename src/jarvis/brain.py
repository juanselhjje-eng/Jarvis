from __future__ import annotations

import base64
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
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None

if load_dotenv:
    load_dotenv()


SYSTEM_PROMPT = """
Eres J.A.R.V.I.S., el asistente personal de un usuario de Windows.

IDENTIDAD
- Eres un único agente de IA. No crees subagentes.
- Entiende intención, planifica tareas y usa herramientas deterministas cuando estén disponibles.
- Habla en español si el usuario habla español.
- Sé natural, preciso y breve cuando una respuesta breve sea suficiente.

PLANIFICACIÓN Y CONTROL
- Para tareas complejas usa: objetivo -> criterios -> herramientas -> ejecución -> verificación -> resultado.
- No inventes herramientas ni afirmes acciones que no fueron confirmadas por una herramienta.
- Para acciones visibles de escritorio, la pantalla observada es la fuente de verdad.
- No ejecutes shell arbitrario generado por texto del usuario.

MEMORIA
- Usa memoria local cuando exista contexto útil. No inventes recuerdos.
- Nunca guardes contraseñas, claves API, cookies o credenciales.

ACCIONES EXTERNAS
- Antes de enviar mensajes, correos, formularios o solicitudes a terceros, prepara el contenido y pide confirmación.
- Una confirmación autoriza únicamente la acción concreta mostrada.

VISIÓN
- Cuando recibas una captura, describe únicamente elementos visibles y relevantes para la tarea.
- No inventes texto, botones, contactos ni estados que no sean visibles.
""".strip()


@dataclass
class BrainConfig:
    provider: str = os.getenv("JARVIS_PROVIDER", "gemini").strip().lower()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    timeout: int = int(os.getenv("JARVIS_AI_TIMEOUT", "120"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    max_history_messages: int = int(os.getenv("JARVIS_MAX_HISTORY_MESSAGES", "12"))


class JarvisBrain:
    """Único cerebro de JARVIS; Gemini y Ollama son proveedores, no agentes."""

    MODEL_PREFERENCE = (
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
    )

    def __init__(self, config: BrainConfig | None = None) -> None:
        self.config = config or BrainConfig()
        self.conversation: list[dict[str, str]] = []
        self.session = requests.Session()
        self._gemini = None
        self._gemini_model_checked = False

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

    def _select_working_gemini_model(self) -> str:
        client = self._gemini_client()
        if client is None:
            raise RuntimeError("Gemini no está configurado.")
        if self._gemini_model_checked:
            return self.config.gemini_model

        configured = self.config.gemini_model
        try:
            available: list[str] = []
            for model in client.models.list():
                name = str(getattr(model, "name", ""))
                actions = getattr(model, "supported_actions", []) or []
                short_name = name.removeprefix("models/")
                if "generateContent" in actions and short_name:
                    available.append(short_name)

            if configured in available:
                selected = configured
            else:
                selected = next((candidate for candidate in self.MODEL_PREFERENCE if candidate in available), "")
                if not selected:
                    raise RuntimeError("La API de Gemini no expone ningún modelo compatible con generateContent para esta clave.")
                print(f"[BRAIN] Modelo Gemini configurado no disponible: {configured}. Usando: {selected}.")
                self.config.gemini_model = selected
            self._gemini_model_checked = True
            return selected
        except Exception as exc:
            print(f"[BRAIN] No pude consultar la lista de modelos Gemini: {exc}")
            self._gemini_model_checked = True
            return configured

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
        model = self._select_working_gemini_model()
        prompt = f"{SYSTEM_PROMPT}\n\nHISTORIAL:\n{self._history_text()}"
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )
        return str(getattr(response, "text", "") or "").strip()

    def analyze_screen(self, image_base64: str, task: str = "Analiza la pantalla y dime qué elementos visibles son relevantes para mi orden.") -> str:
        """Analiza una captura puntual con Gemini; nunca inicia vigilancia continua."""
        if not image_base64:
            return "No recibí una captura válida."
        client = self._gemini_client()
        if client is None or types is None:
            return "La visión requiere Gemini configurado."
        try:
            model = self._select_working_gemini_model()
            image_bytes = base64.b64decode(image_base64)
            contents = [
                types.Part.from_text(text=task),
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ]
            response = client.models.generate_content(model=model, contents=contents)
            return str(getattr(response, "text", "") or "No pude interpretar la captura.").strip()
        except Exception as exc:
            return f"No pude analizar la pantalla con Gemini: {exc}"

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
                        return f"Gemini no pudo responder y Ollama tampoco está disponible. Detalle: {exc}"
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
