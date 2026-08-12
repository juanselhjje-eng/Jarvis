from __future__ import annotations

"""Human-like Windows observation and desktop controls."""

import ctypes
import os
import time
from pathlib import Path


def _pyautogui():
    try:
        import pyautogui
        pyautogui.PAUSE = 0.05
        pyautogui.FAILSAFE = True
        return pyautogui
    except ImportError as exc:
        raise RuntimeError("PyAutoGUI no está instalado. Ejecuta: pip install pyautogui") from exc


def wait(seconds: float = 0.5) -> str:
    seconds = max(0.05, min(float(seconds), 30.0))
    time.sleep(seconds)
    return f"Esperé {seconds:.2f} segundos."


def get_active_window() -> str:
    if os.name != "nt":
        return "Sistema no Windows."
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "No pude identificar la ventana activa."
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return f"VENTANA ACTIVA: {buf.value.strip() or '(sin título)'} | HWND={hwnd}"


def get_mouse_position() -> str:
    pyautogui = _pyautogui()
    x, y = pyautogui.position()
    return f"CURSOR: ({x}, {y})"


def screenshot(path: str = "workspace/screen.png") -> str:
    pyautogui = _pyautogui()
    target = Path(os.path.expandvars(os.path.expanduser(path)))
    if not target.is_absolute():
        from config.settings import WORKSPACE_DIR
        target = WORKSPACE_DIR / target
    target.parent.mkdir(parents=True, exist_ok=True)
    pyautogui.screenshot().save(str(target))
    return f"Captura de pantalla guardada: {target}"


def screen_ocr(path: str = "workspace/screen.png") -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path)))
    if not target.is_absolute():
        from config.settings import WORKSPACE_DIR
        target = WORKSPACE_DIR / target
    if not target.exists():
        screenshot(str(target))
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(target), lang="spa+eng").strip()
        return text[:12000] if text else "No encontré texto legible en la pantalla."
    except ImportError:
        return "OCR no está instalado. La captura sí está disponible."
    except Exception as exc:
        return f"No pude ejecutar OCR: {exc}"


def scroll(amount: int) -> str:
    pyautogui = _pyautogui()
    value = max(-30, min(30, int(amount)))
    pyautogui.scroll(value)
    return f"Desplazamiento ejecutado: {value}."


def drag_mouse(x1: int, y1: int, x2: int, y2: int, duration: float = 0.35, button: str = "left") -> str:
    pyautogui = _pyautogui()
    pyautogui.moveTo(int(x1), int(y1), duration=0.12)
    pyautogui.dragTo(int(x2), int(y2), duration=max(0.05, float(duration)), button=button)
    return f"Arrastre ejecutado: ({int(x1)}, {int(y1)}) → ({int(x2)}, {int(y2)})."


def double_click(button: str = "left") -> str:
    pyautogui = _pyautogui()
    pyautogui.doubleClick(button=button, interval=0.10)
    return f"Doble clic ejecutado: {button}."


def hotkey(keys: str) -> str:
    pyautogui = _pyautogui()
    parts = [part.strip().lower() for part in str(keys).replace(" ", "").split("+") if part.strip()]
    if not parts:
        return "No recibí ninguna tecla."
    pyautogui.hotkey(*parts) if len(parts) > 1 else pyautogui.press(parts[0])
    return f"Atajo ejecutado: {'+'.join(parts)}."


def copy_selection() -> str:
    pyautogui = _pyautogui()
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.08)
    try:
        import pyperclip
        return f"Texto copiado: {str(pyperclip.paste())[:8000]}"
    except ImportError:
        return "Selección copiada al portapapeles."


def paste_text(text: str) -> str:
    pyautogui = _pyautogui()
    value = str(text)
    try:
        import pyperclip
        pyperclip.copy(value)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        pyautogui.write(value, interval=0.008)
    return "Texto pegado en la ventana activa."


def focus_window(title_fragment: str) -> str:
    if os.name != "nt":
        return "Esta función requiere Windows."
    needle = str(title_fragment).strip().lower()
    if not needle:
        return "Necesito parte del título de la ventana."
    user32 = ctypes.windll.user32
    matches = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title and needle in title.lower():
            matches.append((hwnd, title))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    if not matches:
        return f"No encontré una ventana visible que contenga '{title_fragment}'."
    hwnd, title = matches[0]
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    return f"Ventana enfocada: {title}."


def computer_observe() -> str:
    active = get_active_window()
    cursor = get_mouse_position()
    shot = screenshot("workspace/observations/latest.png")
    return f"{active}\n{cursor}\n{shot}"
