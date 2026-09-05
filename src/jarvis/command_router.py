from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path

import psutil

from .memory import LocalMemory


class CommandRouter:
    """Herramientas deterministas del único agente JARVIS."""

    def __init__(self) -> None:
        self.memory = LocalMemory()

    def handle(self, command: str) -> str | dict[str, str] | None:
        text = self._clean_wake_word(command.strip())
        lower = text.lower().strip()
        if not lower:
            return "Dime qué necesitas."

        provider = self._provider_intent(lower)
        if provider:
            return {"provider": provider}

        if self._is_system_request(lower):
            return self.system_status()

        communication = self._communication_intent(text)
        if communication:
            return communication

        search = self._search_intent(text)
        if search:
            self.search_web(search)
            return f"Buscando {search} en Google."

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
            "estado del sistema", "estado sistema", "cómo está el sistema", "como esta el sistema",
            "revisa el sistema", "revisa mi pc", "revisa mi computadora",
        }

    @staticmethod
    def _communication_intent(text: str) -> dict[str, str] | None:
        lower = text.lower()
        if not re.search(r"\b(?:escríbele|escribele|envíale|enviale|mándale|mandale|envía|envia|manda)\b", lower):
            return None
        if "teams" in lower:
            platform_name, url = "Teams", "https://teams.microsoft.com/"
        elif "gmail" in lower or "correo" in lower or "email" in lower:
            platform_name, url = "Gmail", "https://mail.google.com/"
        else:
            return None
        match = re.search(r"\b(?:a|para)\s+([^,.:]+?)(?:\s+(?:y|dile|dile que|con el mensaje|que diga)\b|,|$)", text, flags=re.IGNORECASE)
        person = match.group(1).strip() if match else "el contacto"
        body_match = re.search(r"\b(?:dile|escríbele|escribele|mensaje)\s+(?:que\s+)?(.+)$", text, flags=re.IGNORECASE)
        body = body_match.group(1).strip() if body_match else ""
        webbrowser.open(url, new=2)
        detail = f" He identificado a {person}."
        if body:
            detail += " El mensaje queda pendiente de confirmación antes de enviarlo."
        return {"communication": platform_name.lower(), "person": person, "body": body, "message": f"Abrí {platform_name}.{detail}"}

    @staticmethod
    def _search_intent(text: str) -> str | None:
        match = re.match(r"^(?:busca|buscar|búscame|buscame|googlea|investiga)\s+(.+)$", text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def search_web(query: str) -> None:
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        webbrowser.open(url, new=2)

    @staticmethod
    def _open_intent(text: str) -> str | None:
        for pattern in (r"^(?:abre|abrir|open)\s+(.+)$", r"^(?:inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\s+(.+)$"):
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _remember_intent(text: str) -> str | None:
        match = re.match(r"^(?:recuerda|recordar|acuérdate de|acuerdate de|guarda|guardar|anota|anotar)\s+(.+)$", text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _is_memory_request(text: str) -> bool:
        return text in {"qué recuerdas", "que recuerdas", "qué tienes en memoria", "que tienes en memoria", "qué recuerdas de mí", "que recuerdas de mi"}

    @staticmethod
    def system_status() -> str:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.2)
        return f"Sistema: {platform.system()} {platform.release()}. CPU: {cpu:.0f}%. RAM: {memory.percent:.0f}% usada."

    @staticmethod
    def open_target(target: str) -> str:
        if not target:
            return "No indicaste qué abrir."
        clean = target.strip().lower()
        websites = {
            "google": "https://www.google.com", "google chrome": "https://www.google.com", "chrome": "https://www.google.com",
            "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com", "google maps": "https://maps.google.com",
            "maps": "https://maps.google.com", "github": "https://github.com", "chatgpt": "https://chatgpt.com",
            "teams": "https://teams.microsoft.com/", "microsoft teams": "https://teams.microsoft.com/",
        }
        if clean in websites:
            webbrowser.open(websites[clean], new=2)
            return f"Abriendo {target}."
        path = Path(os.path.expandvars(os.path.expanduser(target)))
        try:
            if path.exists():
                os.startfile(str(path))  # type: ignore[attr-defined]
                return f"Abriendo {path}."
            executable = shutil.which(target)
            if executable:
                subprocess.Popen([executable], shell=False)
                return f"Ejecutando {target}."
            return f"No encontré una aplicación o ruta válida llamada {target}."
        except OSError as exc:
            return f"No pude abrir {target}: {exc}"
