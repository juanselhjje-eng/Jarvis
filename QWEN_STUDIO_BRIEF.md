# Prompt maestro para Qwen Studio

Copia TODO el bloque siguiente en Qwen Studio. El repositorio ya está conectado, así que Qwen debe inspeccionar el código real antes de modificarlo.

---

## PROMPT

Eres el ingeniero principal encargado de llevar este repositorio **Jarvis** a una versión mucho más completa, estable, fluida y profesional. El repositorio de GitHub que tienes conectado es la fuente de verdad. **No quiero solamente recomendaciones ni un análisis: quiero que inspecciones el proyecto, modifiques el código real, pruebes lo que puedas y dejes implementadas las mejoras.**

### 1. CONTEXTO DEL PROYECTO

Jarvis es un agente de escritorio para Windows escrito principalmente en Python. Debe sentirse como un verdadero asistente de escritorio tipo JARVIS, no como un chatbot con una ventana.

Objetivos principales:

- Un solo agente JARVIS como cerebro/orquestador.
- **Gemini como IA principal.**
- **Ollama como fallback/local**, actualmente con llama3.2.
- Memoria persistente local.
- Voz de entrada y salida.
- Control visible del PC.
- Control del navegador y aplicaciones mediante interfaces visibles.
- Computer Use / visión mediante capturas de pantalla.
- Planificación de tareas complejas.
- Sistema de confirmación humana para acciones externas o irreversibles.
- Equipo de subagentes especializados que sean roles internos del mismo JARVIS, no siete cerebros LLM independientes.
- Interfaz nativa Python/Tkinter de aspecto cinematográfico/futurista.
- Sistema de aprendizaje local y Neural Lab.
- Arquitectura modular, mantenible y eficiente.

### 2. IMPORTANTE: INSPECCIONA ANTES DE CAMBIAR

Primero inspecciona TODO el repositorio y entiende la arquitectura actual.

Busca especialmente:

- `main.py`
- `src/jarvis/brain.py`
- `src/jarvis/computer_agent.py`
- `src/jarvis/computer_use.py`
- `src/jarvis/teams_automation.py`
- `src/jarvis/command_router.py`
- `src/jarvis/agent_orchestrator.py`
- `src/jarvis/task_planner.py`
- `src/jarvis/reasoning_layer.py`
- `src/jarvis/agent_protocol.py`
- `src/jarvis/memory.py`
- `src/jarvis/neural_lab.py`
- `src/jarvis/desktop_control.py`
- `src/jarvis/voice_engine.py`
- `src/jarvis/hud_v5.py`
- `src/jarvis/hud_v6.py`
- `src/jarvis/subagents.py`
- `requirements.txt`
- `.env.example`
- workflows de GitHub Actions.

También identifica código antiguo o duplicado que pueda estar causando imports circulares, rutas antiguas o módulos incompatibles. **No mezcles dos arquitecturas distintas.** Debe existir una arquitectura limpia y única.

### 3. SUBAGENTES: IMPLEMENTA EL EQUIPO COMPLETO

Quiero un equipo profesional de roles internos:

1. **ORCHESTRATOR** — recibe la misión, coordina todo y decide qué rol actúa.
2. **PLANNER** — divide una misión compleja en pasos verificables.
3. **VISION** — interpreta capturas y reconoce controles visibles.
4. **DESKTOP** — ejecuta mouse, teclado, aplicaciones y navegación visible.
5. **RESEARCH** — búsqueda, comparación y recopilación de información.
6. **MEMORY** — recupera contexto y guarda aprendizajes/preferencias útiles.
7. **VERIFY** — comprueba que una acción realmente terminó correctamente.
8. **TEAMS SPECIALIST** — flujo específico y robusto para Microsoft Teams.
9. **BROWSER SPECIALIST** — navegación web visible y recuperación ante cambios de interfaz.
10. **SYSTEM SPECIALIST** — estado del PC, aplicaciones y optimización segura.

Estos roles deben compartir el mismo cerebro/configuración de JARVIS cuando sea necesario. **No multipliques llamadas a Gemini innecesariamente.** Prioriza herramientas deterministas antes de usar visión LLM.

