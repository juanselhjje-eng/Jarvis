from __future__ import annotations

import base64
import io
from dataclasses import dataclass

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    from PIL import Image
except ImportError:
    Image = None


@dataclass
class ScreenObservation:
    width: int
    height: int
    image_base64: str | None
    note: str


class ComputerUse:
    """Control visible del escritorio bajo órdenes explícitas del usuario.

    No registra pulsaciones, no captura credenciales y no ejecuta comandos de shell.
    La captura solo ocurre cuando JARVIS la solicita explícitamente para una tarea.
    """

    def __init__(self) -> None:
        self.enabled = pyautogui is not None
        if self.enabled:
            pyautogui.PAUSE = 0.08
            pyautogui.FAILSAFE = True

    def observe(self) -> ScreenObservation:
        if not self.enabled:
            return ScreenObservation(0, 0, None, "Falta pyautogui.")
        try:
            image = pyautogui.screenshot()
            width, height = image.size
            encoded: str | None = None
            if Image is not None:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG", optimize=True)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return ScreenObservation(width, height, encoded, "Captura realizada bajo orden explícita.")
        except Exception as exc:
            return ScreenObservation(0, 0, None, f"No pude observar la pantalla: {exc}")

    def move(self, x: int, y: int) -> str:
        if not self.enabled:
            return "Control visual no disponible: instala pyautogui."
        pyautogui.moveTo(int(x), int(y), duration=0.25)
        return f"Cursor movido a ({int(x)}, {int(y)})."

    def click(self, x: int, y: int, button: str = "left") -> str:
        if not self.enabled:
            return "Control visual no disponible: instala pyautogui."
        if button not in {"left", "right", "middle"}:
            return "Botón no permitido."
        pyautogui.click(int(x), int(y), button=button)
        return f"Clic {button} en ({int(x)}, {int(y)})."

    def type_text(self, text: str) -> str:
        if not self.enabled:
            return "Control visual no disponible: instala pyautogui."
        pyautogui.write(text, interval=0.015)
        return "Texto escrito en la ventana activa."

    def hotkey(self, *keys: str) -> str:
        if not self.enabled:
            return "Control visual no disponible: instala pyautogui."
        allowed = {"ctrl", "shift", "alt", "tab", "enter", "esc", "space", "backspace", "home", "end", "up", "down", "left", "right"}
        if not all(k.lower() in allowed or len(k) == 1 for k in keys):
            return "Atajo rechazado por seguridad."
        pyautogui.hotkey(*keys)
        return f"Atajo ejecutado: {' + '.join(keys)}."
