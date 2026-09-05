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
        return (
            text in {
                "estado del sistema", "estado sistema", "cómo está el sistema", "como esta el sistema",
                "revisa el sistema", "revisa mi pc", "revisa mi computadora",
                "especificaciones de mi pc", "especificaciones de mi computadora",
                "especificaciones de mi ordenador", "especificaciones del pc",
                "especificaciones de pc", "dime las especificaciones de mi pc",
                "dime las especificaciones de mi computadora", "qué tiene mi pc",
                "que tiene mi pc", "información de mi pc", "informacion de mi pc",
                "información del pc", "informacion del pc", "datos de mi pc",
            }
            or any(phrase in text for phrase in (
                "especificaciones de mi pc", "especificaciones de mi computadora",
                "especificaciones del pc", "información de mi pc", "informacion de mi pc",
            ))
        )

    @staticmethod
    def _communication_intent(text: str) -> dict[str, str] | None:
        lower = text.lower()
        if not re.search(r"\b(?:escríbele|escribele|envíale|enviale|mándale|mandale|envía|envia|manda|escribirle|mandar)\b", lower):
            return None

        if "teams" in lower or "teams.live.com" in lower or "teams.microsoft.com" in lower:
            platform_name = "Teams"
            default_url = "https://teams.live.com/v2/" if "educativo" not in lower and "colegio" not in lower and "escuela" not in lower else "https://teams.microsoft.com/"
        elif "gmail" in lower or "correo" in lower or "email" in lower:
            platform_name = "Gmail"
            default_url = "https://mail.google.com/"
        else:
            return None

        url_match = re.search(r"https?://[^\s]+", text, flags=re.IGNORECASE)
        url = url_match.group(0).rstrip(".,)") if url_match else default_url

        remainder = re.sub(r"https?://[^\s]+", " ", text, flags=re.IGNORECASE)
        remainder = re.sub(r"\b(?:teams|microsoft teams|gmail)\b", " ", remainder, flags=re.IGNORECASE)
        remainder = re.sub(r"\b(?:abre|abrir|en|el|la|navegador|google|chrome|personal|educativo|educativa|colegio|escuela)\b", " ", remainder, flags=re.IGNORECASE)
        remainder = re.sub(r"\s+", " ", remainder).strip(" ,:-")

        person = "el contacto"
        body = ""
        person_match = re.search(r"\b(?:a|para)\s+(.+)$", remainder, flags=re.IGNORECASE)
        if person_match:
            tail_text = person_match.group(1).strip()
            split = re.search(
                r"\s+(?:y\s+)?(?:dile|dile que|dile esto|que diga|mensaje|mensaje que|escríbele|escribele|envíale|enviale|mándale|mandale)\b\s*[:,-]?\s*",
                tail_text,
                flags=re.IGNORECASE,
            )
            if split:
                person = tail_text[:split.start()].strip(" ,:-") or person
                body = tail_text[split.end():].strip()
            else:
                greeting = re.search(r"\s+(hola\b.*)$", tail_text, flags=re.IGNORECASE)
                if greeting:
                    person = tail_text[:greeting.start()].strip(" ,:-") or person
                    body = greeting.group(1).strip()
                else:
                    person = tail_text.strip(" ,:-") or person

        webbrowser.open(url, new=2)
        if body:
            message = (
                f"Abrí {platform_name} en el navegador. Contacto: {person}. "
                f"Mensaje preparado: \"{body}\". No lo enviaré sin tu confirmación explícita."
            )
        else:
            message = f"Abrí {platform_name} en el navegador. Contacto detectado: {person}. Falta el texto del mensaje."

        return {
            "communication": platform_name.lower(),
            "person": person,
            "body": body,
            "url": url,
            "message": message,
        }

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
        for pattern in (
            r"^(?:abre|abrir|open|entra|entrar|ve|ir)\s+(?:a\s+|al\s+)?(.+)$",
            r"^(?:inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\s+(.+)$",
        ):
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
        return text in {
            "qué recuerdas", "que recuerdas", "qué tienes en memoria", "que tienes en memoria",
            "qué recuerdas de mí", "que recuerdas de mi",
        }

    @staticmethod
    def system_status() -> str:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.2)
        lines = [
            f"Sistema: {platform.system()} {platform.release()}",
            f"Equipo: {platform.node()}",
            f"Procesador: {platform.processor() or 'No disponible'}",
            f"CPU: {cpu:.0f}% en uso",
            f"RAM: {memory.percent:.0f}% usada ({memory.used / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB)",
        ]
        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
            lines.append(f"Disco del sistema: {disk.percent:.0f}% usado ({disk.used / (1024**3):.1f} GB / {disk.total / (1024**3):.1f} GB)")
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            gpus = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if gpus:
                lines.append("GPU: " + "; ".join(gpus))
        except Exception:
            pass
        return "\n".join(lines)

    @staticmethod
    def open_target(target: str) -> str:
        if not target:
            return "No indicaste qué abrir."

        original = target.strip()
        clean = original.lower()
        clean = re.sub(r"^(?:en\s+)?(?:el\s+)?(?:navegador|google|chrome)\s+", "", clean).strip()
        clean = re.sub(r"^(?:la|el)\s+aplicación\s+", "", clean).strip()

        if re.match(r"^https?://", clean, flags=re.IGNORECASE):
            webbrowser.open(clean, new=2)
            return f"Abriendo {original} en el navegador."

        # Regla de cuentas Teams: "Teams" solo = PERSONAL. Solo las palabras
        # "educativo/colegio/escuela" envían a la cuenta educativa.
        teams_educational = any(word in clean for word in ("educativo", "educativa", "colegio", "escuela", "institucional"))
        if "teams" in clean:
            url = "https://teams.microsoft.com/" if teams_educational else "https://teams.live.com/v2/"
            account = "educativo" if teams_educational else "personal"
            webbrowser.open(url, new=2)
            return f"Abriendo Teams {account} en el navegador."

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
            return f"Abriendo {original} en el navegador."

        browser_target = re.match(r"^(?:en\s+)?(?:google|chrome|navegador)\s+(.+)$", clean)
        if browser_target:
            nested = browser_target.group(1).strip()
            if "teams" in nested:
                teams_educational = any(word in nested for word in ("educativo", "educativa", "colegio", "escuela", "institucional"))
                url = "https://teams.microsoft.com/" if teams_educational else "https://teams.live.com/v2/"
                webbrowser.open(url, new=2)
                return f"Abriendo Teams {'educativo' if teams_educational else 'personal'} en el navegador."
            if nested in websites:
                webbrowser.open(websites[nested], new=2)
                return f"Abriendo {nested} en el navegador."

        path = Path(os.path.expandvars(os.path.expanduser(original)))
        try:
            if path.exists():
                os.startfile(str(path))  # type: ignore[attr-defined]
                return f"Abriendo {path}."
            executable = shutil.which(original)
            if executable:
                subprocess.Popen([executable], shell=False)
                return f"Ejecutando {original}."
            return f"No encontré una aplicación o ruta válida llamada {original}."
        except OSError as exc:
            return f"No pude abrir {original}: {exc}"
