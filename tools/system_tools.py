from __future__ import annotations

from pathlib import Path
import difflib
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from typing import Optional

from config.settings import (
    APP_ALIASES, MUSIC_DIR, USER_MUSIC_DIR, MUSIC_EXTENSIONS,
    WORKSPACE_DIR, TEXT_EXTENSIONS,
)


def _expand(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(str(value).strip()))


def _windows_only() -> None:
    if os.name != "nt":
        raise RuntimeError("Esta herramienta requiere Windows.")


def _start_menu_roots() -> list[Path]:
    roots = []
    for key, default in (
        ("PROGRAMDATA", r"C:\ProgramData"),
        ("APPDATA", str(Path.home() / "AppData/Roaming")),
    ):
        value = os.environ.get(key, default)
        roots.append(Path(value) / "Microsoft/Windows/Start Menu/Programs")
    return roots


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _find_start_menu_shortcut(query: str) -> Optional[Path]:
    q = _normalize_name(query)
    if not q:
        return None
    best: tuple[float, Optional[Path]] = (0.0, None)
    for root in _start_menu_roots():
        if not root.exists():
            continue
        try:
            for item in root.rglob("*"):
                if item.suffix.lower() not in {".lnk", ".url"}:
                    continue
                stem = _normalize_name(item.stem)
                score = 1.0 if q == stem else 0.93 if q in stem or stem in q else difflib.SequenceMatcher(None, q, stem).ratio()
                if score > best[0]:
                    best = (score, item)
        except (OSError, PermissionError):
            pass
    return best[1] if best[0] >= 0.60 else None


def _find_executable(query: str) -> Optional[str]:
    q = str(query).strip().strip('"')
    candidates = APP_ALIASES.get(q.lower(), [q])
    for candidate in candidates:
        # Explicit path.
        if os.path.isabs(candidate) and Path(candidate).exists():
            return candidate
        # PATH lookup.
        found = shutil.which(candidate)
        if found:
            return found

    # Common Windows install locations. Avoid an expensive whole-disk scan.
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("ProgramW6432"),
    ]
    names = [Path(x).name for x in candidates]
    for root in filter(None, roots):
        base = Path(root)
        if not base.exists():
            continue
        for name in names:
            direct = base / name
            if direct.is_file():
                return str(direct)
        # Search only a few levels, which catches many installed apps.
        try:
            for pattern in names:
                for match in base.glob(f"*/{pattern}"):
                    if match.is_file():
                        return str(match)
                for match in base.glob(f"*/*/{pattern}"):
                    if match.is_file():
                        return str(match)
        except (OSError, PermissionError):
            pass
    return None


def _launch_and_verify(target: str, label: str) -> str:
    _windows_only()
    try:
        proc = subprocess.Popen(target, shell=True)
        # Popen returning a PID means Windows accepted the launch command. For shell launches,
        # a short-lived cmd can still fail, so only use this path for explicit executable targets.
        if proc.pid:
            return f"He abierto {label}."
    except Exception as exc:
        return f"No pude abrir {label}: {exc}"
    return f"No pude abrir {label}."


