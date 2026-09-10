from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .memory import LocalMemory

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
    from google.genai import types
    _GENAI_IMPORT_ERROR = ""
except ImportError as exc:
    genai = None
    types = None
    _GENAI_IMPORT_ERROR = str(exc)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"
if load_dotenv:
    load_dotenv(dotenv_path=_ENV_FILE, override=False)

SYSTEM_PROMPT = """
Eres J.A.R.V.I.S., un único agente personal para Windows.

No eres solamente un chatbot. Debes entender la intención del usuario y, cuando corresponde,
usar herramientas deterministas o controlar una aplicación/web de forma visible. Nunca afirmes
haber realizado una acción si no existe un resultado verificable.

Para tareas complejas trabaja como: objetivo -> plan -> herramienta -> acción -> nueva observación
-> corrección -> verificación. La pantalla observada y el resultado real de una herramienta son
la fuente de verdad. No inventes botones, páginas, contactos ni estados.

Cuando el usuario diga "haz esto en esta web", "haz esto en esta aplicación", "entra", "pulsa",
"escribe", "selecciona", "busca dentro" o describa una secuencia de interfaz, la tarea debe
tratarse como una misión de Computer Use y ejecutarse mediante la pantalla visible, no como una
simple respuesta de texto.

APRENDIZAJE: usa la memoria local proporcionada como contexto. Aprende preferencias, instrucciones
recurrentes y lecciones de tareas anteriores. Si el usuario corrige una forma de trabajar, esa
corrección puede convertirse en una lección persistente. No inventes recuerdos.

ACCIONES EXTERNAS: antes de enviar mensajes, correos, formularios, publicaciones, compras o
cambios destructivos, prepara la acción y exige confirmación explícita del usuario.

VISIÓN: las capturas son puntuales y están ligadas a la misión solicitada. No hagas vigilancia
continua ni captures credenciales, contraseñas, cookies, tokens o claves API.

HABLA EN ESPAÑOL cuando el usuario hable español.
""".strip()

