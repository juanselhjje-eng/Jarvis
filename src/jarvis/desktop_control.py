from __future__ import annotations

import os
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from typing import Any

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None


@dataclass
class DesktopAction:
    action: str
    target: str = ""
    text: str = ""
    x: int | None = None
    y: int | None = None


class DesktopController:
    """Control visible del escritorio. No registra teclas ni captura credenciales."""

    def __init__(self) -> None:
        self.enabled = pyautogui is not None
        if self.enabled:
            pyautogui.PAUSE = 0.08
            pyautogui.FAILSAFE = True

    def status(self) -> str:
        if not self.enabled:
            return "Control de escritorio no disponible: falta instalar pyautogui."
        try:
            x, y = pyautogui.position()
            width, height = pyautogui.size()
            return f"Control de escritorio activo. Cursor: ({x}, {y}). Pantalla: {width}x{height}."
        except Exception as exc:
            return f"No pude consultar el escritorio: {exc}"

    def move(self, x: int, y: int) -> str:
        if not self.enabled:
            return "Control de escritorio no disponible."
        pyautogui.moveTo(x, y, duration=0.25)
        return f"Cursor movido a ({x}, {y})."

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> str:
        if not self.enabled:
            return "Control de escritorio no disponible."
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(button=button)
        return "Clic ejecutado en el escritorio."

    def type_text(self, text: str) -> str:
        if not self.enabled:
            return "Control de escritorio no disponible."
        # Solo texto proporcionado explícitamente por el usuario; no se registra lo escrito.
        pyautogui.write(text, interval=0.015)
        return "Texto introducido."

    def hotkey(self, *keys: str) -> str:
        if not self.enabled:
            return "Control de escritorio no disponible."
        pyautogui.hotkey(*keys)
        return f"Atajo ejecutado: {' + '.join(keys)}."

    def open_url(self, url: str) -> str:
        if not (url.startswith("https://") or url.startswith("http://")):
            return "Solo puedo abrir URLs http/https."
        webbrowser.open(url)
        return f"Navegador abierto en {url}."

    def open_browser(self) -> str:
        webbrowser.open("https://www.google.com/")
        return "Navegador abierto."

    def wait(self, seconds: float = 1.0) -> str:
        time.sleep(max(0.0, min(seconds, 10.0)))
        return "Espera completada."
