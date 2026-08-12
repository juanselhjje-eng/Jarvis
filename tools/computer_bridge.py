from __future__ import annotations

"""Registers the desktop-control primitives without making registry.py fragile."""


def install() -> None:
    from tools import registry
    from tools.computer_control import (
        wait, get_active_window, get_mouse_position, screenshot, screen_ocr,
        scroll, drag_mouse, double_click, hotkey, copy_selection, paste_text,
        focus_window, computer_observe,
    )

    additions = {
        "wait": {
            "function": wait,
            "description": "Espera unos segundos para que una aplicación termine de cargar o reaccionar.",
            "parameters": {"seconds": {"type": "number", "description": "Segundos de espera, máximo 30."}},
        },
        "get_active_window": {
            "function": get_active_window,
            "description": "Identifica la ventana de Windows que está actualmente en primer plano.",
            "parameters": {},
        },
        "get_mouse_position": {
            "function": get_mouse_position,
            "description": "Obtiene la posición actual del cursor.",
            "parameters": {},
        },
        "screenshot": {
            "function": screenshot,
            "description": "Toma una captura de la pantalla para observación, OCR o diagnóstico.",
            "parameters": {"path": {"type": "string", "description": "Ruta de salida opcional."}},
        },
        "screen_ocr": {
            "function": screen_ocr,
            "description": "Extrae texto visible de una captura mediante OCR cuando está instalado.",
            "parameters": {"path": {"type": "string", "description": "Captura opcional; si no existe se crea."}},
        },
        "scroll": {
            "function": scroll,
            "description": "Desplaza la ventana activa como lo haría un usuario con la rueda del mouse.",
            "parameters": {"amount": {"type": "integer", "description": "Positivo arriba, negativo abajo."}},
        },
        "drag_mouse": {
            "function": drag_mouse,
            "description": "Arrastra el mouse entre dos coordenadas.",
            "parameters": {
                "x1": {"type": "integer", "description": "X inicial."},
                "y1": {"type": "integer", "description": "Y inicial."},
                "x2": {"type": "integer", "description": "X final."},
                "y2": {"type": "integer", "description": "Y final."},
                "duration": {"type": "number", "description": "Duración del arrastre."},
                "button": {"type": "string", "description": "left, right o middle."},
            },
        },
        "double_click": {
            "function": double_click,
            "description": "Hace doble clic en la posición actual del cursor.",
            "parameters": {"button": {"type": "string", "description": "Botón del mouse."}},
        },
        "hotkey": {
            "function": hotkey,
            "description": "Ejecuta un atajo de teclado como ctrl+l, alt+tab o ctrl+s.",
            "parameters": {"keys": {"type": "string", "description": "Teclas separadas por +."}},
        },
        "copy_selection": {
            "function": copy_selection,
            "description": "Copia la selección actual y, si es posible, devuelve su texto.",
            "parameters": {},
        },
        "paste_text": {
            "function": paste_text,
            "description": "Pega texto en la aplicación que está enfocada.",
            "parameters": {"text": {"type": "string", "description": "Texto a pegar."}},
        },
        "focus_window": {
            "function": focus_window,
            "description": "Busca y enfoca una ventana visible por una parte de su título.",
            "parameters": {"title_fragment": {"type": "string", "description": "Parte del título."}},
        },
        "computer_observe": {
            "function": computer_observe,
            "description": "Observa el estado básico del escritorio: ventana activa, cursor y captura de pantalla.",
            "parameters": {},
        },
    }
    registry.TOOLS.update(additions)


install()
