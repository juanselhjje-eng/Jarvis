from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
MUSIC_DIR = BASE_DIR / "music"
WORKSPACE_DIR = BASE_DIR / "workspace"
USER_MUSIC_DIR = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Music"

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3.5:4b"
OLLAMA_CONTEXT = 4096
OLLAMA_TEMPERATURE = 0.2
OLLAMA_TIMEOUT = 45.0

MUSIC_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".py", ".html", ".css", ".js", ".xml", ".yaml", ".yml"}

MUSIC_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

APP_ALIASES = {
    "notepad": ["notepad.exe"],
    "bloc de notas": ["notepad.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "explorer": ["explorer.exe"],
    "explorador": ["explorer.exe"],
    "calculadora": ["calc.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "terminal": ["wt.exe"],
    "discord": ["Discord.exe"],
    "spotify": ["Spotify.exe"],
    "unity": ["Unity Hub.exe", "UnityHub.exe", "Unity Hub"],
    "unity hub": ["Unity Hub.exe", "UnityHub.exe", "Unity Hub"],
    "visual studio code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
}

VOICE_RATE = 180
VOICE_ENABLED_DEFAULT = True
