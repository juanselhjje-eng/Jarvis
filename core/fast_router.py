from __future__ import annotations

import os
import re
import subprocess
import webbrowser
from datetime import datetime
from urllib.parse import quote_plus

from tools.registry import execute_tool

WEB_ALIASES = {
    "instagram": "https://www.instagram.com/",
    "instagram web": "https://www.instagram.com/",
    "la web de instagram": "https://www.instagram.com/",
    "youtube": "https://www.youtube.com/",
    "youtube web": "https://www.youtube.com/",
    "tiktok": "https://www.tiktok.com/",
    "tiktok web": "https://www.tiktok.com/",
    "facebook": "https://www.facebook.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "whatsapp web": "https://web.whatsapp.com/",
    "gmail": "https://mail.google.com/",
    "google": "https://www.google.com/",
    "google drive": "https://drive.google.com/",
    "google docs": "https://docs.google.com/",
    "discord web": "https://discord.com/app",
    "spotify web": "https://open.spotify.com/",
    "github": "https://github.com/",
}


def _open_url_robust(url: str) -> bool:
    try:
        if os.name == "nt":
            subprocess.Popen(["cmd", "/c", "start", "", url], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
    except Exception:
        pass
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False


def _clean(text: str) -> str:
    value = re.sub(r"^\s*(?:jarvis[,:]?\s*)+", "", str(text), flags=re.I)
    return re.sub(r"\s+", " ", value).strip(" .!?\t\r\n").lower()


def fast_route(text: str):
    """Handle high-frequency requests without an LLM round-trip."""
    clean = _clean(text)
    if not clean:
        return None

    if re.fullmatch(r"(?:hola|hola jarvis|hey|hey jarvis|buenas|buenos dias|buenas tardes|buenas noches)", clean):
        hour = datetime.now().hour
        salutation = "Buenos días" if 5 <= hour < 12 else "Buenas tardes" if 12 <= hour < 19 else "Buenas noches"
        return f"{salutation}. JARVIS en línea. Sistemas principales disponibles; dime qué quieres hacer y me encargo."

    for verb in ("abre", "abrir", "ve a", "ir a", "entra a", "entrar a"):
        if clean.startswith(verb + " "):
            target = clean[len(verb):].strip()
            target = re.sub(r"^(?:la web de|la pagina de|la página de)\s+", "", target)
            url = WEB_ALIASES.get(target)
            if url:
                ok = _open_url_robust(url)
                return f"He abierto {target} en el navegador." if ok else f"No pude abrir {target} en el navegador."

    if re.match(r"^(?:https?://|www\.)", clean, re.I):
        url = clean if re.match(r"^https?://", clean, re.I) else "https://" + clean
        ok = _open_url_robust(url)
        return f"He abierto {url}." if ok else f"No pude abrir {url}."

    m = re.match(r"^(?:busca|buscar|googlea|googlear)\s+(?:en google\s+)?(.+)$", clean, re.I)
    if m and not clean.startswith(("busca en google imágenes", "busca en google imagenes")):
        query = m.group(1).strip()
        ok = _open_url_robust("https://www.google.com/search?q=" + quote_plus(query))
        return f"Buscando {query} en Google." if ok else "No pude abrir la búsqueda de Google."

    m = re.match(r"^(?:abre|abrir|inicia|iniciar)\s+(.+)$", clean, re.I)
    if m:
        target = m.group(1).strip()
        if target not in WEB_ALIASES:
            try:
                return execute_tool("open_application", name=target)
            except Exception:
                return None
    return None
