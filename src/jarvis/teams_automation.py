from __future__ import annotations

import time
import webbrowser
from dataclasses import dataclass

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


@dataclass
class TeamsDraft:
    account: str
    contact: str
    message: str


class TeamsAutomation:
    """Automatización visible de Teams usando la sesión ya iniciada del usuario."""

    PERSONAL_URL = "https://teams.live.com/v2/"
    EDUCATIONAL_URL = "https://teams.microsoft.com/"

    def __init__(self) -> None:
        self.load_wait = 5.0

    @staticmethod
    def _available() -> bool:
        return pyautogui is not None and pyperclip is not None

    @staticmethod
    def _paste(text: str) -> None:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")

    def open(self, educational: bool = False) -> str:
        url = self.EDUCATIONAL_URL if educational else self.PERSONAL_URL
        account = "educativo" if educational else "personal"
        webbrowser.open(url, new=2)
        return f"Abriendo Teams {account} en el navegador."

    def _open_and_find(self, contact: str, educational: bool) -> str:
        if not self._available():
            return "Para automatizar Teams faltan pyautogui y pyperclip. Ejecuta: python -m pip install pyautogui pyperclip"
        url = self.EDUCATIONAL_URL if educational else self.PERSONAL_URL
        account = "educativo" if educational else "personal"
        webbrowser.open(url, new=2)
        time.sleep(self.load_wait)

        # Teams documenta navegación por teclado para Search y Compose.
        # Personal: Ctrl+E / Ctrl+R. Educativo/web: Ctrl+Alt+E / Alt+Shift+R.
        if educational:
            pyautogui.hotkey("ctrl", "alt", "e")
        else:
            pyautogui.hotkey("ctrl", "e")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        self._paste(contact)
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(2)
        pyautogui.press("enter")
        time.sleep(2)
        return account

    def open_contact(self, contact: str, educational: bool = False) -> str:
        if not contact:
            return "Necesito el nombre del contacto."
        try:
            account = self._open_and_find(contact, educational)
            return f"Abrí Teams {account} y busqué a {contact}."
        except Exception as exc:
            account = "educativo" if educational else "personal"
            return f"Abrí Teams {account}, pero no pude abrir el contacto {contact}: {exc}"

    def prepare_message(self, contact: str, message: str, educational: bool = False) -> str:
        if not contact or not message:
            return "Necesito el contacto y el texto del mensaje."
        try:
            account = self._open_and_find(contact, educational)
            if educational:
                pyautogui.hotkey("alt", "shift", "r")
            else:
                pyautogui.hotkey("ctrl", "r")
            time.sleep(0.5)
            self._paste(message)
            return (
                f"Abrí Teams {account}, busqué a {contact} y dejé preparado el mensaje: "
                f"\"{message}\". El mensaje está escrito pero NO lo he enviado. "
                "Di 'sí, envíalo' para enviarlo."
            )
        except Exception as exc:
            account = "educativo" if educational else "personal"
            return f"Abrí Teams {account}, pero no pude completar la automatización de {contact}: {exc}"

    def send_draft(self) -> str:
        if not self._available():
            return "La automatización de Teams no está disponible."
        try:
            pyautogui.hotkey("ctrl", "shift", "x")
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "enter")
            return "Mensaje enviado en Teams."
        except Exception as exc:
            return f"No pude enviar el mensaje: {exc}"
