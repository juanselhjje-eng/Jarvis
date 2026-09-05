from __future__ import annotations

import os
import time
import webbrowser
from dataclasses import dataclass

try:
    import pyautogui
except ImportError:  # pragma: no cover
    pyautogui = None

try:
    import pyperclip
except ImportError:  # pragma: no cover
    pyperclip = None


@dataclass
class TeamsDraft:
    account: str
    contact: str
    message: str


class TeamsAutomation:
    """Automatización visible de Teams mediante el navegador y teclado.

    No accede a credenciales ni intenta saltarse autenticación. Usa la sesión de
    Teams que el usuario ya tiene abierta en el navegador.
    """

    PERSONAL_URL = "https://teams.live.com/v2/"
    EDUCATIONAL_URL = "https://teams.microsoft.com/"

    def __init__(self) -> None:
        self.search_x = int(os.getenv("JARVIS_TEAMS_SEARCH_X", "50"))
        self.search_y = int(os.getenv("JARVIS_TEAMS_SEARCH_Y", "10"))
        self.result_x = int(os.getenv("JARVIS_TEAMS_RESULT_X", "50"))
        self.result_y = int(os.getenv("JARVIS_TEAMS_RESULT_Y", "25"))
        self.compose_x = int(os.getenv("JARVIS_TEAMS_COMPOSE_X", "50"))
        self.compose_y = int(os.getenv("JARVIS_TEAMS_COMPOSE_Y", "88"))
        self.load_wait = float(os.getenv("JARVIS_TEAMS_LOAD_WAIT", "5"))

    @staticmethod
    def _available() -> bool:
        return pyautogui is not None and pyperclip is not None

    @staticmethod
    def _click_percent(x_percent: int, y_percent: int) -> None:
        width, height = pyautogui.size()
        pyautogui.click(int(width * x_percent / 100), int(height * y_percent / 100))

    @staticmethod
    def _paste(text: str) -> None:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")

    def open(self, educational: bool = False) -> str:
        url = self.EDUCATIONAL_URL if educational else self.PERSONAL_URL
        account = "educativo" if educational else "personal"
        webbrowser.open(url, new=2)
        return f"Abriendo Teams {account} en el navegador."

    def prepare_message(self, contact: str, message: str, educational: bool = False) -> str:
        if not contact or not message:
            return "Necesito el contacto y el texto del mensaje."
        if not self._available():
            return "Para automatizar Teams faltan pyautogui y pyperclip. Ejecuta: python -m pip install pyautogui pyperclip"

        url = self.EDUCATIONAL_URL if educational else self.PERSONAL_URL
        account = "educativo" if educational else "personal"
        webbrowser.open(url, new=2)
        time.sleep(self.load_wait)

        try:
            self._click_percent(self.search_x, self.search_y)
            pyautogui.hotkey("ctrl", "a")
            self._paste(contact)
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(2)
            pyautogui.press("enter")
            time.sleep(2)

            self._click_percent(self.compose_x, self.compose_y)
            self._paste(message)
            return (
                f"Abrí Teams {account}, busqué a {contact} y dejé preparado el mensaje: "
                f"\"{message}\". El mensaje está escrito pero NO lo he enviado. "
                "Di 'sí, envíalo' para enviarlo."
            )
        except Exception as exc:
            return f"Abrí Teams {account}, pero no pude completar la automatización de {contact}: {exc}"

    def send_draft(self) -> str:
        if not self._available():
            return "La automatización de Teams no está disponible."
        try:
            pyautogui.press("enter")
            return "Mensaje enviado en Teams."
        except Exception as exc:
            return f"No pude enviar el mensaje: {exc}"
