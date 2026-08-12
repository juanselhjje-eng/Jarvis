# JARVIS

Asistente personal local para Windows con memoria persistente, consejo multi-IA, herramientas de escritorio, documentos, voz, visión y reparación controlada.

## 🚀 Instalación rápida

### 1. Descargar el proyecto

```bat
git clone https://github.com/juanselhjje-eng/Jarvis.git
cd Jarvis
```

### 2. Crear el entorno de Python

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements_gui.txt
```

### 3. Crear `.env`

En la carpeta principal `JARVIS`, crea un archivo llamado exactamente:

```text
.env
```

**No lo llames `.env.txt`.**

Puedes crearlo desde CMD con:

```bat
notepad .env
```

Si Windows pregunta si quieres crear el archivo, acepta.

---

# 🔑 Configurar las IAs

Dentro de `.env` coloca únicamente las claves de las APIs que tengas.

Ejemplo:

```env
OPENAI_API_KEY=TU_CLAVE_AQUI
OPENAI_MODEL=gpt-5.1

ANTHROPIC_API_KEY=TU_CLAVE_AQUI
CLAUDE_MODEL=claude-sonnet-4-20250514

GEMINI_API_KEY=TU_CLAVE_AQUI
GEMINI_MODEL=TU_MODELO_GEMINI

XAI_API_KEY=TU_CLAVE_AQUI
GROK_MODEL=TU_MODELO_GROK

JARVIS_AI=AUTO
```

Si no tienes una API, deja esa variable vacía:

```env
GEMINI_API_KEY=
```

JARVIS utilizará automáticamente los proveedores que estén configurados.

## ⚠️ MUY IMPORTANTE

**Nunca publiques tus API keys en GitHub, Discord, capturas de pantalla ni README.**

El archivo `.env` debe permanecer únicamente en tu PC.

Si accidentalmente publicaste una API key, revócala inmediatamente desde el proveedor y genera una nueva.

---

# 🧠 ¿Qué hace JARVIS con las diferentes IAs?

JARVIS no necesita que todas las APIs estén configuradas para funcionar.

Cuando varias están disponibles, puede utilizarlas como especialistas:

```text
                 JARVIS
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
       OpenAI    Claude    Gemini
          │         │         │
          └─────────┼─────────┘
                    ↓
                  Grok
                    ↓
             decisión final
```

La aplicación puede utilizar diferentes proveedores según la tarea y conservar el resultado útil en su memoria local.

---

# 🦙 Modelo local con Ollama

Si quieres que JARVIS también funcione sin depender siempre de APIs externas, instala Ollama y descarga el modelo que tengas configurado.

Después inicia Ollama antes de ejecutar JARVIS.

La configuración del modelo local depende del hardware disponible.

---

# ▶️ Ejecutar JARVIS

Con el entorno virtual activado:

```bat
python app.py
```

---

# 👤 Primera ejecución

En el primer inicio JARVIS puede preguntarte cómo quieres que te llame.

Ese nombre forma parte de tu perfil local y se conserva entre sesiones.

---

# 💾 Memoria

La memoria personal se guarda localmente y no forma parte del repositorio.

La instalación utiliza memoria persistente para conservar información útil entre sesiones, como:

- preferencias;
- contexto de proyectos;
- procedimientos que funcionaron;
- errores y recuperaciones;
- conocimiento aprendido;
- historial necesario para mantener continuidad.

La memoria personal **no debe subirse a GitHub**.

---

# 🌐 Aprendizaje colectivo opcional

JARVIS también tiene una capa de aprendizaje colectivo.

La idea es compartir únicamente **lecciones sanitizadas y verificadas**, no conversaciones privadas completas ni API keys.

```text
JARVIS A ─┐
JARVIS B ─┤
JARVIS C ─┼──→ lecciones verificadas ──→ base colectiva
JARVIS D ─┘                              │
                                        ↓
                              futuros JARVIS
