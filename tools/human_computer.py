from __future__ import annotations

"""Human-like Windows interaction helpers.

These tools let JARVIS act on visible UI elements by semantic text instead of
requiring the model to guess screen coordinates. They never delete data.
"""

import os
import time
from typing import Optional


def _pyautogui():
    import pyautogui
    pyautogui.PAUSE = 0.05
    pyautogui.FAILSAFE = True
    return pyautogui


def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Click exact screen coordinates."""
    p = _pyautogui()
    p.click(int(x), int(y), clicks=max(1, min(int(clicks), 3)), button=str(button or "left"))
    return f"Clic ejecutado en ({int(x)}, {int(y)})."


def _uia_click(text: str, window_title: str = "") -> Optional[str]:
    """Try Windows UI Automation first; works better than OCR for real controls."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        windows = desktop.windows(visible_only=True)
        needle = str(text).strip().casefold()
        title_needle = str(window_title).strip().casefold()
        candidates = []
        for win in windows:
            title = (win.window_text() or "").strip()
            if title_needle and title_needle not in title.casefold():
                continue
            try:
                controls = win.descendants()
            except Exception:
                controls = []
            for ctl in controls:
                label = (ctl.window_text() or "").strip()
                if not label:
                    continue
                low = label.casefold()
                score = 0
                if low == needle:
                    score = 100
                elif needle in low:
                    score = 85
                elif low in needle:
                    score = 70
                if score:
                    candidates.append((score, win, ctl, label, title))
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, win, ctl, label, title in candidates[:8]:
            try:
                win.set_focus()
            except Exception:
                pass
            try:
                ctl.click_input()
                return f"Hice clic en '{label}' en '{title or 'la ventana activa'}'."
            except Exception:
                try:
                    ctl.invoke()
                    return f"Activé '{label}' en '{title or 'la ventana activa'}'."
                except Exception:
                    continue
    except ImportError:
        return None
    except Exception:
        return None
    return None


def _ocr_click(text: str) -> Optional[str]:
    """Fallback: OCR locates visible text and clicks its bounding box."""
    try:
        import pytesseract
        from PIL import Image
        p = _pyautogui()
        image = p.screenshot()
        data = pytesseract.image_to_data(image, lang="spa+eng", output_type=pytesseract.Output.DICT)
        needle = str(text).strip().casefold()
        best = None
        for i, raw in enumerate(data.get("text", [])):
            label = str(raw).strip()
            if not label:
                continue
            low = label.casefold()
            score = 100 if low == needle else 80 if needle in low else 0
            if score:
                x, y = int(data["left"][i]), int(data["top"][i])
                w, h = int(data["width"][i]), int(data["height"][i])
                best = (score, x + w // 2, y + h // 2, label)
                if score == 100:
                    break
        if best:
            _, x, y, label = best
            p.click(x, y)
            return f"Hice clic sobre el texto visible '{label}'."
    except Exception:
        pass
    return None


def click_text(text: str, window_title: str = "", double: bool = False) -> str:
    """Find a visible control/text label and click it.

    Example: click_text('Juegos') or click_text('Configuración').
    Uses Windows UI Automation first and OCR as fallback.
    """
    value = str(text).strip()
    if not value:
        return "Necesito el texto o nombre del elemento que quieres pulsar."
    result = _uia_click(value, window_title)
    if result:
        if double:
            # UIA already clicked once; perform a second semantic attempt where possible.
            _uia_click(value, window_title)
        return result
    if double:
        first = _ocr_click(value)
        if first:
            _ocr_click(value)
            return first.replace("Hice clic", "Hice doble clic", 1)
    result = _ocr_click(value)
    return result or f"No encontré un elemento visible llamado '{value}'."


def inspect_ui() -> str:
    """Return visible UI control names using Windows UI Automation."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        rows = []
        for win in desktop.windows(visible_only=True):
            title = (win.window_text() or "").strip()
            if not title:
                continue
            rows.append(f"VENTANA: {title}")
            try:
                for ctl in win.descendants()[:80]:
                    label = (ctl.window_text() or "").strip()
                    if label:
                        rows.append(f"  - {label}")
            except Exception:
                pass
        return "\n".join(rows[:500]) or "No encontré controles UI visibles."
    except ImportError:
        return "UI Automation no está instalado. Ejecuta: pip install pywinauto"
    except Exception as exc:
        return f"No pude inspeccionar la interfaz de Windows: {exc}"