def open_application(name: str) -> str:
    """Open a Windows application, or a well-known website requested as an app-like target."""
    _windows_only()
    raw = str(name).strip().strip('"')
    query = _normalize_name(raw)
    # Natural-language web aliases: "abre instagram web", "abre youtube", etc.
    # These are deterministic and do not require an AI round-trip.
    web_aliases = {
        "instagram": "https://www.instagram.com/",
        "instagram web": "https://www.instagram.com/",
        "youtube": "https://www.youtube.com/",
        "youtube web": "https://www.youtube.com/",
        "facebook": "https://www.facebook.com/",
        "facebook web": "https://www.facebook.com/",
        "tiktok": "https://www.tiktok.com/",
        "tiktok web": "https://www.tiktok.com/",
        "whatsapp web": "https://web.whatsapp.com/",
        "whatsapp": "https://web.whatsapp.com/",
        "gmail": "https://mail.google.com/",
        "gmail web": "https://mail.google.com/",
        "google": "https://www.google.com/",
        "google web": "https://www.google.com/",
        "google drive": "https://drive.google.com/",
        "google docs": "https://docs.google.com/",
        "discord web": "https://discord.com/app",
        "spotify web": "https://open.spotify.com/",
        "github": "https://github.com/",
        "github web": "https://github.com/",
    }
    web_target = web_aliases.get(query)
    if web_target:
        webbrowser.open(web_target, new=2)
        return f"He abierto {raw} en el navegador."
    # If the user supplied a domain/URL, open it directly.
    if re.match(r"^(?:https?://|www\.)", raw, re.I) or re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(?:/.*)?$", raw, re.I):
        url = raw if re.match(r"^https?://", raw, re.I) else "https://" + raw
        webbrowser.open(url, new=2)
        return f"He abierto {url} en el navegador."
    if not query:
        return "Necesito el nombre de la aplicación."

    # Known aliases first.
    executable = _find_executable(raw)
    if executable:
        try:
            subprocess.Popen([executable], close_fds=True)
            return f"He abierto {raw}."
        except (OSError, PermissionError) as exc:
            return f"Encontré {raw}, pero Windows no permitió iniciarla: {exc}"

    # Start Menu shortcut is the most reliable generic route for GUI apps.
    shortcut = _find_start_menu_shortcut(raw)
    if shortcut:
        try:
            os.startfile(str(shortcut))
            return f"He abierto {raw}."
        except OSError as exc:
            return f"Encontré el acceso de {raw}, pero no pude iniciarlo: {exc}"

    # Last resort: ask Windows shell to resolve the application name.
    try:
        completed = subprocess.run(
            ["cmd", "/c", "start", "", raw],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode == 0:
            return f"He enviado a Windows la orden de abrir {raw}."
    except Exception:
        pass
    return f"No encontré una aplicación instalada llamada '{raw}'."


def open_url(url: str) -> str:
    value = str(url).strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        value = "https://" + value
    webbrowser.open(value)
    return f"He abierto {value}."


def open_folder(path: str) -> str:
    _windows_only()
    target = _expand(path)
    if not os.path.isdir(target):
        return f"La carpeta no existe: {target}"
    os.startfile(target)
    return f"He abierto {target}."


def open_file(path: str) -> str:
    _windows_only()
    target = _expand(path)
    if not os.path.isfile(target):
        return f"El archivo no existe: {target}"
    os.startfile(target)
    return f"He abierto {target}."



def open_workspace() -> str:
    """Opens JARVIS's project workspace in Windows Explorer."""
    _windows_only()
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    os.startfile(str(WORKSPACE_DIR))
    return f"Workspace abierto: {WORKSPACE_DIR}"

def create_folder(path: str) -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    target.mkdir(parents=True, exist_ok=True)
    return f"Carpeta creada: {target}"


def create_file(path: str, content: str = "") -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(content), encoding="utf-8")
    return f"Archivo creado: {target}"


def append_file(path: str, content: str) -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(str(content))
    return f"Contenido añadido a: {target}"


def list_folder(path: str = ".") -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    if not target.exists():
        return f"No existe: {target}"
    items = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = [f"[DIR] {p.name}" if p.is_dir() else f"[FILE] {p.name}" for p in items[:300]]
    return "\n".join(lines) if lines else "(vacío)"


def read_file(path: str) -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    if not target.is_file():
        return f"El archivo no existe: {target}"
    try:
        return target.read_text(encoding="utf-8")[:30000]
    except UnicodeDecodeError:
        return "El archivo no es texto UTF-8."


def delete_file(path: str, confirm: bool = False) -> str:
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    if not target.is_file():
        return f"El archivo no existe: {target}"
    if not confirm:
        return f"CONFIRMACIÓN NECESARIA para eliminar: {target}"
    target.unlink()
    return f"Archivo eliminado: {target}"


