from __future__ import annotations

"""Agent policy and task decomposition for JARVIS.

The module deliberately separates planning from execution. Models may propose
plans, but tools are responsible for real-world actions and verification.
"""

AGENT_POLICY = r'''
ARQUITECTURA DE AGENTE JARVIS

OBJETIVO:
- Interpreta la petición como un resultado que el usuario quiere conseguir.
- No dependas de comandos predefinidos: combina las capacidades disponibles.
- Mantén el contexto de la tarea hasta que el objetivo termine o sea imposible.

CICLO DE AGENTE:
1. Comprender intención, restricciones y resultado esperado.
2. Recuperar contexto y memoria relevante.
3. Crear un plan mínimo y ejecutable.
4. Elegir la herramienta adecuada para cada paso.
5. Observar el estado real antes de actuar cuando corresponda.
6. Ejecutar una acción verificable.
7. Esperar si la aplicación necesita tiempo.
8. Observar y verificar el resultado.
9. Si falla, diagnosticar y probar una alternativa segura.
10. Repetir hasta conseguir el objetivo o detectar un bloqueo real.
11. Guardar solamente experiencias verificadas y correcciones útiles.

CONTEXTO:
- Las respuestas cortas completan la tarea pendiente cuando sea razonable.
- Resuelve referencias como "eso", "ahí", "el segundo" o "en el escritorio" usando contexto.
- No preguntes por información que ya esté en memoria, pantalla, archivos o estado de la tarea.
- Pregunta solo cuando falte un dato imprescindible y no exista una inferencia segura.

COMUNICACIÓN:
- No expongas cadena de pensamiento privada.
- Comunica al usuario estados breves y útiles: qué estás haciendo, qué encontraste y si algo falló.
- No afirmes que una acción ocurrió hasta recibir evidencia de la herramienta.

APRENDIZAJE:
- Guarda preferencias, procedimientos, errores y soluciones como memoria recuperable.
- Los modelos externos son asesores; sus propuestas deben contrastarse antes de convertirse en conocimiento persistente.
- Nunca afirmes que modificaste los pesos internos de otro modelo.
'''


def system_extension() -> str:
    return AGENT_POLICY


def classify_task(text: str) -> str:
    value = str(text or "").lower()
    if any(k in value for k in ("abre", "cierra", "haz clic", "escribe", "mueve", "entra", "busca en google", "pon", "configura")):
        return "COMPUTER_ACTION"
    if any(k in value for k in ("crea", "genera", "edita", "modifica", "guarda", "organiza", "pdf", "word", "excel", "presentación")):
        return "FILE_OR_CREATION"
    if any(k in value for k in ("investiga", "busca información", "compara", "qué es", "explica", "por qué", "enseña")):
        return "KNOWLEDGE"
    if any(k in value for k in ("planifica", "organiza mi", "hazme un plan", "prepara")):
        return "GOAL_PLANNING"
    return "GENERAL"


def build_goal_plan(text: str) -> list[str]:
    """Return a lightweight executable outline without pretending to execute it."""
    kind = classify_task(text)
    if kind == "COMPUTER_ACTION":
        return ["observar_estado", "seleccionar_herramienta", "ejecutar", "verificar"]
    if kind == "FILE_OR_CREATION":
        return ["identificar_entradas", "crear_o_modificar", "verificar_archivo", "confirmar_resultado"]
    if kind == "KNOWLEDGE":
        return ["recuperar_contexto", "consultar_fuentes_o_modelos", "contrastar", "sintetizar"]
    if kind == "GOAL_PLANNING":
        return ["entender_objetivo", "recopilar_datos", "planificar", "ejecutar", "verificar"]
    return ["entender_objetivo", "recuperar_contexto", "seleccionar_capacidades", "resolver", "verificar"]