El HUD debe mostrar visualmente qué roles están activos, su estado y qué etapa de la misión están ejecutando.

### 4. PROBLEMA CRÍTICO DE TEAMS QUE DEBES SOLUCIONAR

El flujo real probado fue:

> “entra a Teams en Google, mira a los q les he escrito, entra a la que se llama Majo G y dile hola”

JARVIS logró entrar a Teams personal y llegó a la lista de chats, pero **seleccionó a Samuel en lugar de Majo G**.

Este es un bug crítico.

Quiero un flujo robusto:

`ORCHESTRATOR -> TEAMS SPECIALIST -> abrir Teams personal -> localizar Majo G -> verificar que el chat abierto sea Majo G -> preparar mensaje -> HUMAN GATE -> enviar solamente después de confirmación`

Reglas obligatorias:

- Si el usuario pide `Majo G`, jamás seleccionar `Samuel` u otro contacto parecido.
- El nombre objetivo debe tratarse como una restricción fuerte.
- Antes de hacer clic, comprobar que el objetivo visual corresponde al contacto solicitado.
- Después del clic, tomar una nueva observación y verificar el encabezado/chat abierto.
- Si no se puede confirmar el contacto, detenerse o continuar buscando; nunca adivinar.
- No repetir clics idénticos sobre la misma pantalla.
- No gastar llamadas de Gemini innecesariamente.
- Usar búsqueda/teclado/deterministic automation cuando sea más fiable.
- Una vez confirmado el contacto correcto, detener el bucle de búsqueda y pasar al siguiente paso.
- Preparar el mensaje sin enviarlo.
- El envío requiere confirmación explícita del usuario.
- Frases como `sí`, `si envíalo`, `sí envíalo`, `envíalo`, `mándalo`, `hazlo`, `confirmo`, etc. deben continuar una acción pendiente solamente cuando exista una acción externa pendiente.
- `no`, `cancela`, etc. deben cancelar.

No uses bypass de autenticación, extracción de cookies, robo de tokens, captura de contraseñas ni técnicas ocultas. Usa la sesión visible que ya tenga iniciada el usuario.

### 5. CONTROL DEL CUOTEO DE GEMINI

El sistema actualmente puede consumir demasiado rápido la cuota gratuita de Gemini porque el OODA visual hace muchas llamadas consecutivas.

Implementa un **Vision Budget / Rate Limiter**:

- Limitar llamadas de visión por misión.
- Detectar HTTP 429 / RESOURCE_EXHAUSTED.
- Aplicar backoff.
- Evitar repetir análisis si la pantalla no cambió significativamente.
- Cachear observaciones cuando sea apropiado.
- Dar prioridad a acciones deterministas.
- No entrar en bucles de clic.
- Si Gemini queda temporalmente limitado, informar claramente y usar una estrategia alternativa segura cuando exista.
- No intentar evadir la cuota.

Idealmente añade métricas visibles:

`VISION CALLS / MISSION`, `CACHE HITS`, `429 COOLDOWN`, `STEPS`, `TIME`, `SUCCESS`.

### 6. COMPUTER AGENT / OODA

Mejora el agente visual para que no sea simplemente:

`captura -> Gemini -> clic -> captura -> Gemini -> clic`

Quiero:

`OBSERVE -> UNDERSTAND -> PLAN -> ACT -> VERIFY -> UPDATE STATE`

El estado de misión debe conocer:

- objetivo global
- paso actual
- aplicación actual
- ventana actual
- objetivo visual
- última acción
- resultado
- confianza
- errores
- número de intentos
- evidencia de finalización.

Añade guards contra:

- clic repetido
- objetivo incorrecto
- pantalla sin cambios
- acción fuera de la pantalla
- coordenadas inválidas
- loops
- cambios inesperados de ventana
- pérdida de foco
- respuestas inválidas de Gemini.

Si una acción no puede verificarse, no la marques como completada.

### 7. PLANIFICADOR REAL

Haz que `task_planner.py` y `agent_orchestrator.py` estén realmente conectados al ejecutor.

Ejemplo:

Usuario:
> “Busca apartamentos de menos de X, compáralos, revisa cuáles cumplen mis condiciones y prepara contacto.”

