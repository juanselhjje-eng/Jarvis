from __future__ import annotations
import json
import re
import time
import threading
from pathlib import Path
from providers.ollama_provider import OllamaProvider
from providers.cloud_providers import MultiAIManager
from tools.registry import execute_tool, ollama_tool_definitions
from config.user_profile import load_profile
from memory.learning import get_learning_engine
from core.self_repair import SelfRepairEngine
from memory.autonomous_learning import AutonomousLearning

BASE_PROMPT = """Eres JARVIS, un asistente personal local para Windows.
Habla en español salvo que el usuario pida otro idioma.
Tu objetivo es resolver la tarea del usuario de forma útil y verificable.
Tienes herramientas reales. Cuando una herramienta puede hacer la acción solicitada, ÚSALA.
Nunca afirmes que hiciste algo si la herramienta no confirmó que se hizo.
Puedes encadenar herramientas y comprobar sus resultados.
Puedes controlar el computador mediante las herramientas disponibles: abrir programas y webs, ejecutar programas, escribir, usar teclas, mover/clicar el mouse, trabajar con archivos y proyectos, documentos, PDFs, hojas de cálculo, presentaciones, generar imágenes PNG con IA, organizar carpetas, usar cámara/visión cuando estén disponibles y reproducir música autorizada/local. Si el usuario pide crear/generar/dibujar una imagen, usa generate_image y guarda el resultado en workspace/generated/images; no digas que solo puedes crear Word o PDF.
REGLA DE SEGURIDAD: JARVIS no elimina archivos, carpetas ni datos y bloquea comandos de borrado. Puede crear, leer, editar, copiar, mover, organizar y procesar datos sin destruir el original.
Para música usa exclusivamente play_local_music; no abras Google ni un navegador para reproducir música.
Para escribir en otra aplicación, abre/focaliza primero la aplicación y luego usa type_text.
Para proyectos de programación, crea carpetas y archivos reales dentro del workspace cuando sea apropiado y verifica los resultados.
Puedes trabajar con archivos importados y documentos. Usa read_pdf para leer PDFs, pdf_merge/pdf_split para crear copias procesadas, read_docx/append_docx para DOCX, read_xlsx/write_xlsx_cell para hojas XLSX y read_pptx para presentaciones. No borres originales.
Cuando el usuario te entregue un archivo, identifica primero su tipo y usa la herramienta especializada correspondiente. Si necesitas modificarlo, conserva el original y crea una copia cuando sea una operación de transformación.
Puedes organizar carpetas con organize_folder; nunca uses una operación destructiva para "organizar".
La cámara es un módulo de percepción: puede entregar snapshots al workspace. No afirmes que "ves" el contenido si no existe un proveedor de visión compatible; puedes guardar y preparar la captura.
No muestres razonamiento interno, cadenas de pensamiento ni instrucciones privadas. Puedes explicar conclusiones, decisiones y comprobaciones de forma resumida.
Las respuestas NO deben ser respuestas vacías o genéricas como "Listo.", "Hecho.", "Claro." o "Entendido.". Después de una acción, informa qué hiciste, sobre qué elemento y cuál fue el resultado. En preguntas conceptuales, responde con contenido útil, contexto y ejemplos cuando aporten valor. En tareas complejas, entrega un pequeño resumen de lo realizado y, si corresponde, los siguientes pasos.
No inventes resultados, capacidades, archivos, acciones ni verificaciones.
No ejecutes shell arbitrario: usa las herramientas registradas. Para programas externos usa run_program; nunca conviertas una petición en un comando de borrado.
Cuando la tarea sea sencilla, responde rápido. Cuando sea compleja, planifica internamente y usa las herramientas necesarias.
Distingue siempre entre CONVERSACIÓN/PREGUNTA e ACCIÓN. Una pregunta o comentario informativo no debe ejecutar herramientas solo por contener palabras parecidas a comandos.
Si el usuario pregunta si aprendes, piensas, recuerdas o cómo funcionas, responde usando tu estado y memoria reales; nunca respondas simplemente "Listo.".
Antes de ejecutar una acción, identifica el objetivo, selecciona la herramienta adecuada y comprueba el resultado. Si una acción falla, intenta una alternativa segura y registra el aprendizaje.
"""

