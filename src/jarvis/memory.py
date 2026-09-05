from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MEMORY_FILE = DATA_DIR / "memory.json"


class LocalMemory:
    """Memoria persistente local; no envía datos a ningún servicio."""

    def __init__(self, path: Path = MEMORY_FILE) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._load()
            data[key] = value
            self._save(data)

    def clear(self) -> None:
        with self._lock:
            self._save({})
