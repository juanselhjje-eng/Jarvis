from tools.system_tools import (
    open_application, open_url, open_folder, open_file,
    create_folder, create_file, append_file, list_folder, read_file,
    get_system_info, scan_local_music, play_local_music,
    open_google_search, open_google_images, type_text, press_keys,
    move_mouse, click_mouse, open_workspace, inspect_code, self_repair_code, audit_jarvis_code,
    run_program, edit_text_file, generate_image,
)
from plugins.document_tools import (
    import_file, copy_file, move_file, organize_folder, read_pdf, pdf_merge, pdf_split, pdf_add_text,
    read_docx, append_docx, create_docx, read_xlsx, write_xlsx_cell, read_pptx, image_info, extract_archive,)

TOOLS = {
    "open_application": {
        "function": open_application,
        "description": "Abre una aplicación instalada en Windows y verifica que Windows la haya aceptado.",
        "parameters": {"name": {"type": "string", "description": "Nombre de la aplicación."}},
    },
    "open_url": {
        "function": open_url,
        "description": "Abre una URL en el navegador.",
        "parameters": {"url": {"type": "string", "description": "URL completa."}},
    },
    "open_workspace": {
        "function": open_workspace,
        "description": "Abre el workspace de JARVIS en el Explorador de Windows.",
        "parameters": {},
    },
    "open_folder": {
        "function": open_folder,
        "description": "Abre una carpeta de Windows.",
        "parameters": {"path": {"type": "string", "description": "Ruta."}},
    },
    "open_file": {
        "function": open_file,
        "description": "Abre un archivo con su programa predeterminado.",
        "parameters": {"path": {"type": "string", "description": "Ruta."}},
    },
    "create_folder": {
        "function": create_folder,
        "description": "Crea una carpeta. Las rutas relativas usan workspace.",
        "parameters": {"path": {"type": "string", "description": "Ruta."}},
    },
    "create_file": {
        "function": create_file,
        "description": "Crea un archivo de texto. Las rutas relativas usan workspace.",
        "parameters": {
            "path": {"type": "string", "description": "Ruta o nombre."},
            "content": {"type": "string", "description": "Contenido."},
        },
    },
    "append_file": {
        "function": append_file,
        "description": "Añade texto al final de un archivo.",
        "parameters": {
            "path": {"type": "string", "description": "Ruta."},
            "content": {"type": "string", "description": "Texto."},
        },
    },
    "list_folder": {
        "function": list_folder,
        "description": "Lista archivos y carpetas.",
        "parameters": {"path": {"type": "string", "description": "Ruta opcional."}},
    },
    "read_file": {
        "function": read_file,
        "description": "Lee un archivo de texto.",
        "parameters": {"path": {"type": "string", "description": "Ruta."}},
    },
    "system_info": {
        "function": get_system_info,
        "description": "Obtiene CPU, RAM y disco.",
        "parameters": {},
    },
    "scan_local_music": {
        "function": scan_local_music,
        "description": "Busca música localmente sin abrir Google ni depender del navegador.",
        "parameters": {},
    },
    "play_local_music": {
        "function": play_local_music,
        "description": "Reproduce una canción local con el reproductor predeterminado de Windows.",
        "parameters": {"query": {"type": "string", "description": "Canción o artista."}},
    },
    "google_search": {
        "function": open_google_search,
        "description": "Busca en Google solo si el usuario lo solicita explícitamente.",
        "parameters": {"query": {"type": "string", "description": "Consulta."}},
    },
    "google_image_search": {
        "function": open_google_images,
        "description": "Busca imágenes en Google solo si el usuario lo solicita explícitamente.",
        "parameters": {"query": {"type": "string", "description": "Consulta."}},
    },
    "type_text": {
        "function": type_text,
        "description": "Escribe texto en la ventana actualmente enfocada.",
        "parameters": {
            "text": {"type": "string", "description": "Texto a escribir."},
            "interval": {"type": "number", "description": "Intervalo entre caracteres."},
        },
    },
    "press_keys": {
        "function": press_keys,
        "description": "Pulsa una tecla o combinación como ctrl+s, alt+tab o enter.",
        "parameters": {"keys": {"type": "string", "description": "Teclas separadas por +."}},
    },
    "move_mouse": {
        "function": move_mouse,
        "description": "Mueve el cursor a una posición de pantalla.",
        "parameters": {
            "x": {"type": "integer", "description": "Coordenada X."},
            "y": {"type": "integer", "description": "Coordenada Y."},
            "duration": {"type": "number", "description": "Duración."},
        },
    },
    "run_program": {
        "function": run_program,
        "description": "Ejecuta un programa de Windows sin shell y devuelve su resultado. Acepta 'executable' y también 'path' por compatibilidad con llamadas antiguas; bloquea comandos de borrado.",
        "parameters": {
            "executable": {"type": "string", "description": "Programa o ruta al ejecutable. Puede omitirse si se proporciona path."},
            "arguments": {"type": "string", "description": "Argumentos del programa."},
            "working_dir": {"type": "string", "description": "Directorio de trabajo opcional."},
            "timeout": {"type": "integer", "description": "Tiempo máximo en segundos."},
            "path": {"type": "string", "description": "Alias compatible con versiones anteriores: programa o ejecutable."},
        },
    },
    "edit_text_file": {
        "function": edit_text_file,
        "description": "Edita un archivo de texto y conserva un respaldo .bak; no elimina el original.",
        "parameters": {
            "path": {"type": "string", "description": "Archivo."},
            "instruction": {"type": "string", "description": "Qué cambio se necesita."},
            "content": {"type": "string", "description": "Contenido nuevo completo."},
        },
    },
    "generate_image": {
        "function": generate_image,
        "description": "Genera una imagen con IA usando la API configurada y la guarda en generated/images.",
        "parameters": {
            "prompt": {"type": "string", "description": "Descripción de la imagen."},
            "filename": {"type": "string", "description": "Nombre del PNG de salida."},
            "size": {"type": "string", "description": "Tamaño soportado por el modelo, por ejemplo 1024x1024."},
        },
    },
    "audit_jarvis_code": {
        "function": audit_jarvis_code,
        "description": "Audita el código Python de JARVIS y repara automáticamente errores de sintaxis verificables.",
        "parameters": {"repair": {"type": "boolean", "description": "Si debe reparar errores encontrados."}},
    },
    "inspect_code": {
        "function": inspect_code,
        "description": "Comprueba un archivo Python sin modificarlo y devuelve errores de sintaxis.",
        "parameters": {"path": {"type": "string", "description": "Ruta del archivo Python."}},
    },
    "self_repair_code": {
        "function": self_repair_code,
        "description": "Crea un respaldo, intenta reparar un archivo de código con la IA local, valida y hace rollback si falla.",
        "parameters": {
            "path": {"type": "string", "description": "Archivo de código a reparar."},
            "error": {"type": "string", "description": "Error o fallo observado."},
        },
    },
    "click_mouse": {
        "function": click_mouse,
        "description": "Hace clic con el mouse en la posición actual.",
        "parameters": {
            "button": {"type": "string", "description": "left, right o middle."},
            "clicks": {"type": "integer", "description": "Cantidad de clics."},
        },
    },
    "import_file": {
        "function": import_file, "description": "Importa un archivo al workspace sin eliminar el original.",
        "parameters": {"path":{"type":"string","description":"Ruta del archivo a importar."},"destination":{"type":"string","description":"Carpeta destino."}},
    },
    "copy_file": {
        "function": copy_file, "description": "Copia un archivo sin borrar el original.",
        "parameters": {"source":{"type":"string","description":"Origen."},"destination":{"type":"string","description":"Destino."}},
    },
    "move_file": {
        "function": move_file, "description": "Mueve un archivo sin eliminar datos; crea destino si hace falta.",
        "parameters": {"source":{"type":"string","description":"Origen."},"destination":{"type":"string","description":"Destino."}},
    },
    "organize_folder": {
        "function": organize_folder, "description": "Organiza archivos por tipo en subcarpetas sin eliminar ninguno.",
        "parameters": {"path":{"type":"string","description":"Carpeta."}},
    },
    "read_pdf": {
        "function": read_pdf, "description": "Lee y extrae texto de un PDF.",
        "parameters": {"path":{"type":"string","description":"PDF."}},
    },
    "pdf_merge": {
        "function": pdf_merge, "description": "Combina varios PDFs en uno nuevo.",
        "parameters": {"output":{"type":"string","description":"PDF de salida."},"files":{"type":"array","items":{"type":"string"},"description":"PDFs a combinar."}},
    },
    "pdf_split": {
        "function": pdf_split, "description": "Divide un PDF en páginas individuales.",
        "parameters": {"path":{"type":"string","description":"PDF."},"output_dir":{"type":"string","description":"Carpeta de salida."}},
    },
    "read_docx": {
        "function": read_docx, "description": "Lee el texto de un documento DOCX.",
        "parameters": {"path":{"type":"string","description":"DOCX."}},
    },
    "append_docx": {
        "function": append_docx, "description": "Añade un párrafo a un DOCX existente.",
        "parameters": {"path":{"type":"string","description":"DOCX."},"text":{"type":"string","description":"Texto."}},
    },
    "read_xlsx": {
        "function": read_xlsx, "description": "Lee una hoja de cálculo XLSX.",
        "parameters": {"path":{"type":"string","description":"XLSX."},"sheet":{"type":"string","description":"Hoja opcional."}},
    },
    "write_xlsx_cell": {
        "function": write_xlsx_cell, "description": "Modifica una celda XLSX y guarda el archivo.",
        "parameters": {"path":{"type":"string","description":"XLSX."},"cell":{"type":"string","description":"Celda, por ejemplo A1."},"value":{"description":"Valor nuevo."},"sheet":{"type":"string","description":"Hoja opcional."}},
    },
    "read_pptx": {
        "function": read_pptx, "description": "Extrae texto de una presentación PPTX.",
        "parameters": {"path":{"type":"string","description":"PPTX."}},
    },
    "image_info": {
        "function": image_info, "description": "Analiza formato, tamaño y modo de una imagen.",
        "parameters": {"path":{"type":"string","description":"Imagen."}},
    },
    "pdf_add_text": {
        "function": pdf_add_text, "description": "Añade texto a una página de un PDF y guarda una copia nueva; no toca el original.",
        "parameters": {"path":{"type":"string","description":"PDF original."},"output":{"type":"string","description":"PDF de salida."},"text":{"type":"string","description":"Texto."},"page":{"type":"integer","description":"Página empezando en 1."},"x":{"type":"number","description":"Coordenada X."},"y":{"type":"number","description":"Coordenada Y."}},
    },
    "create_docx": {
        "function": create_docx, "description": "Crea un documento DOCX real.",
        "parameters": {"path":{"type":"string","description":"Ruta."},"title":{"type":"string","description":"Título."},"content":{"type":"string","description":"Contenido."}},
    },
    "extract_archive": {
        "function": extract_archive, "description": "Extrae ZIP al workspace sin borrar el archivo comprimido.",
        "parameters": {"path":{"type":"string","description":"ZIP."},"destination":{"type":"string","description":"Destino."}},
    },
}


