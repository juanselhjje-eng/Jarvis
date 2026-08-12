from __future__ import annotations

"""Adds a consistent observe -> plan -> act -> verify policy to the assistant."""

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    from core.orchestrator import Orchestrator
    original = Orchestrator._system_prompt
    if getattr(original, "_computer_mode", False):
        _INSTALLED = True
        return

    def enhanced(self):
        base = original(self)
        return base + """

MODO CONTROL HUMANO DEL COMPUTADOR:
- Trata el escritorio como un entorno con estado, no como una lista de comandos aislados.
- Para una tarea que dependa de lo que aparece en pantalla, primero OBSERVA: usa computer_observe, get_active_window o inspect_ui; usa screenshot/screen_ocr si la interfaz no expone controles.
- Para hacer clic en un botón, menú, pestaña o texto cuyo nombre conoces, PRIORIZA click_text. Esta herramienta busca el elemento mediante Windows UI Automation y usa OCR como respaldo; no inventes coordenadas cuando existe un nombre visible.
- Usa click_at solamente cuando tengas coordenadas reales obtenidas de la pantalla o cuando la interfaz sea puramente gráfica.
- Para abrir una aplicación, usa open_application. Para una web usa open_url o la ruta rápida. No intentes abrir una aplicación escribiendo un nombre arbitrario en shell.
- Si el usuario dice 'abre X', 'entra a X', 've a X' o 'inicia X', interpreta X como aplicación o sitio según el contexto y ejecuta la acción; no respondas solo con una explicación.
- Si el usuario dice 'haz clic en X', 'dale clic a X', 'pulsa X' o 'selecciona X', usa click_text(X). Si dice 'doble clic', usa click_text(X, double=True).
- Si una tarea contiene varias acciones ('abre X y luego haz clic en Y'), mantén una ÚNICA tarea: abre X, espera, verifica la ventana, localiza Y, haz clic y verifica el resultado.
- Para acciones tipo 'haz juegos', 'haz esto', 'juega', 'continúa' o similares, no inventes el objetivo: inspecciona la interfaz primero y usa el contexto disponible para determinar qué acción concreta corresponde. Si falta un objetivo imprescindible, pide únicamente ese dato.
- Después de abrir o interactuar, VERIFICA el estado: ventana activa, UI Automation, OCR o captura. Si la acción no ocurrió, intenta una alternativa segura antes de informar fallo.
- Mantén el contexto de una tarea completa. No vuelvas al estado inicial después de cada clic.
- Usa atajos de teclado cuando sean más fiables que coordenadas.
- Antes de interactuar con una aplicación que acaba de abrirse, espera un momento razonable y comprueba que la ventana esté activa.
- Si una acción falla, cambia de estrategia de forma segura y registra la experiencia para futuras tareas.
- No borres archivos, carpetas ni datos. Para transformaciones de archivos conserva el original.
- Nunca muevas el cursor o hagas clic sin una razón relacionada con la tarea del usuario.
- Si la solicitud es ambigua, pregunta solo por el dato que realmente falta; no reinicies toda la conversación.
"""

    enhanced._computer_mode = True
    Orchestrator._system_prompt = enhanced
    _INSTALLED = True


install()
