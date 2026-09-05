from __future__ import annotations

import os
import platform
import re
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path

import psutil

from .memory import LocalMemory
from .system_control import SystemControl
from .teams_automation import TeamsAutomation


class CommandRouter:
    """Herramientas deterministas del único agente JARVIS."""

    def __init__(self) -> None:
        self.memory = LocalMemory()
        self.system = SystemControl()
        self.teams = TeamsAutomation()
        self._optimization_pending = False
        self._message_pending = False

    def handle(self, command: str) -> str | dict[str, str] | None:
        text = self._clean_wake_word(command.strip())
        lower = text.lower().strip()
        if not lower:
            return "Dime qué necesitas."

        # Las confirmaciones de acciones externas son deterministas y nunca pasan al modelo.
        if self._message_pending:
            if self._is_confirmation(lower):
                self._message_pending = False
                return {"send_message": "teams"}
            if self._is_rejection(lower):
                self._message_pending = False
                return "Mensaje cancelado. No envié nada."

        if self._optimization_pending and self._is_confirmation(lower):
            self._optimization_pending = False
            return self.system.optimize_safe()
        if self._optimization_pending and self._is_rejection(lower):
            self._optimization_pending = False
            return "Optimización cancelada. No hice cambios."

        provider = self._provider_intent(lower)
        if provider:
            return {"provider": provider}

        teams_command = self._teams_intent(text)
        if teams_command:
            return teams_command

        if self._is_optimization_request(lower):
            self._optimization_pending = True
            return self.system.optimization_report()

        if self._is_wallpaper_request(lower):
            path = self._extract_wallpaper_path(text)
            if not path:
                return "Indícame la ruta de la imagen, por ejemplo: cambia el fondo a C:\\Users\\Juan\\Pictures\\fondo.jpg"
            return self.system.set_wallpaper(path)

        if self._is_temperature_request(lower):
            return f"Temperatura: {self.system.cpu_temperature()}"

        if self._is_system_request(lower):
            return self.system.pc_status()

        app = self._application_intent(text)
        if app:
            try:
                return self.system.open_application(app)
            except (OSError, subprocess.SubprocessError) as exc:
                return f"No pude abrir {app}: {exc}"

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
        if re.search(r"\b(?:usa|usar|cambia(?:r)?(?:\s+a)?|cámbiate a|cambiar a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?claude\b", text):
            return "claude"
        if re.search(r"\b(?:usa|usar|cambia(?:r)?(?:\s+a)?|cámbiate a|cambiar a|selecciona)\s+(?:el\s+)?(?:modelo\s+)?ollama\b", text):
            return "ollama"
        return None

    @staticmethod
    def _is_confirmation(text: str) -> bool:
        normalized = re.sub(r"[^a-záéíóúüñ ]", "", text.lower()).strip()
        return normalized in {
            "sí", "si", "si envialo", "sí envíalo", "sí envía", "si envia",
            "envíalo", "envialo", "envialo ya", "ennvialo", "envía", "envia",
            "mándalo", "mandalo", "mándale", "mandale", "hazlo", "confirmo",
            "confirmar", "dale", "adelante", "procede", "proceder", "sí hazlo", "si hazlo",
        }

    @staticmethod
    def _is_rejection(text: str) -> bool:
        normalized = re.sub(r"[^a-záéíóúüñ ]", "", text.lower()).strip()
        return normalized in {"no", "cancela", "cancelar", "no lo hagas", "detente", "para", "parar"}

    def _teams_intent(self, text: str) -> dict[str, str] | None:
        lower = text.lower()
        if "teams" not in lower:
            return None

        # Regla del proyecto: Teams sin calificativo = personal.
        # Solo "educativo/colegio/escuela/institucional" cambia a la cuenta educativa.
        educational = bool(re.search(r"\b(?:educativo|educativa|colegio|escuela|institucional)\b", lower))
        message_markers = r"(?:dile(?:\s+que)?|dile\s+esto|que\s+diga|escr[ií]bele|env[ií]ale|m[aá]ndale|manda(?:le)?|env[ií]a|escribirle|mandar)"
        has_message_action = bool(re.search(rf"\b{message_markers}\b", lower))
        has_contact = bool(
            re.search(r"\b(?:a|para)\s+[^,;]+", text, re.IGNORECASE)
            or re.search(r"\b(?:contacto|persona|se llama)\s+[^,;]+", text, re.IGNORECASE)
        )

        if not has_message_action and not has_contact:
            return {"communication": "teams", "action": "open", "educational": str(educational)}

        person, body = self._extract_contact_and_message(text)
        if not person:
            return {"communication": "teams", "action": "open", "educational": str(educational)}
        if not body:
            return {"communication": "teams", "action": "open_contact", "educational": str(educational), "person": person}

        result = self.teams.prepare_message(person, body, educational=educational)
        if "NO lo he enviado" in result:
            self._message_pending = True
        return {
            "communication": "teams",
            "message": result,
            "person": person,
            "body": body,
            "educational": str(educational),
            "pending": str(self._message_pending),
        }

    @staticmethod
    def _extract_contact_and_message(text: str) -> tuple[str, str]:
        """Extrae contacto y mensaje de órdenes naturales, tolerando errores comunes de voz."""
        cleaned = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:jarvis|viernes|microsoft teams|teams)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(?:personal|educativo|educativa|colegio|escuela|institucional|en google|en el google|por google|del google|de google|en chrome|en el navegador|desde google|desde chrome|navegador)\b",
            " ", cleaned, flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\b(?:entra|entrar|abre|abrir|mira|mirar|busca|buscar|ve|ir|entra a)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(?:a los que les he escrito|a los que les e escrito|a los que les escribí|a los q(?:ue)? les he escrito|a los q(?:ue)? les e escrito|a quien le escribí|a quien le escribi|mis chats|mis conversaciones)\b",
            " ", cleaned, flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,:-")

        # "la que se llama Majo G y dile hola"
        named = re.search(
            r"\b(?:la|el)?\s*(?:que\s+)?se\s+llama\s+(.+?)(?=\s+(?:y\s+)?(?:dile|escr[ií]bele|env[ií]ale|m[aá]ndale)\b|$)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if named:
            person = named.group(1).strip(" ,:-\"")
            after = cleaned[named.end():]
            body_match = re.search(
                r"\b(?:y\s+)?(?:dile(?:\s+que)?|dile\s+esto|escr[ií]bele|env[ií]ale|m[aá]ndale)\s*[:,-]?\s*(.+)$",
                after,
                flags=re.IGNORECASE,
            )
            body = body_match.group(1).strip(" \"'") if body_match else ""
            return person, body

        # "a Majo G y dile hola"
        direct = re.search(
            r"\b(?:a|para)\s+(.+?)(?=\s+(?:y\s+)?(?:dile|escr[ií]bele|env[ií]ale|m[aá]ndale)\b|$)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if direct:
            person = direct.group(1).strip(" ,:-\"")
            after = cleaned[direct.end():]
            body_match = re.search(
                r"\b(?:y\s+)?(?:dile(?:\s+que)?|dile\s+esto|escr[ií]bele|env[ií]ale|m[aá]ndale)\s*[:,-]?\s*(.+)$",
                after,
                flags=re.IGNORECASE,
            )
            body = body_match.group(1).strip(" \"'") if body_match else ""
            if person.lower() not in {"la", "el", "que", "los", "las", "los q", "q"}:
                return person, body

        contact = re.search(
            r"\b(?:contacto|persona)\s+(.+?)(?=\s+(?:y\s+)?(?:dile|escr[ií]bele|env[ií]ale|m[aá]ndale)\b|$)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if contact:
            person = contact.group(1).strip(" ,:-\"")
            after = cleaned[contact.end():]
            body_match = re.search(
                r"\b(?:y\s+)?(?:dile(?:\s+que)?|dile\s+esto|escr[ií]bele|env[ií]ale|m[aá]ndale)\s*[:,-]?\s*(.+)$",
                after,
                flags=re.IGNORECASE,
            )
            return person, body_match.group(1).strip(" \"'") if body_match else ""

        return "", ""

    @staticmethod
    def _communication_intent(text: str) -> dict[str, str] | None:
        lower = text.lower()
        if "teams" in lower:
            return None
        if not re.search(r"\b(?:escr[ií]bele|env[ií]ale|m[aá]ndale|env[ií]a|manda|escribirle|mandar)\b", lower):
            return None
        if "gmail" in lower or "correo" in lower or "email" in lower:
            return {
                "communication": "gmail",
                "person": "el contacto",
                "body": "",
                "url": "https://mail.google.com/",
                "message": "Abrí Gmail en el navegador. La automatización de Gmail todavía requiere configurar su herramienta específica.",
            }
        return None

    @staticmethod
    def _is_system_request(text: str) -> bool:
        phrases = (
            "estado del sistema", "estado sistema", "cómo está el sistema", "como esta el sistema", "revisa el sistema",
            "revisa mi pc", "revisa mi computadora", "revisa mi ordenador", "como esta mi pc", "cómo está mi pc",
            "como esta mi computadora", "cómo está mi computadora", "como esta el pc", "cómo está el pc",
            "estado de mi pc", "estado del pc", "especificaciones de mi pc", "especificaciones de mi computadora",
            "especificaciones de mi ordenador", "especificaciones del pc", "especificaciones de pc",
            "dime las especificaciones de mi pc", "dime las especificaciones de mi computadora", "qué tiene mi pc", "que tiene mi pc",
            "información de mi pc", "informacion de mi pc", "información del pc", "informacion del pc", "datos de mi pc",
            "diagnóstico de mi pc", "diagnostico de mi pc",
        )
        return text in phrases or any(phrase in text for phrase in phrases)

    @staticmethod
    def _is_temperature_request(text: str) -> bool:
        return bool(re.search(r"\b(?:temperatura|temperaturas|caliente|calor)\b", text)) and bool(re.search(r"\b(?:pc|computadora|ordenador|procesador|cpu|sistema)\b", text))

    @staticmethod
    def _is_optimization_request(text: str) -> bool:
        return bool(re.search(r"\b(?:optimiza|optimizar|optimízalo|optimizalo|optimización|optimizacion)\b", text))

    @staticmethod
    def _is_wallpaper_request(text: str) -> bool:
        return bool(re.search(r"\b(?:fondo de pantalla|fondo|wallpaper)\b", text)) and bool(re.search(r"\b(?:cambia|cambiar|pon|poner|usa|usar|establece|establecer)\b", text))

    @staticmethod
    def _extract_wallpaper_path(text: str) -> str | None:
        match = re.search(r"(?:a|por|como|con|desde)\s+(.+)$", text, re.IGNORECASE)
        if not match:
            return None
        candidate = match.group(1).strip().strip('"')
        return candidate if Path(os.path.expandvars(os.path.expanduser(candidate))).suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"} else None

    @staticmethod
    def _application_intent(text: str) -> str | None:
        match = re.match(r"^(?:abre|abrir|inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\s+(?:la\s+|el\s+)?(?:aplicación\s+|app\s+)?(.+)$", text, flags=re.IGNORECASE)
        if not match:
            return None
        target = match.group(1).strip().lower()
        known = {"calculadora", "calc", "bloc de notas", "notepad", "explorador", "explorador de archivos", "administrador de tareas", "configuración", "configuracion", "settings", "panel de control", "cmd", "powershell"}
        return target if target in known else None

    @staticmethod
    def _search_intent(text: str) -> str | None:
        match = re.match(r"^(?:busca|buscar|búscame|buscame|googlea|investiga)\s+(.+)$", text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def search_web(query: str) -> None:
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(query), new=2)

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
        return text in {"qué recuerdas", "que recuerdas", "qué tienes en memoria", "que tienes en memoria", "qué recuerdas de mí", "que recuerdas de mi"}

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
        return "\n".join(lines)

    @staticmethod
    def open_target(target: str) -> str:
        original = target.strip()
        clean = re.sub(r"^(?:en\s+)?(?:el\s+)?(?:navegador|google|chrome)\s+", "", original.lower()).strip()
        clean = re.sub(r"^(?:la|el)\s+aplicación\s+", "", clean).strip()
        if re.match(r"^https?://", clean, flags=re.IGNORECASE):
            webbrowser.open(clean, new=2)
            return f"Abriendo {original} en el navegador."
        if "teams" in clean:
            educational = bool(re.search(r"\b(?:educativo|educativa|colegio|escuela|institucional)\b", clean))
            webbrowser.open("https://teams.microsoft.com/" if educational else "https://teams.live.com/v2/", new=2)
            return f"Abriendo Teams {'educativo' if educational else 'personal'} en el navegador."
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
            return f"Abriendo {original}."
        return f"Puedo abrir {original}, pero todavía no tengo una integración específica para ese destino."