class Orchestrator:
    def __init__(self):
        self.provider = OllamaProvider()
        self.ai_manager = MultiAIManager(self.provider)
        self.tools = ollama_tool_definitions()
        self.profile = load_profile()
        self.history = []
        self.learning = get_learning_engine()
        self.last_learning_event = ""
        self.repair = SelfRepairEngine(self.provider)
        self.autonomous_learning = AutonomousLearning(self.learning, self.ai_manager)
        self._last_user_activity = time.time()
        self.task_events = []
        self._ai_lock = threading.RLock()
        self._reflection_threads: list[threading.Thread] = []
        self._last_proactive_generation = 0.0
        self._reset_history()

    def _system_prompt(self):
        p = self.profile.get("personality", {})
        adaptive = self.learning.adaptive_context(limit=8)
        return BASE_PROMPT + f"""
{adaptive}

PERSONALIDAD BASE CONFIGURADA:
Nombre: {p.get('name','JARVIS')}
Tono base: {p.get('tone','Profesional')}
Estilo base: {p.get('style','Claro y directo')}
Proactividad: {p.get('proactivity',80)}/100
Creatividad: {p.get('creativity',70)}/100
Humor: {p.get('humor',35)}/100
Verbosidad: {p.get('verbosity',55)}/100

ADAPTIVE PERSONALITY ENGINE:
- Adapta tu forma de hablar dinámicamente a CADA usuario y a cada mensaje, sin cambiar tus valores ni tus límites de seguridad.
- Detecta solo señales no sensibles del mensaje actual y del contexto conversacional: idioma, formalidad, nivel técnico aparente, longitud preferida, urgencia, frustración, entusiasmo y si el usuario escribe de forma breve o detallada.
- Si el usuario escribe corto y directo, responde corto y directo; si pide profundidad, aumenta el detalle. Si usa lenguaje casual, puedes responder de forma natural y casual sin caricaturizarlo. Si está frustrado, sé calmado, concreto y orientado a resolver. Si está aprendiendo, explica paso a paso.
- No imites errores ortográficos de forma exagerada. Mantén claridad.
- No hagas diagnósticos psicológicos ni infieras atributos sensibles.
- No conviertas una adaptación temporal en una preferencia permanente sin evidencia repetida.
- La personalidad puede evolucionar con preferencias explícitas y aprendizaje validado, pero nunca debe sacrificar exactitud por complacer al usuario.
- No anuncies que estás adaptando tu personalidad salvo que el usuario lo pregunte.

ESTILO DE RESPUESTA:
Responde como un asistente inteligente y colaborativo, no como un contestador de comandos. Evita respuestas vacías como 'listo', 'hecho', 'sí' o 'entendido' cuando no aporten información. Tras una acción, indica brevemente qué hiciste y el resultado. En conversación normal, conversa de forma natural.
"""

    def learning_stats(self):
        return self.learning.stats()

    def teach(self, task: str, correction: str):
        self.learning.teach(task, correction)
        self.last_learning_event = "CORRECTION LEARNED"

    def _reset_history(self):
        self.history = [{"role": "system", "content": self._system_prompt()}]

    def reset(self):
        self._reset_history()

    def update_profile(self, profile):
        self.profile = profile
        if self.history:
            self.history[0] = {"role": "system", "content": self._system_prompt()}

    def _chat(self, messages, **kwargs):
        """Serialize local-model calls so background learning never corrupts a conversation."""
        with self._ai_lock:
            return self.ai_manager.chat(messages, **kwargs)

    def _schedule_reflection(self, task: str, result: str) -> None:
        """Reflect on a completed interaction in the background without delaying the user."""
        task = str(task).strip()
        result = str(result).strip()
        if not task or not result:
            return
        def worker():
            try:
                memory = self.learning.context(task, limit=5)
                prompt = f"""Analiza esta interacción REAL de JARVIS y extrae una sola lección útil para futuras tareas.

TAREA DEL USUARIO:
{task[:1200]}

RESULTADO OBSERVADO:
{result[:1800]}

MEMORIA RELACIONADA:
{memory[:2500]}

Reglas:
- No inventes hechos.
- No conviertas una respuesta puntual en una preferencia permanente salvo que la evidencia lo justifique.
- Prioriza técnicas, rutas de herramientas, errores evitados y preferencias explícitas.
- Si el resultado fue un error sin una solución verificada, marca la lección como una hipótesis de baja confianza.
- Solo las lecciones con confianza alta se convertirán en reglas adaptativas.
- Devuelve SOLO JSON válido: {"lesson":"...","confidence":0.0}
- La lección debe ser breve, accionable y reutilizable.
"""
                response = self._chat(
                    [{"role":"system","content":"Eres el módulo de reflexión y aprendizaje persistente de JARVIS."},
                     {"role":"user","content":prompt}],
                    tools=None,
                    think=True,
                    temperature=0.15,
                )
                raw = getattr(getattr(response, "message", None), "content", "") or ""
                match = re.search(r"\{.*\}", raw, re.S)
                if not match:
                    return
                data = json.loads(match.group(0))
                lesson = str(data.get("lesson", "")).strip()
                confidence = float(data.get("confidence", 0.8))
                if lesson and confidence >= 0.55:
                    self.learning.record_reflection(task, result, lesson, confidence)
                    self.last_learning_event = "SELF-REFLECTION SAVED"
            except Exception:
                # Learning must never break the user's task.
                return
        t = threading.Thread(target=worker, daemon=True, name="jarvis-reflection")
        self._reflection_threads.append(t)
        t.start()

    def generate_proactive_question(self, force: bool = False) -> str:
        """Generate one safe, useful question when the user has been idle."""
        existing = self.learning.get_proactive_question()
        if existing and not force:
            return existing
        now = time.time()
        if not force and now - self._last_proactive_generation < 45:
            return ""
        self._last_proactive_generation = now
        recent = self.learning.recent_proactive_questions(limit=8)
        memory = self.learning.adaptive_context(limit=8)
        prompt = f"""Eres el módulo de aprendizaje proactivo de JARVIS.
El usuario lleva un rato sin hablar. Formula UNA sola pregunta corta que ayude a JARVIS a entender mejor cómo ayudarle en el computador.

Memoria adaptativa:
{memory[:3000]}

Preguntas ya hechas recientemente:
{recent[:8]}

Reglas:
- Pregunta solo por preferencias, flujos de trabajo, herramientas, proyectos o formas de ayudar.
- NO pidas contraseñas, API keys, datos financieros, dirección, ubicación precisa, información médica o cualquier dato sensible.
- No repitas una pregunta reciente.
- No seas insistente ni dramático.
- Español natural.
- Devuelve solo la pregunta, sin introducción.
"""
        try:
            response = self._chat(
                [{"role":"system","content":"Generador de aprendizaje proactivo de JARVIS."},
                 {"role":"user","content":prompt}],
                tools=None,
                think=True,
                temperature=0.35,
            )
            q = str(getattr(getattr(response, "message", None), "content", "") or "").strip()
            q = re.sub(r"^['\"]|['\"]$", "", q).strip()
            if q and not q.endswith(("?", "¿?")):
                q += "?"
            if q:
                self.learning.set_proactive_question(q)
                self.last_learning_event = "PROACTIVE QUESTION READY"
            return q
        except Exception:
            return ""

    def proactive_enabled(self) -> bool:
        return bool(self.profile.get("learning", {}).get("proactive_questions", True))

    def learning_mode(self) -> str:
        return str(self.profile.get("learning", {}).get("mode", "ADAPTIVE")).upper()

    @staticmethod
    def _strip_wake(text):
        return re.sub(r"^\s*(?:jarvis[,:]?\s*)+", "", text, flags=re.I).strip()

    @staticmethod
    def _is_failure(result: str) -> bool:
        value = str(result).strip().lower()
        markers = (
            "error", "no pude", "no encontr", "no está instalado", "no esta instalado",
            "falló", "fallo", "failed", "traceback", "exception", "denegado",
            "no permitido", "no existe", "necesito el nombre", "no recibí", "no recibi",
        )
        return value.startswith("error") or any(marker in value for marker in markers)

    def _attempt_recovery(self, task: str, failed_tool: str, args: dict, error: str, deep: bool = True) -> str | None:
        """Busca una ruta alternativa con el modelo y guarda la corrección verificada."""
        memory = self.learning.context(task, limit=8)
        prompt = f"""La herramienta anterior falló. Debes RECUPERAR la tarea, no rendirte.

TAREA DEL USUARIO:
{task}

HERRAMIENTA QUE FALLÓ:
{failed_tool}
ARGUMENTOS:
{json.dumps(args, ensure_ascii=False)}
ERROR/RESULTADO:
{error[:2500]}

MEMORIA DE EXPERIENCIAS:
{memory}

REGLAS:
- Busca una ruta alternativa o corrige los argumentos.
- No repitas exactamente la misma herramienta con exactamente los mismos argumentos.
- Usa solamente herramientas disponibles.
- No uses shell arbitrario.
- No elimines archivos ni carpetas.
- Si es un error de código, usa self_repair_code/inspect_code.
- Si la memoria contiene una recuperación parecida, priorízala.
- Ejecuta la herramienta y verifica el resultado.
"""
        try:
            response = self._chat(
                [
                    {"role": "system", "content": self._system_prompt() + "\nEstás en modo RECUPERACIÓN. Corrige el fallo usando herramientas reales."},
                    {"role": "user", "content": prompt},
                ],
                tools=self.tools,
                think=True if deep else False,
            )
        except Exception as exc:
            return f"No pude iniciar la recuperación: {exc}"

        current = response
        attempted: set[tuple[str, str]] = set()
        original_signature = (failed_tool, json.dumps(args, sort_keys=True, ensure_ascii=False))
        for _ in range(2):
            message = getattr(current, "message", None)
            calls = getattr(message, "tool_calls", None) or []
            if not calls:
                return None
            for call in calls:
                name = getattr(call.function, "name", "")
                raw_args = getattr(call.function, "arguments", {}) or {}
                if isinstance(raw_args, str):
                    try:
                        call_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        call_args = {}
                else:
                    call_args = dict(raw_args) if isinstance(raw_args, dict) else {}
                signature = (name, json.dumps(call_args, sort_keys=True, ensure_ascii=False))
                if signature == original_signature or signature in attempted:
                    continue
                attempted.add(signature)
                try:
                    result = execute_tool(name, **call_args)
                except Exception as exc:
                    result = f"ERROR al ejecutar {name}: {exc}"
                result_text = str(result)
                if self._is_failure(result_text):
                    self.learning.record_failure(task, name, result_text)
                    self.last_learning_event = f"RECOVERY FAILED // {name}"
                    continue
                self.learning.record_recovery(task, failed_tool, error, name, result_text)
                self.learning.record_success(task, name, result_text)
                self.last_learning_event = f"RECOVERY LEARNED // {failed_tool} -> {name}"
                return result_text
            try:
                current = self._chat(
                    [
                        {"role": "system", "content": self._system_prompt() + "\nContinúa en modo RECUPERACIÓN."},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": "La primera ruta no funcionó. Elige otra herramienta o corrige los parámetros."},
                    ],
                    tools=self.tools,
                    think=True,
                )
            except Exception:
                break
        return None

    def _execute_and_learn(self, task: str, tool: str, args: dict, deep: bool = True) -> str:
        """Ejecuta una acción, registra el resultado y activa recuperación automática si falla."""
        try:
            result = execute_tool(tool, **args)
        except Exception as exc:
            result = f"ERROR al ejecutar {tool}: {exc}"
        result_text = str(result)
        if not self._is_failure(result_text):
            self.learning.record_success(task, tool, result_text)
            self.last_learning_event = f"EXPERIENCIA GUARDADA // {tool}"
            return result_text
        self.learning.record_failure(task, tool, result_text)
        self.last_learning_event = f"ERROR APRENDIDO // {tool}"
        recovery = self._attempt_recovery(task, tool, args, result_text, deep=deep)
        if recovery:
            return f"{result_text}\nRecuperación: {recovery}"
        return result_text

    def _remember_direct(self, task: str, tool: str, result: str):
        result = str(result)
        if self._is_failure(result):
            self.learning.record_failure(task, tool, result)
            self.last_learning_event = f"ERROR APRENDIDO // {tool}"
        else:
            self.learning.record_success(task, tool, result)
            self.last_learning_event = f"EXPERIENCIA GUARDADA // {tool}"
        return result

    def _deterministic(self, text):
        clean = self._strip_wake(text)
        low = clean.lower().strip()

        # Explicit teaching command. This is persistent and non-destructive.
        if low.startswith("aprende que ") or low.startswith("recuerda que "):
            correction = clean.split(" ", 2)[-1].strip()
            self.learning.teach("global", correction)
            self.last_learning_event = "CORRECCIÓN GUARDADA"
            return "Entendido. He guardado esa corrección en mi memoria de aprendizaje."

        m = re.match(r"(?:abre|abrir|inicia|iniciar|entra(?:r)? a)\s+(.+?)\s+y\s+(?:escribe|escribir|teclea)\s+(.+)$", clean, re.I)
        if m:
            app_result = self._execute_and_learn(text, "open_application", {"name": m.group(1).strip()})
            if app_result.startswith("No encontré") or "no pude" in app_result.lower():
                return app_result
            time.sleep(0.35)
            type_result = self._execute_and_learn(text, "type_text", {"text": m.group(2).strip(), "interval": 0.008})
            return f"{app_result} {type_result}"

        m = re.match(r"(?:abre|abrir|inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)\s+(.+)$", clean, re.I)
        if m:
            return self._execute_and_learn(text, "open_application", {"name": m.group(1).strip(" .!?")})

        if low in {"estado", "estado del sistema", "diagnóstico", "diagnostico", "status"}:
            return self._execute_and_learn(text, "system_info", {})

        m = re.match(r"(?:reproduce|reproducir|pon|ponme|escucha|quiero escuchar|quiero oír)\s+(?:la\s+)?(?:canción\s+|musica\s+|música\s+)?(.+)$", clean, re.I)
        if m:
            return self._execute_and_learn(text, "play_local_music", {"query": m.group(1).strip(" .!?")})

        if low.startswith("busca en google imágenes de ") or low.startswith("busca en google imagenes de "):
            prefix = "busca en google imágenes de " if low.startswith("busca en google imágenes de ") else "busca en google imagenes de "
            return self._execute_and_learn(text, "google_image_search", {"query": clean[len(prefix):].strip()})
        if low.startswith("busca en google "):
            return self._execute_and_learn(text, "google_search", {"query": clean[len("busca en google "):].strip()})
        return None

    @staticmethod
    def _looks_like_code_error(result: str) -> bool:
        value = str(result).lower()
        markers = ("syntaxerror", "nameerror", "typeerror", "attributeerror", "importerror", "indentationerror", "traceback", "module not found", "error al ejecutar")
        return any(m in value for m in markers) and any(ext in value for ext in (".py", "python", "line "))

    @staticmethod
    def _extract_error_path(result: str) -> str | None:
        m = re.search(r'([a-zA-Z]:\\[^\n:]+\.py|(?:[\w./\\-]+\.py))', str(result))
        return m.group(1) if m else None

    def _recover_code_error(self, task: str, tool_name: str, result: str) -> str | None:
        if not self._looks_like_code_error(result):
            return None
        path = self._extract_error_path(result)
        if not path:
            return None
        self.last_learning_event = f"SELF-REPAIR // {Path(path).name if 'Path' in globals() else path}"
        repair_result = self.repair.repair(path, result)
        self.learning.record(task, "self_repair", repair_result, success="corregí" in repair_result.lower() or "reparé" in repair_result.lower(), error="no pude" in repair_result.lower() or "fall" in repair_result.lower())
        return repair_result

    def adaptive_status(self) -> dict:
        stats = self.learning.stats()
        stats["proactive_question"] = bool(self.learning.get_proactive_question())
        stats["mode"] = self.learning_mode()
        return stats

    def autonomous_learning_async(self, force: bool = False):
        """Let the AI council teach JARVIS in the background without user input."""
        def _run():
            try:
                idle = time.time() - self._last_user_activity
                if force or idle >= 90:
                    result = self.autonomous_learning.run_once(force=force)
                    if result:
                        self.last_learning_event = result[:160]
            except Exception as exc:
                self.last_learning_event = f"AUTONOMOUS LEARNING ERROR // {exc}"
        threading.Thread(target=_run, daemon=True, name="jarvis-autonomous-learning").start()

    def maintenance_async(self):
        def _run():
            try:
                result = self.repair.audit_project(repair=True, max_repairs=2)
                self.last_learning_event = result[:120]
                # Learning is intentionally separate from code repair.
                self.autonomous_learning_async()
            except Exception as exc:
                self.last_learning_event = f"MAINTENANCE ERROR // {exc}"
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def _polish_action_response(text: str) -> str:
        """Evita respuestas vacías/genéricas después de herramientas deterministas."""
        value = str(text or "").strip()
        if not value:
            return value
        low = value.lower().strip(" .!\n")
        generic = {"listo", "hecho", "ok", "vale", "entendido", "claro", "perfecto"}
        if low in generic:
            return "La acción terminó, pero no recibí un detalle verificable del sistema."
        replacements = {
            "he abierto ": "Abrí ",
            "he creado ": "Creé ",
            "he enviado a windows la orden de abrir ": "Envié a Windows la orden de abrir ",
            "texto escrito.": "Escribí el texto solicitado correctamente.",
        }
        for old, new in replacements.items():
            if low.startswith(old):
                # Preserve the original casing/content after the matched prefix.
                return new + value[len(old):]
        return value

    def handle(self, text: str, deep: bool | None = None):
        text = str(text).strip()
        self._last_user_activity = time.time()
        if not text:
            return ""
        # If JARVIS previously asked a learning question, treat the next natural answer as data.
        pending = self.learning.get_proactive_question()
        if pending and text and not text.startswith("/") and text.lower() not in {"salir", "exit", "cerrar", "cancelar"}:
            self.learning.record_proactive_answer(pending, text)
            self.last_learning_event = "PROACTIVE ANSWER LEARNED"

        direct = self._deterministic(text)
        if direct is not None:
            direct = self._polish_action_response(direct)
            self._schedule_reflection(text, direct)
            return direct

        if deep is None:
            deep = bool(self.profile.get("reasoning", {}).get("deep", True))

        self.history.append({"role": "user", "content": text})
        learned_context = self.learning.context(text)
        self.history[0] = {"role": "system", "content": self._system_prompt() + "\n" + learned_context}
        try:
            response = self._chat(self.history, tools=self.tools, think=bool(deep))
            for _ in range(8 if deep else 5):
                message = response.message
                calls = getattr(message, "tool_calls", None) or []
                if not calls:
                    answer = str(getattr(message, "content", "") or "").strip()

                    # Qwen/Ollama can return an empty visible content field after
                    # internal reasoning. Never turn that into a fake "Listo.".
                    # Retry once without thinking so conversational questions and
                    # normal information requests always receive a real answer.
                    if not answer:
                        retry_messages = list(self.history)
                        retry_messages.append({
                            "role": "system",
                            "content": (
                                "Responde ahora al usuario de forma natural y con contenido útil. "
                                "Evita respuestas de una sola palabra o frases genéricas como Listo/Hecho. "
                                "Si es una pregunta, explica la respuesta con suficiente contexto. Si es una acción, "
                                "resume qué se hizo y el resultado verificable. No muestres razonamiento interno. "
                                "Si la pregunta es sobre JARVIS, explica honestamente qué capacidades tiene."
                            ),
                        })
                        retry = self._chat(
                            retry_messages,
                            tools=None,
                            think=False,
                            temperature=0.25,
                        )
                        answer = str(getattr(getattr(retry, "message", None), "content", "") or "").strip()

                    if not answer:
                        answer = "No obtuve una respuesta visible del modelo. Voy a intentarlo de nuevo."
                    if answer.strip().lower().strip(" .!\n") in {"listo", "hecho", "ok", "vale", "entendido", "claro", "perfecto"}:
                        retry_messages = list(self.history) + [{
                            "role": "system",
                            "content": "Amplía la respuesta anterior. No uses una confirmación genérica. Da el resultado concreto, el motivo o el siguiente paso útil. No muestres razonamiento interno."
                        }]
                        try:
                            richer = self._chat(retry_messages, tools=None, think=False, temperature=0.3)
                            richer_text = str(getattr(getattr(richer, "message", None), "content", "") or "").strip()
                            if richer_text:
                                answer = richer_text
                        except Exception:
                            pass

                    # Final deep response: let the council review the verified
                    # tool results before JARVIS speaks. This keeps execution local
                    # while making the final answer multi-model reviewed.
                    if deep and self.ai_manager.mode == "AUTO" and self.ai_manager.council_mode != "OFF":
                        try:
                            reviewed = self._chat(self.history, tools=None, think=True, temperature=0.18)
                            reviewed_text = str(getattr(getattr(reviewed, "message", None), "content", "") or "").strip()
                            if reviewed_text:
                                answer = reviewed_text
                        except Exception:
                            pass

                    self.history.append({"role": "assistant", "content": answer})
                    if len(self.history) > 30:
                        self.history = [self.history[0]] + self.history[-28:]
                    self._schedule_reflection(text, answer)
                    return answer
                self.history.append(message)
                for call in calls:
                    name = getattr(call.function, "name", "")
                    args = getattr(call.function, "arguments", {}) or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    try:
                        result = execute_tool(name, **args)
                    except Exception as exc:
                        result = f"ERROR al ejecutar {name}: {exc}"
                    result_text = str(result)
                    recovery = self._recover_code_error(text, name, result_text)
                    if recovery:
                        result_text += "\n" + recovery
                    failed = self._is_failure(result_text)
                    if failed:
                        self.learning.record_failure(text, name, result_text)
                        self.last_learning_event = f"ERROR APRENDIDO // {name}"
                        recovery = self._attempt_recovery(text, name, args, result_text, deep=bool(deep))
                        if recovery:
                            result_text += f"\nRECUPERACIÓN VERIFICADA: {recovery}"
                    else:
                        self.learning.record_success(text, name, result_text)
                        self.last_learning_event = f"EXPERIENCIA GUARDADA // {name}"
                    self.history.append({"role": "tool", "tool_name": name, "content": result_text})
                response = self._chat(self.history, tools=self.tools, think=bool(deep))
            return "Detuve la cadena porque superó el límite seguro de pasos."
        except Exception as exc:
            return f"No pude completar la solicitud: {exc}"
