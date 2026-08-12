from __future__ import annotations

"""Adds a consistent observe -> act -> verify policy to the assistant prompt."""

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
- Para una tarea que dependa de lo que aparece en pantalla, primero OBSERVA: usa computer_observe o get_active_window y, si hace falta, screenshot/screen_ocr.
- Después ACTÚA con la herramienta mínima necesaria: enfoca la ventana, mueve/clica/teclea, espera a que la aplicación reaccione y continúa.
- Después VERIFICA: comprueba la ventana activa, usa OCR/captura o lee el resultado de la herramienta. Si no se verificó, no afirmes que terminó.
- Mantén el contexto de una tarea completa. No vuelvas al estado inicial después de cada clic.
- Usa atajos de teclado cuando sean más fiables que coordenadas. Usa coordenadas solo cuando la pantalla lo requiera.
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