def get_tool(tool_name: str):
    item = TOOLS.get(tool_name)
    return item["function"] if item else None


def list_tools():
    return {n: {"description": d["description"], "parameters": d["parameters"]} for n, d in TOOLS.items()}


def _normalize_tool_args(tool_name: str, kwargs: dict) -> dict:
    """Accept safe legacy argument names emitted by older prompts/models.

    Old JARVIS versions used `path` for run_program while the current function
    uses `executable`. Normalize it at the boundary so a stale model call does
    not become a Python TypeError.
    """
    args = dict(kwargs or {})
    if tool_name == "run_program":
        if not args.get("executable") and args.get("path"):
            args["executable"] = args["path"]
        args.pop("path", None)
        args.setdefault("arguments", "")
        args.setdefault("working_dir", "")
        args.setdefault("timeout", 30)
    return args


def execute_tool(tool_name: str, **kwargs):
    fn = get_tool(tool_name)
    if fn is None:
        raise ValueError(f"La herramienta '{tool_name}' no existe.")
    return fn(**_normalize_tool_args(tool_name, kwargs))


def get_tool_descriptions():
    return "\n".join(
        f"- {n}: {d['description']} Parámetros: {', '.join(d['parameters']) or 'sin parámetros'}"
        for n, d in TOOLS.items()
    )


def ollama_tool_definitions():
    return [{
        "type": "function",
        "function": {
            "name": name,
            "description": data["description"],
            "parameters": {
                "type": "object",
                "properties": data["parameters"],
                "required": list(data["parameters"].keys()),
            },
        },
    } for name, data in TOOLS.items()]