@dataclass
class BrainConfig:
    provider: str = os.getenv("JARVIS_PROVIDER", "gemini").strip().lower()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    timeout: int = int(os.getenv("JARVIS_AI_TIMEOUT", "120"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    max_history_messages: int = int(os.getenv("JARVIS_MAX_HISTORY_MESSAGES", "12"))
    max_memory_items: int = int(os.getenv("JARVIS_MAX_MEMORY_ITEMS", "8"))

class JarvisBrain:
    """Un solo cerebro con Gemini primario, Ollama de respaldo y memoria persistente local."""

    MODEL_PREFERENCE = (
        "gemini-3.6-flash", "gemini-3.6-flash-lite", "gemini-3.5-flash",
        "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite",
    )

    def __init__(self, config: BrainConfig | None = None, memory: LocalMemory | None = None) -> None:
        self.config = config or BrainConfig()
        self.memory = memory or LocalMemory()
        self.conversation: list[dict[str, str]] = []
        self.session = requests.Session()
        self._gemini = None
        self._gemini_model_checked = False

    @property
    def provider(self) -> str:
        return self.config.provider

    def _reload_environment(self) -> None:
        if load_dotenv:
            load_dotenv(dotenv_path=_ENV_FILE, override=False)

    def _gemini_client(self):
        self._reload_environment()
        if self._gemini is not None:
            return self._gemini
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(f"GEMINI_API_KEY no fue cargada desde {_ENV_FILE}. Revisa que exista .env y que la variable tenga un valor.")
        if genai is None:
            detail = f" Detalle de importación: {_GENAI_IMPORT_ERROR}" if _GENAI_IMPORT_ERROR else ""
            raise RuntimeError(f"google-genai no está disponible en este Python.{detail}")
        self._gemini = genai.Client(api_key=api_key)
        return self._gemini

    def _select_working_gemini_model(self) -> str:
        client = self._gemini_client()
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
                    raise RuntimeError("La clave Gemini no expone un modelo compatible con generateContent.")
                print(f"[BRAIN] {configured} no está disponible. Seleccionado: {selected}.")
            self.config.gemini_model = selected
            self._gemini_model_checked = True
            return selected
        except Exception as exc:
            print(f"[BRAIN] No pude consultar modelos Gemini: {exc}")
            self._gemini_model_checked = True
            return configured

    def gemini_available(self) -> bool:
        self._reload_environment()
        return bool(os.getenv("GEMINI_API_KEY", "").strip()) and genai is not None

    def gemini_diagnostic(self) -> str:
        self._reload_environment()
        key = os.getenv("GEMINI_API_KEY", "").strip()
        env_status = "encontrado" if _ENV_FILE.is_file() else "NO encontrado"
        python_status = f"Python: {os.sys.executable}"
        if not key:
            return f"Gemini: OFFLINE | .env: {env_status} ({_ENV_FILE}) | GEMINI_API_KEY: NO detectada | {python_status}"
        if genai is None:
            return f"Gemini: OFFLINE | .env: {env_status} | GEMINI_API_KEY: detectada ({len(key)} caracteres) | google-genai: NO disponible | {_GENAI_IMPORT_ERROR} | {python_status}"
        return f"Gemini: CONFIGURADO | .env: {env_status} | GEMINI_API_KEY: detectada ({len(key)} caracteres) | google-genai: disponible | modelo solicitado: {self.config.gemini_model} | {python_status}"

    def ollama_available(self) -> bool:
        try:
            response = self.session.get(self.config.ollama_host, timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def is_available(self) -> bool:
        return (self.gemini_available() or self.ollama_available()) if self.provider == "gemini" else self.ollama_available()

    def set_provider(self, provider: str) -> str:
        provider = provider.strip().lower()
        if provider not in {"ollama", "gemini"}:
            raise ValueError("Proveedor no válido. Usa gemini u ollama.")
        if provider == "gemini" and not self.gemini_available():
            raise RuntimeError(self.gemini_diagnostic())
        if provider == "ollama" and not self.ollama_available():
            raise RuntimeError("Ollama no está disponible.")
        self.config.provider = provider
        return provider

    def reset_conversation(self) -> None:
        self.conversation.clear()

    def remember(self, text: str, category: str = "fact") -> None:
        self.memory.remember(text, category=category)

    def learn(self, lesson: str, context: str = "") -> None:
        self.memory.learn(lesson, context=context)

    def memory_summary(self) -> str:
        return self.memory.summary()

    def _history_text(self) -> str:
        return "\n".join(f"{'Usuario' if m['role'] == 'user' else 'J.A.R.V.I.S.'}: {m['content']}" for m in self.conversation)

    def _context(self, request: str = "") -> str:
        recalled = self.memory.recall(request, limit=self.config.max_memory_items)
        return recalled or "Sin recuerdos relevantes para esta solicitud."

    def _ask_gemini(self) -> str:
        client = self._gemini_client()
        model = self._select_working_gemini_model()
        response = client.models.generate_content(
            model=model,
            contents=f"{SYSTEM_PROMPT}\n\nMEMORIA RELEVANTE:\n{self._context(self.conversation[-1]['content'] if self.conversation else '')}\n\nHISTORIAL:\n{self._history_text()}",
        )
        return str(getattr(response, "text", "") or "").strip()

    def analyze_screen(self, image_base64: str, task: str = "Analiza la pantalla.") -> str:
        if not image_base64:
            return "No recibí una captura válida."
        try:
            client = self._gemini_client()
            if types is None:
                return "La visión de Gemini no está disponible en este entorno."
            model = self._select_working_gemini_model()
            image_bytes = base64.b64decode(image_base64)
            prompt = f"{SYSTEM_PROMPT}\n\nMEMORIA RELEVANTE:\n{self._context(task)}\n\nOBJETIVO VISUAL:\n{task}"
            response = client.models.generate_content(
                model=model,
                contents=[types.Part.from_text(text=prompt), types.Part.from_bytes(data=image_bytes, mime_type="image/png")],
            )
            return str(getattr(response, "text", "") or "No pude interpretar la captura.").strip()
        except Exception as exc:
            return f"No pude analizar la pantalla con Gemini: {exc}"

    def _ask_ollama(self) -> str:
        memory = self._context(self.conversation[-1]["content"] if self.conversation else "")
        payload = {
            "model": self.config.ollama_model,
            "messages": [
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nMEMORIA RELEVANTE:\n{memory}"},
                *self.conversation,
            ],
            "stream": False,
            "keep_alive": self.config.ollama_keep_alive,
            "options": {"temperature": 0.2},
        }
        response = self.session.post(f"{self.config.ollama_host}/api/chat", json=payload, timeout=self.config.timeout)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return str(data.get("message", {}).get("content", "")).strip()

    def ask(self, user_message: str) -> str:
        user_message = user_message.strip()
        if not user_message:
            return "No recibí ninguna orden."
        self.conversation.append({"role": "user", "content": user_message})
        self.conversation = self.conversation[-self.config.max_history_messages:]
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
            self.conversation = self.conversation[-self.config.max_history_messages:]
            return answer
        except requests.Timeout:
            return "La respuesta de Ollama tardó demasiado."
        except requests.RequestException as exc:
            print(f"[BRAIN] Error Ollama: {exc}")
            return "Se produjo un error al comunicarme con Ollama."
        except Exception as exc:
            print(f"[BRAIN] Error: {exc}")
            return "Se produjo un error al procesar la solicitud."
