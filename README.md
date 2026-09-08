# J.A.R.V.I.S. — Mission Control

Asistente personal para Windows con **un solo agente**, Gemini como cerebro principal y Ollama como alternativa local.

La diferencia importante es que JARVIS no se limita a contestar: puede observar puntualmente la pantalla y ejecutar acciones visibles dentro de aplicaciones y páginas mediante un ciclo acotado **OBSERVE → DECIDE → ACT → OBSERVE**.

## Arquitectura

```text
Voz / texto
    ↓
JARVIS Brain
    ├── Gemini
    └── Ollama
    ↓
Intent / herramienta
    ├── herramientas Windows
    ├── navegador y servicios
    ├── Teams
    └── Computer Use
             ↓
      captura puntual
             ↓
        visión Gemini
             ↓
        acción visible
             ↓
        nueva captura
             ↓
         resultado
```

La pantalla es la fuente de verdad para Computer Use. JARVIS no usa registro oculto de teclas ni vigilancia continua.

## Computer Use

Puedes dar órdenes naturales como:

- `abre Teams personal`
- `abre Teams y busca a Majo`
- `abre Google y busca noticias de tecnología`
- `entra a esta web y pulsa el botón que dice continuar`
- `abre la aplicación y rellena el formulario`
- `haz esto dentro de la aplicación`
- `mira la pantalla y dime qué aparece`

Para una tarea visual, el agente puede realizar hasta un número limitado de ciclos. Si no puede identificar con seguridad un elemento, se detiene en lugar de hacer clic a ciegas.

Las acciones externas —enviar mensajes, correos, publicar, comprar o acciones destructivas— quedan detrás de confirmación humana.

## Teams

`Teams` personal es el comportamiento predeterminado. Las palabras `educativo`, `colegio`, `escuela` o `institucional` seleccionan Teams educativo.

Ejemplo:

```text
entra a Teams personal, busca a Majo G y escríbele hola
```

JARVIS prepara el mensaje y espera una confirmación antes de enviarlo.

## Visión

```text
mira la pantalla
```

captura una imagen puntual y la analiza con Gemini. La captura no se realiza continuamente.

## Voz

`faster-whisper` procesa la entrada localmente. `pyttsx3` funciona como salida de voz local. ElevenLabs queda como opción, no como requisito.

## Gemini

Configura `.env`:

```env
JARVIS_PROVIDER=gemini
GEMINI_API_KEY=tu_clave
GEMINI_MODEL=gemini-2.5-flash
```

JARVIS consulta los modelos disponibles para la clave y evita depender de un modelo antiguo que ya no exista.

## Ollama

```env
JARVIS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

Ollama funciona como proveedor local del mismo agente, no como otro agente.

## Instalación

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Copia `.env.example` a `.env` y completa la clave de Gemini si vas a usar Gemini.

## Ejecutar en Windows

```bat
cd C:\Users\juans\Desktop\Jarvis-main
py main.py
```

No uses `py mainpy`: el archivo se llama `main.py`.

## Estructura principal

```text
src/jarvis/
├── brain.py              # Gemini/Ollama + visión
├── computer_use.py       # mouse, teclado y capturas visibles
├── computer_agent.py     # OODA visual para actuar dentro de apps/webs
├── command_router.py     # herramientas deterministas
├── agent_protocol.py     # confirmaciones y límites
├── agent_orchestrator.py # planificación
├── reasoning_layer.py    # esfuerzo y verificación
├── task_planner.py       # planes de tareas
├── teams_automation.py   # Teams visible
├── voice_engine.py       # voz
├── memory.py             # memoria local
└── hud_v4.py             # Mission Control Tkinter
```

## Inspiración

La arquitectura toma ideas generales de asistentes agentic: pipeline de herramientas, visión, memoria, rutinas, auditoría, aprobaciones y una interfaz Mission Control. No se copian código, assets ni texto propietario de terceros.

La referencia de Jarvis AI Assistant destaca precisamente un flujo de intención → herramientas → progreso → aprobación → resultado, además de Computer Use, navegador, memoria y rutinas. citeturn0view0

El proyecto clásico de Jarvis para Linux también sirve como referencia histórica de un asistente Python orientado a ejecutar tareas del PC y ampliar funcionalidades mediante módulos. citeturn1view0

## Seguridad

No se implementa vigilancia oculta, captura de credenciales, registro de teclas ni ejecución de shell arbitrario generado por el modelo. Las acciones externas y destructivas requieren aprobación explícita.
