import re
from tools.registry import execute_tool

OPEN_WORDS = r"(?:abre|abrir|inicia|iniciar|ejecuta|ejecutar|lanza|lanzar)"

class CommandRouter:
    """Rutas rápidas para acciones deterministas. El LLM queda para conversación."""

    def route(self, text: str):
        low = text.strip().lower()

        # Open direct URL BEFORE generic application routing.
        # Otherwise "abre https://..." can be mistaken for an application name.
        m = re.search(r"(?:abre|abrir)\s+(https?://\S+)", low)
        if m:
            return execute_tool("open_url", url=m.group(1))

        # Open well-known websites before application routing.
        # Examples: "abre instagram web", "abre youtube", "entra a github".
        web_aliases = {
            "instagram": "https://www.instagram.com/",
            "instagram web": "https://www.instagram.com/",
            "youtube": "https://www.youtube.com/",
            "youtube web": "https://www.youtube.com/",
            "facebook": "https://www.facebook.com/",
            "facebook web": "https://www.facebook.com/",
            "tiktok": "https://www.tiktok.com/",
            "tiktok web": "https://www.tiktok.com/",
            "whatsapp": "https://web.whatsapp.com/",
            "whatsapp web": "https://web.whatsapp.com/",
            "gmail": "https://mail.google.com/",
            "gmail web": "https://mail.google.com/",
            "google": "https://www.google.com/",
            "google web": "https://www.google.com/",
            "github": "https://github.com/",
            "github web": "https://github.com/",
        }
        m = re.search(r"(?:abre|abrir|entra(?:r)?\s+a|ve\s+a)\s+(.+)", low)
        if m:
            target = re.sub(r"\b(?:ahora|por favor|jarvis)\b", "", m.group(1)).strip(" .!?/")
            if target in web_aliases:
                return execute_tool("open_url", url=web_aliases[target])

        # GENERACIÓN DE IMÁGENES: ruta determinista para que no dependa de que el modelo
        # local decida correctamente si debe llamar a la herramienta.
        image_patterns = [
            r"(?:crea|crear|genera|generar|haz|hacer|dibuja|dibujar)\s+(?:una\s+)?imagen(?:\s+de|\s+sobre|\s+con)?\s*(.+)",
            r"(?:crea|genera|haz)\s+(?:un\s+)?(?:dibujo|ilustraci[oó]n|render)\s+(?:de|sobre|con)?\s*(.+)",
        ]
        for pattern in image_patterns:
            m = re.search(pattern, low)
            if m:
                prompt = m.group(1).strip(" .!?\"")
                if prompt:
                    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", prompt)[:60].strip("_") or "jarvis_image"
                    return execute_tool("generate_image", prompt=prompt, filename=f"{safe_name}.png", size="1024x1024")

        # Open app / program
        m = re.search(OPEN_WORDS + r"\s+(.+)", low)
        if m:
            target = re.sub(r"\b(ahora|por favor|jarvis)\b", "", m.group(1)).strip()
            if target:
                return execute_tool("open_application", name=target)

        # Música LOCAL: "Jarvis, reproduce Mil vidas" / "pon música".
        # Esta ruta se ejecuta antes de Google y no necesita Internet para reproducir.
        m = re.search(r"(?:escucha|escuchar|pon|poner|reproduce|reproducir)\s+(.+)", low)
        if m:
            query = re.sub(r"\b(?:jarvis)\b", "", m.group(1)).strip()
            if query:
                query = re.sub(r"^m[uú]sica\s*", "", query).strip()
            return execute_tool("listen_music", query=query)

        # Google search
        m = re.search(r"(?:busca|buscar|búscame|buscame)\s+(?:en google\s+)?(.+)", low)
        if m and not re.search(r"imágenes|imagenes|fotos|fotograf", low):
            return execute_tool("google_search", query=m.group(1).strip())

        return None
