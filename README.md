# JARVIS

Asistente personal local para Windows con memoria persistente, consejo multi-IA, herramientas de escritorio, documentos, voz, visión y reparación controlada.

## V29

La versión actual añade una capa de **control humano del computador**:

- observar ventana activa, cursor y pantalla;
- capturar pantalla y usar OCR cuando está instalado;
- enfocar ventanas por título;
- escribir, pegar, copiar, atajos de teclado, clic, doble clic, desplazamiento y arrastre;
- esperar a que las aplicaciones reaccionen;
- trabajar por ciclos **observar → actuar → verificar**;
- conservar contexto entre mensajes y respuestas cortas;
- registrar éxitos, errores y recuperaciones en memoria SQLite local;
- consejo multi-IA para planificación y respuestas profundas;
- aprendizaje autónomo por contribuciones independientes de los proveedores disponibles;
- UI neural en español con estado, memoria, consejo y herramientas.

## Seguridad del proyecto

JARVIS no expone `.env`, bases de datos locales ni workspaces al repositorio. La aplicación no registra una herramienta de borrado en su catálogo de acciones. Las reparaciones de código usan respaldo, validación y rollback cuando es posible.

## Instalación

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements_gui.txt
```

Configura las claves de IA en un archivo `.env` local. **Nunca subas ese archivo a GitHub.**

Para el modelo local, inicia Ollama y deja disponible el modelo configurado por el proyecto.

## Ejecutar

```bat
python app.py
```

## Memoria

La memoria se crea localmente en `memory/learning.db`. Esa base no forma parte del repositorio y se reconstruye automáticamente al iniciar.

## OCR

`pytesseract` permite usar OCR, pero Windows también necesita una instalación funcional de Tesseract OCR para que `screen_ocr` pueda leer texto de la pantalla.

## Principio de aprendizaje

Las IAs externas no modifican mágicamente los pesos de Qwen. JARVIS aprende de forma persistente mediante experiencias verificadas, correcciones, recuperaciones, conocimiento y un grafo de nodos/conexiones. Esto permite que una sesión futura reutilice lo aprendido sin fingir un reentrenamiento del modelo base.

## Calidad

GitHub Actions compila los módulos Python y comprueba que no se rastreen secretos ni archivos de memoria/runtime nuevos.
