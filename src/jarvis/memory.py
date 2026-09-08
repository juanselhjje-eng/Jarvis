from __future__ import annotations

import json
import re
import time
from pathlib import Path
from threading import Lock
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MEMORY_FILE = DATA_DIR / "memory.json"


class LocalMemory:
    """Memoria persistente local con hechos, preferencias, lecciones y contexto de tareas."""

    def __init__(self, path: Path = MEMORY_FILE) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"facts": [], "preferences": {}, "lessons": [], "tasks": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"facts": [], "preferences": {}, "lessons": [], "tasks": []}
            data.setdefault("facts", [])
            data.setdefault("preferences", {})
            data.setdefault("lessons", [])
            data.setdefault("tasks", [])
            # Compatibilidad con la memoria antigua que guardaba una sola "nota".
            legacy = data.get("nota")
            if legacy and str(legacy) not in data["facts"]:
                data["facts"].append(str(legacy))
            return data
        except (OSError, json.JSONDecodeError):
            return {"facts": [], "preferences": {}, "lessons": [], "tasks": []}

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _safe_text(value: str, limit: int = 500) -> str:
        value = re.sub(r"\s+", " ", str(value)).strip()
        return value[:limit]

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._load()
            if key == "nota":
                text = self._safe_text(value)
                if text and text not in data["facts"]:
                    data["facts"].append(text)
                    data["facts"] = data["facts"][-100:]
                data["nota"] = text
            else:
                data[key] = value
            self._save(data)

    def remember(self, text: str, category: str = "fact") -> None:
        text = self._safe_text(text)
        if not text:
            return
        with self._lock:
            data = self._load()
            if category == "preference":
                key = text.lower()
                data["preferences"][key] = text
            else:
                facts: list[str] = data["facts"]
                if text not in facts:
                    facts.append(text)
                    data["facts"] = facts[-100:]
            self._save(data)

    def learn(self, lesson: str, context: str = "") -> None:
        lesson = self._safe_text(lesson)
        context = self._safe_text(context)
        if not lesson:
            return
        with self._lock:
            data = self._load()
            lessons: list[dict[str, Any]] = data["lessons"]
            record = {"lesson": lesson, "context": context, "time": int(time.time())}
            if not any(item.get("lesson") == lesson and item.get("context") == context for item in lessons):
                lessons.append(record)
            data["lessons"] = lessons[-100:]
            self._save(data)

    def record_task(self, task: str, result: str, success: bool) -> None:
        task = self._safe_text(task)
        result = self._safe_text(result)
        if not task:
            return
        with self._lock:
            data = self._load()
            tasks: list[dict[str, Any]] = data["tasks"]
            tasks.append({"task": task, "result": result, "success": bool(success), "time": int(time.time())})
            data["tasks"] = tasks[-80:]
            self._save(data)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-záéíóúüñ0-9]{3,}", text.lower()) if token not in {"para", "esta", "este", "hacer", "como"}}

    def recall(self, query: str, limit: int = 8) -> str:
        """Recupera memoria relevante con una búsqueda local ligera."""
        q = self._tokens(query)
        with self._lock:
            data = self._load()
        candidates: list[tuple[float, str]] = []
        for fact in data.get("facts", []):
            text = str(fact)
            score = len(q & self._tokens(text)) / max(1, len(q)) if q else 0.0
            candidates.append((score + 0.10, f"Hecho: {text}"))
        for key, value in data.get("preferences", {}).items():
            text = str(value)
            score = len(q & self._tokens(text)) / max(1, len(q)) if q else 0.0
            candidates.append((score + 0.15, f"Preferencia: {text}"))
        for item in data.get("lessons", []):
            text = str(item.get("lesson", ""))
            context = str(item.get("context", ""))
            score = len(q & self._tokens(text + " " + context)) / max(1, len(q)) if q else 0.0
            candidates.append((score, f"Lección: {text}" + (f" ({context})" if context else "")))
        for item in data.get("tasks", [])[-40:]:
            text = str(item.get("task", ""))
            score = len(q & self._tokens(text)) / max(1, len(q)) if q else 0.0
            if score > 0:
                candidates.append((score * 0.8, f"Tarea previa: {text} -> {item.get('result', '')}"))
        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = [text for score, text in candidates if score > 0][:limit]
        return "\n".join(selected)

    def summary(self) -> str:
        with self._lock:
            data = self._load()
        return f"MEMORIA LOCAL: {len(data.get('facts', []))} hechos, {len(data.get('preferences', {}))} preferencias, {len(data.get('lessons', []))} lecciones, {len(data.get('tasks', []))} tareas registradas."

    def clear(self) -> None:
        with self._lock:
            self._save({"facts": [], "preferences": {}, "lessons": [], "tasks": []})
