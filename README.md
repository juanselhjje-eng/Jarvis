# J.A.R.V.I.S.

J.A.R.V.I.S. es un agente de escritorio para Windows construido en Python. La arquitectura actual está enfocada en **Computer Use visible**, planificación, memoria local, voz, Gemini/Ollama y un laboratorio separado para aprendizaje neuronal.

> No es una promesa de una IA que literalmente pueda hacer cualquier cosa. El objetivo es darle una interfaz de herramientas amplia para operar el computador de forma visible y verificable, manteniendo límites claros para acciones externas o destructivas.

## Arquitectura

```text
USUARIO / VOZ / HUD
        │
        ▼
┌───────────────────────┐
│       CORE AGENT      │  Gemini → Ollama fallback
└───────────┬───────────┘
            │
     INTENT / PLAN / POLICY
            │
     ┌──────┴────────┐
     ▼               ▼
DETERMINISTIC     COMPUTER USE
TOOLS             OBSERVE → DECIDE → ACT → VERIFY
     │               │
     └──────┬────────┘
            ▼
      RESULT / MEMORY
            │
            ▼
       MISSION CONTROL

Neural Lab queda aislado del runtime:
DATA → MLP → TRAIN → EVALUATE → SAVE
```

## Capacidades actuales

- **Gemini como cerebro principal** y **Ollama como fallback/local**.
- Descubrimiento de modelos Gemini compatibles en lugar de asumir que un modelo antiguo existe. La API de Gemini permite enumerar modelos y sus acciones soportadas. urlGemini Models APIhttps://ai.google.dev/api/models?hl=es-419
- **Computer Use visual**: captura puntual de pantalla, clic, movimiento, escritura, atajos y espera.
- **OODA acotado**: observa, decide, actúa y vuelve a observar para corregir el siguiente paso.
- Puede trabajar dentro de aplicaciones y webs visibles cuando la interfaz está disponible.
- Preflight para abrir aplicaciones conocidas antes de una misión visual compleja.
- Confirmación humana antes de enviar/publicar/comprar/eliminar o ejecutar acciones externas/destructivas.
- Confirmación pendiente reanudable con órdenes como `sí envíalo` o cancelación.
- Escritura Unicode mediante pegado visible para texto con tildes y caracteres españoles.
- Voz con reconocimiento y TTS local/compatible.
- Memoria local sin guardar contraseñas, cookies, tokens ni claves API.
- Mission Control nativo Tkinter con telemetría, arquitectura, OODA, eventos, aprendizaje y consola interactiva.
- **Neural Lab**: crea y entrena pequeños MLP locales, mide pérdida/accuracy y guarda los pesos en `data/neural_lab/`. No modifica el código de JARVIS ni se sustituye a sí mismo silenciosamente.

La API estándar de generación de Gemini se usa mediante `client.models.generate_content(...)`. urlGemini Generate Contenthttps://ai.google.dev/api/generate-content

## Comandos de ejemplo

```text
revisa mi pc
abre chrome
abre teams personal
mira la pantalla
abre chrome y busca documentación de Python
entra a Teams, busca a Majo G y escribe hola
sí envíalo
crea una red neuronal
estado del neural lab
usa ollama
usa gemini
esfuerzo alto
limpiar conversación
```

Para una tarea visual compleja, JARVIS debe tener la aplicación o página visible. Si una misión necesita enviar algo, la ejecución se detiene antes de la acción externa y solicita confirmación.

## Aprendizaje neuronal

El Neural Lab es un componente experimental separado. Por ejemplo:

```text
Tú: crea una red neuronal
JARVIS: Neural Lab completado. Arquitectura [2, 8, 8, 2] ...
```

Esto permite experimentar con redes entrenables sin convertir el propio código del agente en un objetivo de auto-modificación. En una siguiente fase se pueden añadir datasets locales, validación, checkpoints, métricas y modelos especializados sin poner el runtime principal en riesgo.

## Seguridad operacional

El agente está diseñado para automatizar la interfaz visible, no para actuar como malware. No incluye keylogging oculto, captura de credenciales, robo de cookies/tokens, vigilancia continua de pantalla ni ejecución arbitraria de shell desde el modelo.

Las acciones de comunicación y las acciones destructivas requieren una compuerta de confirmación explícita.

## Estructura principal

```text
main.py
src/jarvis/
├── brain.py             # Gemini/Ollama
├── command_router.py    # herramientas deterministas
├── computer_use.py      # control visible del escritorio
├── computer_agent.py    # bucle visual OODA
├── neural_lab.py        # redes neuronales locales experimentales
├── hud_v5.py            # Mission Control interactivo
├── memory.py            # memoria local
├── system_control.py    # Windows
├── teams_automation.py  # Teams
├── reasoning_layer.py   # esfuerzo/verificación
├── agent_protocol.py    # política de riesgo
└── voice_engine.py      # voz
```

## Instalación

En Windows:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
py main.py
```

Configura `GEMINI_API_KEY` en `.env` si quieres Gemini. No pegues la clave en el chat ni la subas a GitHub.

## Importante sobre el error de `ControlLoop`

Si aparece un traceback que menciona rutas como `src\\jarvis\\execution\\loop.py` o `src\\jarvis\\core\\runtime.py`, estás ejecutando una copia local antigua de JARVIS. La arquitectura actual usa `src/jarvis/execution.py` y no importa el runtime desde `src/jarvis/__init__.py`.

Después de actualizar el proyecto, la prueba de arranque debe hacerse desde la carpeta que contiene el `main.py` actual:

```bat
cd C:\Users\juans\Desktop\Jarvis
py main.py
```

Si tu carpeta local conserva archivos antiguos, reemplaza la carpeta por la versión actual del repositorio en vez de mezclar los árboles `core/`, `execution/` y `providers/` antiguos con `src/jarvis/` actual.