def get_system_info() -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.05)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        return f"CPU {cpu:.0f}% | RAM {ram.percent:.0f}% ({ram.used/2**30:.1f}/{ram.total/2**30:.1f} GB) | DISCO {disk.percent:.0f}%"
    except Exception as exc:
        return f"No pude leer toda la telemetría: {exc}"


def scan_local_music() -> list[str]:
    roots = [Path(MUSIC_DIR), Path(USER_MUSIC_DIR)]
    found, seen = [], set()
    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in MUSIC_EXTENSIONS:
                    key = str(p.resolve()).lower()
                    if key not in seen:
                        seen.add(key)
                        found.append(str(p))
        except (PermissionError, OSError):
            continue
    return found


def _clean_title(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[_\-.()\[\]{}]", " ", text)
    return " ".join(text.split())


def find_local_song(query: str) -> Optional[Path]:
    q = _clean_title(query)
    songs = [Path(x) for x in scan_local_music()]
    if not songs:
        return None
    for song in songs:
        title = _clean_title(song.stem)
        if q == title or q in title or title in q:
            return song
    best, score_best = None, 0.0
    for song in songs:
        score = difflib.SequenceMatcher(None, q, _clean_title(song.stem)).ratio()
        if score > score_best:
            score_best, best = score, song
    return best if score_best >= 0.48 else None


def play_local_music(query: str) -> str:
    _windows_only()
    song = find_local_song(query)
    if song is None:
        return f"No encontré '{query}' en la música local."
    try:
        os.startfile(str(song))
        return f"Reproduciendo localmente: {song.stem}"
    except OSError as exc:
        return f"Encontré {song.name}, pero no pude reproducirlo: {exc}"


def open_google_search(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(str(query))
    webbrowser.open(url)
    return f"He abierto Google para: {query}"


def open_google_images(query: str) -> str:
    url = "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(str(query))
    webbrowser.open(url)
    return f"He abierto imágenes de Google para: {query}"


def type_text(text: str, interval: float = 0.01) -> str:
    """Types into the currently focused Windows application."""
    try:
        import pyautogui
    except ImportError:
        return "PyAutoGUI no está instalado en este entorno."
    pyautogui.write(str(text), interval=max(0.0, float(interval)))
    return "Texto escrito."


def press_keys(keys: str) -> str:
    try:
        import pyautogui
    except ImportError:
        return "PyAutoGUI no está instalado en este entorno."
    parts = [x.strip().lower() for x in str(keys).split("+") if x.strip()]
    if not parts:
        return "No recibí teclas."
    pyautogui.hotkey(*parts) if len(parts) > 1 else pyautogui.press(parts[0])
    return f"Teclas ejecutadas: {keys}"


def move_mouse(x: int, y: int, duration: float = 0.15) -> str:
    try:
        import pyautogui
    except ImportError:
        return "PyAutoGUI no está instalado en este entorno."
    pyautogui.moveTo(int(x), int(y), duration=max(0.0, float(duration)))
    return f"Cursor movido a ({int(x)}, {int(y)})."


def click_mouse(button: str = "left", clicks: int = 1) -> str:
    try:
        import pyautogui
    except ImportError:
        return "PyAutoGUI no está instalado en este entorno."
    pyautogui.click(button=button, clicks=max(1, int(clicks)), interval=0.08)
    return f"Clic ejecutado: {button} x{clicks}."




def run_program(executable: str, arguments: str = "", working_dir: str = "", timeout: int = 30) -> str:
    """Run a Windows program without a shell. Destructive delete commands are blocked."""
    _windows_only()
    exe = str(executable).strip().strip('"')
    args = str(arguments or "").strip()
    if not exe:
        return "Necesito el programa que quieres ejecutar."
    dangerous = re.compile(r"(?:^|[\s;&|])(del|erase|rd|rmdir|remove-item|rm)(?:[\s;&|]|$)|(?:format|diskpart|cipher\\s+/w)", re.I)
    combined = f"{exe} {args}"
    if dangerous.search(combined):
        return "Por seguridad, JARVIS no ejecuta comandos de eliminación o borrado."
    target = _expand(exe)
    if not (Path(target).exists() or shutil.which(target)):
        found = _find_executable(target)
        if found:
            target = found
    try:
        argv = [target]
        if args:
            import shlex
            argv.extend(shlex.split(args, posix=False))
        proc = subprocess.Popen(argv, cwd=_expand(working_dir) if working_dir else None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            out, err = proc.communicate(timeout=max(1, int(timeout)))
        except subprocess.TimeoutExpired:
            proc.kill()
            return f"El programa {exe} sigue ejecutándose; superó el tiempo de espera de {timeout}s."
        output = (out or err or "").strip()
        if len(output) > 6000:
            output = output[:6000] + "\n...[salida recortada]"
        return f"Programa ejecutado: {exe} (código {proc.returncode}).\n{output}".strip()
    except Exception as exc:
        return f"No pude ejecutar {exe}: {exc}"


def edit_text_file(path: str, instruction: str, content: str = "") -> str:
    """Edit or replace a text file. Original is backed up once as .bak."""
    target = Path(_expand(path))
    if not target.is_absolute():
        target = WORKSPACE_DIR / target
    if not target.is_file():
        return f"El archivo no existe: {target}"
    if target.suffix.lower() not in TEXT_EXTENSIONS and target.suffix.lower() not in {".py", ".json", ".yaml", ".yml", ".md", ".html", ".css", ".js", ".ts", ".txt", ".csv", ".xml"}:
        return "Ese archivo no parece ser un archivo de texto editable con esta herramienta."
    try:
        original = target.read_text(encoding="utf-8")
        backup = target.with_suffix(target.suffix + ".bak")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
        if content:
            new_text = str(content)
        else:
            return "Necesito el contenido nuevo para editar el archivo."
        target.write_text(new_text, encoding="utf-8")
        return f"Archivo actualizado: {target}. Respaldo: {backup}"
    except Exception as exc:
        return f"No pude editar {target}: {exc}"


def generate_image(prompt: str, filename: str = "jarvis_image.png", size: str = "1024x1024") -> str:
    """Generate an image with OpenAI Images API and save it locally."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "No hay OPENAI_API_KEY configurada para generar imágenes."
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
        # gpt-image-1 devuelve normalmente b64_json. La API puede cambiar el tamaño
        # disponible, así que permitimos configurarlo desde .env.
        result = client.images.generate(model=model, prompt=str(prompt), size=size)
        item = result.data[0]
        out_dir = WORKSPACE_DIR / "generated" / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / Path(filename).name
        import base64
        if getattr(item, "b64_json", None):
            target.write_bytes(base64.b64decode(item.b64_json))
        elif getattr(item, "url", None):
            import urllib.request
            urllib.request.urlretrieve(item.url, target)
        else:
            return "El proveedor no devolvió una imagen utilizable."
        return f"Imagen generada y guardada en: {target}"
    except Exception as exc:
        return f"No pude generar la imagen con OpenAI ({os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1')}): {exc}. Comprueba OPENAI_API_KEY, OPENAI_IMAGE_MODEL y que tu cuenta tenga acceso/facturación habilitada para imágenes."

def inspect_code(path: str) -> str:
    """Checks a Python file for syntax errors without modifying it."""
    from core.self_repair import _safe_path, _python_compile
    target = _safe_path(path)
    if not target.is_file():
        return f"El archivo no existe: {target}"
    if target.suffix.lower() != ".py":
        return "La inspección automática está disponible para archivos Python."
    ok, detail = _python_compile(target)
    return f"CODE CHECK {'OK' if ok else 'ERROR'}: {detail}"


def self_repair_code(path: str, error: str) -> str:
    """Backs up, repairs and validates a code file using the local AI."""
    from core.self_repair import SelfRepairEngine
    return SelfRepairEngine().repair(path, error)


def audit_jarvis_code(repair: bool = True) -> str:
    """Audits the JARVIS Python project and optionally self-repairs syntax failures."""
    from core.self_repair import SelfRepairEngine
    return SelfRepairEngine().audit_project(repair=bool(repair))
