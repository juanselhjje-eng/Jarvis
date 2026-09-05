# J.A.R.V.I.S.

Asistente personal para Windows, local-first, con **un solo agente de IA**. Puedes hablarle de forma natural; no necesitas aprender comandos.

## Cómo funciona

```text
Tu voz
  ↓
"Jarvis, abre Google"
  ↓
JARVIS / JarvisBrain
  ├── Ollama (local)
  └── Claude API (opcional)
  ↓
Herramientas
  ├── Windows
  ├── navegador
  ├── archivos
  ├── memoria
  ├── Gmail / Teams (integraciones)
  └── documentos
```

Ollama y Claude son **proveedores del mismo cerebro**, no agentes diferentes.

## Ejemplos de órdenes

- `Jarvis, abre Google.`
- `Jarvis, abre Gmail.`
- `Jarvis, usa Claude.`
- `Jarvis, usa Ollama.`
- `Jarvis, busca información sobre la fotosíntesis.`
- `Jarvis, recuerda que mañana tengo que entregar sociales.`
- `Jarvis, ¿qué recuerdas?`
- `Jarvis, revisa mi PC.`
- `Jarvis, abre Teams.`
- `Jarvis, escríbele a Pepe por Gmail y dile hola.`

Las acciones que modifican o envían información sensible deben tener una confirmación explícita antes de ejecutarse.

## Voz

JARVIS utiliza `faster-whisper` localmente para transcribir voz y `pyttsx3` para responder. El programa queda escuchando en ciclos y solo procesa una orden cuando detecta una palabra de activación, por defecto `Jarvis` o `Viernes`.

La configuración está en `.env`:

```env
JARVIS_WAKE_WORDS=jarvis,viernes
WHISPER_MODEL=base
```

## Ollama

Instala Ollama en Windows y deja el servicio local disponible. Después descarga el modelo configurado, por ejemplo `llama3.2`.

```env
JARVIS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

## Claude

Claude es opcional. Guarda la API key solamente en `.env`:

```env
ANTHROPIC_API_KEY=tu_clave
CLAUDE_MODEL=claude-sonnet-4-6
```

Nunca subas `.env`, claves, cookies, sesiones de navegador o memoria privada al repositorio.

## Instalación

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copia `.env.example` como `.env` y configura los proveedores que quieras usar.

## Ejecutar

```bat
python main.py
```

O ejecuta `START_JARVIS.bat`.

## Arquitectura

- `main.py` — runtime principal.
- `brain.py` — único cerebro y proveedores Ollama/Claude.
- `command_router.py` — herramientas deterministas y reconocimiento de intenciones simples.
- `voice_engine.py` — escucha y voz local.
- `memory.py` — memoria persistente local.
- `app.py` — compatibilidad para iniciar el mismo runtime.

La arquitectura está preparada para crecer con herramientas de Windows, navegador, documentos, Gmail, Teams, calendario, visión y automatización, sin crear subagentes.

## Seguridad

JARVIS no debe realizar vigilancia oculta ni registrar teclas de forma encubierta. Las automatizaciones de correo, mensajería y cambios importantes deben verificarse antes de confirmar una acción irreversible.
