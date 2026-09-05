from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import psutil

from memory import LocalMemory


class CommandRouter:
    """Herramientas deterministas del único agente JARVIS."""

    def __init__(self) -> None:
        self.memory = LocalMemory()

    def handle(self, command: str) -> str | None:
        text = command.strip()
        lower = text.lower()

        if lower in {"/sistema", "estado del sistema", "estado sistema"}:
            return self.system_status()

        if lower.startswith("/abrir "):
            target = text[7:].strip()
            return self.open_target(target)

        if lower.startswith("/recordar "):
            value = text[10:].strip()
            if not value:
                return "Indica qué quieres que recuerde."
            self.memory.set("nota", value)
            return "Queda guardado en la memoria local."

        if lower in {"/memoria", "qué recuerdas", "que recuerdas"}:
            value = self.memory.get("nota")
            return f"Recuerdo: {value}" if value else "No tengo notas guardadas todavía."

        return None

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

        path = Path(os.path.expandvars(os.path.expanduser(target)))
        try:
            if path.exists():
                os.startfile(str(path))  # type: ignore[attr-defined]
                return f"Abriendo {path}."

            subprocess.Popen(target, shell=True)
            return f"Ejecutando {target}."
        except Exception as exc:
            return f"No pude abrir {target}: {exc}"
