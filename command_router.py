from __future__ import annotations

import os
import platform
import re
import subprocess
import webbrowser
from pathlib import Path

import psutil

from memory import LocalMemory


class CommandRouter:
    """Herramientas deterministas del único agente JARVIS.

    Convierte órdenes naturales sencillas en acciones reales. No es otro agente:
    solo detecta intenciones conocidas y ejecuta la herramienta correspondiente.
    """

    def __init__(self) -> None:
        self.memory = LocalMemory()

    def handle(self, command: str) -> str | None:
        text = self._clean_wake_word(command.strip())
        lower = text.lower().strip()

        if not lower:
            return "Dime qué necesitas."

        provider = self._provider_intent(lower)
        if provider:
            return {"provider": provider}

        if self._is_system_request(lower):
            return self.system_status()

        target = self._open_intent(text)
        if target:
            return self.open_target(target)

        memory_value = self._remember_intent(text)
        if memory_value is not None:
            self.memory.set("nota", memory_value)
            return "Entendido. Lo he guardado en mi memoria local."

        if self._is_memory_request(lower):
            value = self.memory.get("nota")
            return f"Recuerdo: {value}" if value else "No tengo notas guardadas todavía."

        if lower in {"/limpiar", "limpiar conversación", "borra la conversación", "olvida esta conversación"}:
            return None

        return None

    @staticmethod
    def _clean_wake_word(text: str) -> str:
        return re.sub(r"^\s*(?:jarvis|viernes)\s*[,;:\-]?\s*", "", text, flags=re.IGNORECASE)

    @staticmethod
    def _provider_intent(text: str) -> str | None:
        if re.search(r"\b(?:usa|usar|cambia(?:r)?(?: a)?|cámbiate a|cambiar a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?claude\b", text):
            return "claude"
        if re.search(r"\b(?:usa|usar|cambia(?:r)?(?: a)?|cámbiate a|cambiar a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?ollama\b", text):
            return "ollama"
        return None

    @staticmethod
    def _is_system_request(text: str) -> bool:
        return text in {
            "/sistema",
            "estado del sistema",
            "estado sistema",
            "cómo está el sistema",
            "como esta el sistema",
            "revisa el sistema",
            "revisa mi pc",
            "revisa mi computadora",
        }

    @staticmethod
    def _open_intent(text: str) -> str | None:
        patterns = (
            r"^(?:abre|abrir|open)\s+(.+)$",
            r"^(?:inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\s+(.+)$",
        )
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _remember_intent(text: str) -> str | None:
        match = re.match(
            r"^(?:recuerda|recordar|acuérdate de|acuerdate de|guarda|guardar|anota|anotar)\s+(.+)$",
            text,
            flags=re.IGNORECASE,
        )
        return match.group(1).strip() if match else None

    @staticmethod
    def _is_memory_request(text: str) -> bool:
        return text in {
            "/memoria",
            "qué recuerdas",
            "que recuerdas",
            "qué tienes en memoria",
            "que tienes en memoria",
            "qué recuerdas de mí",
            "que recuerdas de mi",
        }

    @staticmethod
    def system_status() -> str:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.2)
        return (
            f"Sistema: {platform.system()} {platform.release()}. "
            f"CPU: {cpu:.0f}%. RAM: {memory.percent:.0f}% usada."
        )

    @staticmethod
    def open_target(target: str) -> str:
        if not target:
            return "No indicaste qué abrir."

        clean = target.strip().lower()
        websites = {
            "google": "https://www.google.com",
            "google chrome": "https://www.google.com",
            "chrome": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "google maps": "https://maps.google.com",
            "maps": "https://maps.google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com",
        }

        if clean in websites:
            webbrowser.open(websites[clean], new=2)
            return f"Abriendo {target}."

        path = Path(os.path.expandvars(os.path.expanduser(target)))
        try:
            if path.exists():
                os.startfile(str(path))  # type: ignore[attr-defined]
                return f"Abriendo {path}."

            subprocess.Popen(target, shell=True)
            return f"Ejecutando {target}."
        except Exception as exc:
            return f"No pude abrir {target}: {exc}"