JARVIS debe poder construir una misión con pasos, ejecutar herramientas cuando existan, verificar cada paso y pedir confirmación antes de cualquier comunicación externa.

Usa estados como:

`QUEUED -> PLANNING -> EXECUTING -> VERIFYING -> WAITING_CONFIRMATION -> COMPLETED / FAILED / CANCELLED`

Permite reintentos controlados y recuperación de errores.

### 8. MEMORIA

Mejora la memoria local para que pueda guardar y recuperar:

- hechos
- preferencias
- correcciones del usuario
- contexto de tareas
- resultados
- aprendizajes
- contactos o nombres mencionados durante una misión cuando sea apropiado

Implementa recuperación semántica/local si es razonable sin convertir el proyecto en algo excesivamente pesado. SQLite FTS, embeddings locales u otra solución ligera son opciones.

Debe haber separación entre memoria de conversación temporal y memoria persistente.

Nunca guardes contraseñas, tokens, cookies, claves API ni secretos.

### 9. NEURAL LAB

Mejora el Neural Lab sin afirmar que un grafo visual equivale a entrenamiento real.

Si actualmente existe un grafo derivado de capturas, mantenlo como representación visual, pero separa claramente:

- visual graph
- aprendizaje supervisado real
- métricas
- feedback

Si puedes implementar un pequeño sistema real de aprendizaje local con ejemplos etiquetados, hazlo de forma ligera y mantenible.

### 10. HUD: QUIERO UNA INTERFAZ MUCHO MÁS PROFESIONAL

La interfaz actual debe evolucionar mucho.

Quiero inspiración visual de una interfaz JARVIS cinematográfica:

- fondo casi negro
- espacio/partículas sutiles
- núcleo holográfico central grande
- partículas y anillos orbitales suaves
- cyan/blanco como información principal
- pequeños acentos cálidos solo cuando tengan significado
- tipografía limpia
- mucho espacio negativo
- animaciones fluidas
- microinteracciones
- glow controlado
- sensación de sistema avanzado, no de dashboard genérico.

NO quiero:

- exceso de cajas
- demasiadas líneas
- paneles apretados
- apariencia de plantilla web
- colores chillones
- texto innecesario
- UI que parezca hecha automáticamente.

Debe seguir siendo **native Python/Tkinter**, no reemplazar todo por HTML.

El centro debe ser el núcleo de JARVIS.

Alrededor deben aparecer de forma elegante:

- estado de JARVIS
- misión actual
- actividad de subagentes
- estado de visión
- micrófono
- evidencia
- confirmación humana
- controles esenciales.

Añade animaciones suaves y evita bloquear el hilo de UI.

### 11. RENDIMIENTO Y FLUIDEZ

Optimiza agresivamente donde sea seguro:

- UI siempre en el hilo principal.
- Workers para operaciones pesadas.
- Colas para eventos.
- Debounce/throttle de actualizaciones.
- No recalcular gráficos innecesariamente.
- No tomar capturas si no son necesarias.
- Cachear recursos.
- Reducir llamadas repetidas a Gemini.
- Evitar fugas de threads.
- Cerrar correctamente recursos al salir.
- Evitar loops ocupados.
- Manejar excepciones sin matar la UI.

La aplicación debe sentirse fluida incluso durante una misión larga.

### 12. VOZ

Mantén voz local como opción principal y soporte opcional de ElevenLabs si ya existe.

Mejora:

- activación/desactivación clara del micrófono
- evitar que JARVIS se escuche a sí mismo
- procesamiento por chunks
- estados visibles: MIC OFF / LISTENING / THINKING / SPEAKING
- recuperación ante errores de micrófono
- no capturar audio continuamente cuando el micrófono está desactivado.

### 13. COMMAND ROUTER

Haz que las órdenes naturales sean robustas.

Ejemplos:

- “entra a Teams” -> Teams personal.
- “entra al Teams del colegio” -> Teams educativo.
- “abre Chrome” -> Chrome.
- “mira la pantalla” -> observación puntual.
- “haz clic en...” -> Computer Use.
- “recuerda que...” -> memoria.
- “usa Gemini” -> Gemini.
- “usa Ollama” -> Ollama.

