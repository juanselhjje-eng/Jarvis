# J.A.R.V.I.S. BETA 0.2

Asistente personal para Windows, local-first, con **un solo agente de IA**. Puedes hablarle de forma natural; no necesitas aprender comandos.

## Cómo funciona

```text
Tu voz o texto
      ↓
   JARVIS
      ↓
 JarvisBrain
 ┌────┴────┐
Ollama   Claude
      ↓
Herramientas deterministas
      ↓
Acción real / resultado
      ↓
Respuesta + voz
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

Las acciones sensibles, como enviar mensajes, deben tener confirmación explícita antes de ejecutarse. Las integraciones de Gmail/Teams todavía no están implementadas como automatización completa.

## Voz

### Entrada

`faster-whisper` funciona localmente para convertir tu voz en texto. Las palabras de activación por defecto son `Jarvis` y `Viernes`.

### Salida

La voz principal usa **ElevenLabs**. Si no está configurado o la API falla, JARVIS intenta utilizar `pyttsx3` como respaldo local.

La configuración está en `.env`:

```env
JARVIS_TTS=elevenlabs
ELEVENLABS_API_KEY=tu_clave
ELEVENLABS_VOICE_ID=W5JElH3dK1UYYAiHH7uh
ELEVENLABS_MODEL=eleven_multilingual_v2
ELEVENLABS_OUTPUT_FORMAT=pcm_22050
```

`pcm_22050` permite reproducir el audio directamente con `sounddevice` sin depender de un reproductor externo. ElevenLabs también ofrece otros formatos y modelos; la configuración se mantiene en `.env` para poder cambiarlos sin modificar el código.

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
- `voice_engine.py` — reconocimiento local y TTS de ElevenLabs con respaldo local.
- `memory.py` — memoria persistente local.
- `hud.py` — interfaz gráfica futurista basada en Tkinter.

Se eliminó el antiguo stack de agentes/orquestadores para que el repositorio refleje la arquitectura actual y no mantenga código muerto o contradictorio.

## Seguridad

JARVIS no debe realizar vigilancia oculta ni registrar teclas de forma encubierta. Las automatizaciones de correo, mensajería y cambios importantes deben verificarse antes de confirmar una acción irreversible.