```

Esto no significa que las APIs externas reentrenen automáticamente sus modelos después de cada mensaje. JARVIS aprende a nivel de aplicación reutilizando experiencias, soluciones y procedimientos verificados.

Para una futura versión comercial, la memoria colectiva debería utilizar una base de datos separada —por ejemplo Supabase— con aislamiento por usuario y consentimiento explícito.

---

# 🖥️ Control del computador

JARVIS puede trabajar con herramientas de escritorio disponibles en la instalación para:

- observar la pantalla;
- capturar pantalla;
- OCR;
- enfocar ventanas;
- teclado;
- ratón;
- navegador;
- aplicaciones;
- archivos y documentos;
- verificación de resultados;
- recuperación ante errores.

Su ciclo de trabajo es:

```text
OBJETIVO
   ↓
OBSERVAR
   ↓
PLANEAR
   ↓
ACTUAR
   ↓
VERIFICAR
   ↓
¿FALLÓ?
 ┌─┴─┐
NO  SÍ
 ↓   ↓
FIN RECUPERAR
     ↓
   REINTENTAR
```

Las reparaciones no deben convertirse en eliminación destructiva automática.

---

# 🎙️ Voz

JARVIS puede utilizar el sistema de voz configurado por la instalación para escuchar y responder.

Las voces disponibles dependen del motor TTS instalado y de las voces que tenga Windows.

---

# 👁️ Visión

Las funciones de visión dependen del proveedor y de las herramientas instaladas. Para OCR local, Windows necesita una instalación funcional de Tesseract OCR además de `pytesseract`.

---

# 📁 Archivos importantes

```text
JARVIS/
├── app.py
├── core/
├── providers/
├── tools/
├── plugins/
├── ui/
├── memory/
├── requirements.txt
├── requirements_gui.txt
└── .env                 ← privado, NO subir
```

---

# 🛡️ Seguridad

Antes de publicar una instalación de JARVIS:

1. No incluyas `.env`.
2. No incluyas bases de datos de memoria.
3. No incluyas tokens ni cookies.
4. No incluyas sesiones de navegador.
5. No compartas API keys.
6. Usa `.env.example` para documentar variables.

Puedes comprobar antes de hacer `git push`:

```bat
git status
```

Si aparece `.env`, memoria local, bases de datos o archivos privados, **no hagas push todavía**.

---

# 🧪 Comprobar configuración

Con el entorno virtual activo puedes comprobar que Python puede leer `.env`:

```bat
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI=', bool(os.getenv('OPENAI_API_KEY'))); print('ANTHROPIC=', bool(os.getenv('ANTHROPIC_API_KEY'))); print('GEMINI=', bool(os.getenv('GEMINI_API_KEY'))); print('XAI=', bool(os.getenv('XAI_API_KEY')))"
```

Para comprobar los modelos:

```bat
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI MODEL:', os.getenv('OPENAI_MODEL')); print('CLAUDE MODEL:', os.getenv('CLAUDE_MODEL')); print('GEMINI MODEL:', os.getenv('GEMINI_MODEL')); print('GROK MODEL:', os.getenv('GROK_MODEL')); print('JARVIS AI:', os.getenv('JARVIS_AI'))"
```

---

# ❓ Solución de problemas

### Windows dice que no puede abrir `.env`

No intentes abrirlo como si fuera una aplicación. Ejecuta:

```bat
notepad .env
```

### Aparece `OPENAI=False`

Comprueba que:

- `.env` está dentro de la carpeta del proyecto;
- el archivo no se llama `.env.txt`;
- la variable se llama exactamente `OPENAI_API_KEY`;
- la clave está después de `=`;
- reiniciaste JARVIS después de modificar `.env`.

### Una IA aparece como `False`

Significa que no hay una API key configurada para ese proveedor. Es normal si no la tienes.

---

# 📜 Licencia y uso de APIs

JARVIS es una aplicación que puede conectarse a servicios externos mediante las credenciales proporcionadas por cada usuario.

Cada usuario es responsable de sus propias cuentas, claves, límites de uso y cumplimiento de los términos de los proveedores utilizados.