No dependas únicamente de coincidencias frágiles de texto. Usa intención estructurada cuando sea posible.

### 14. SEGURIDAD

Mantén el sistema seguro por diseño.

Siempre requiere confirmación antes de:

- enviar mensajes
- publicar
- comprar
- pagar
- transferir
- borrar información
- acciones irreversibles.

No implementes:

- keyloggers
- robo de cookies
- robo de tokens
- extracción de contraseñas
- bypass de login
- persistencia oculta
- vigilancia oculta
- malware

Las capacidades de ciberseguridad deben ser defensivas: análisis de código, revisión de configuraciones, detección de vulnerabilidades, hardening, laboratorios y pruebas autorizadas.

### 15. CALIDAD DEL CÓDIGO

Haz una revisión completa y mejora:

- imports
- tipos
- dataclasses
- interfaces
- manejo de errores
- logging
- nombres
- duplicación
- circular imports
- módulos muertos
- compatibilidad Python 3.13
- configuración mediante `.env`
- requisitos.

No rompas APIs internas sin actualizar todos los consumidores.

Si hay archivos viejos que provocan conflictos, limpia la arquitectura de forma controlada.

### 16. TESTS

Añade o mejora tests para las partes críticas, especialmente:

- router
- memoria
- confirmation gate
- Teams intent
- Teams contact guard
- ComputerAction parsing
- duplicate-action guard
- planner
- orchestrator
- rate limiter
- configuración.

Si no puedes ejecutar algo por depender de Windows/Gemini/GUI, crea mocks y tests unitarios para la lógica que sí pueda probarse.

### 17. README Y CONFIGURACIÓN

Actualiza README con:

- arquitectura
- instalación
- configuración Gemini/Ollama
- voz
- ejecución
- comandos principales
- Computer Use
- subagentes
- memoria
- seguridad
- troubleshooting
- límites conocidos.

`.env.example` debe reflejar la configuración real y no contener secretos.

### 18. FORMA DE TRABAJAR

No hagas un parche superficial.

Quiero que:

1. inspecciones el repositorio completo;
2. detectes problemas arquitectónicos;
3. diseñes una solución coherente;
4. implementes los cambios reales;
5. revises imports y dependencias;
6. añadas tests;
7. ejecutes las pruebas que puedas;
8. corrijas errores encontrados;
9. revises rendimiento;
10. revises la UI;
11. revises especialmente Teams;
12. dejes el repositorio en un estado ejecutable.

Si encuentras una implementación existente que ya funciona, **mejórala en lugar de reemplazarla innecesariamente**.

No inventes que una función está implementada si no lo está.

No te limites a decirme qué debería hacer: **haz los cambios en el repositorio**.

### 19. PRIORIDAD ABSOLUTA

Ordena el trabajo así:

**P0 — estabilidad**
- eliminar conflictos/circular imports
- asegurar arranque
- asegurar configuración
- evitar crashes.

**P1 — Teams correcto**
- nunca seleccionar el contacto equivocado
- verificación visual
- deterministic-first
- detener búsqueda cuando encuentre el objetivo
- confirmación antes de enviar.

**P2 — Computer Use/OODA**
- guards
- estado
- verificación
- recuperación
- rate limiting Gemini.

**P3 — subagentes**
- equipo visible
- roles coordinados
- un solo cerebro.

**P4 — planner/orchestrator**
- ejecución real de planes.

**P5 — memoria/aprendizaje**
- recuperación y feedback.

**P6 — HUD**
- rediseño cinematográfico y fluido.

**P7 — rendimiento/tests/documentación**
- optimización y calidad final.

### 20. RESULTADO FINAL QUE ESPERO

Quiero que este proyecto termine siendo un **JARVIS de escritorio real**, dentro de los límites técnicos normales de Windows, con:

`VOICE -> JARVIS CORE -> ORCHESTRATOR -> SPECIALIST -> TOOLS -> COMPUTER USE -> VERIFY -> MEMORY`

y un HUD que haga visible ese proceso sin convertirlo en una pantalla llena de paneles.

La aplicación debe sentirse rápida, coherente y profesional.

**Empieza ahora inspeccionando el repositorio y después implementa. No me entregues solamente un plan.**

---
