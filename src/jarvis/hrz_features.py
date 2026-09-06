from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


@dataclass
class TaskItem:
    title: str
    due: str = ""
    priority: str = "normal"
    done: bool = False


@dataclass
class ReminderItem:
    title: str
    when: str
    fired: bool = False


class FeatureHub:
    """Funciones locales de productividad para la interfaz HRZ.

    Las integraciones externas se mantienen separadas: no se envían correos,
    mensajes ni eventos sin una acción explícita de confirmación.
    """

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.path = Path(data_dir) / "hrz_productivity.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: list[TaskItem] = []
        self.reminders: list[ReminderItem] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.tasks = [TaskItem(**item) for item in raw.get("tasks", [])]
            self.reminders = [ReminderItem(**item) for item in raw.get("reminders", [])]
        except (OSError, ValueError, TypeError):
            self.tasks, self.reminders = [], []

    def _save(self) -> None:
        payload = {
            "tasks": [asdict(item) for item in self.tasks],
            "reminders": [asdict(item) for item in self.reminders],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_task(self, title: str, due: str = "", priority: str = "normal") -> TaskItem:
        with self._lock:
            item = TaskItem(title.strip(), due.strip(), priority.strip().lower() or "normal")
            self.tasks.append(item)
            self._save()
            return item

    def complete_task(self, index: int) -> bool:
        with self._lock:
            if 0 <= index < len(self.tasks):
                self.tasks[index].done = True
                self._save()
                return True
            return False

    def add_reminder(self, title: str, when: str) -> ReminderItem:
        with self._lock:
            item = ReminderItem(title.strip(), when.strip())
            self.reminders.append(item)
            self._save()
            return item

    def due_reminders(self, now: datetime | None = None) -> list[ReminderItem]:
        now = now or datetime.now()
        due: list[ReminderItem] = []
        for item in self.reminders:
            if item.fired:
                continue
            try:
                target = datetime.fromisoformat(item.when)
            except ValueError:
                continue
            if target <= now:
                item.fired = True
                due.append(item)
        if due:
            with self._lock:
                self._save()
        return due

    def counts(self) -> tuple[int, int, int]:
        total = len(self.tasks)
        done = sum(1 for item in self.tasks if item.done)
        pending_reminders = sum(1 for item in self.reminders if not item.fired)
        return total, done, pending_reminders

    def dashboard(self) -> str:
        total, done, reminders = self.counts()
        return f"Tareas {done}/{total}  •  Recordatorios {reminders}  •  Datos locales"

    def integration_status(self) -> dict[str, str]:
        return {
            "Gmail": "PREPARADO / requiere OAuth",
            "Google Calendar": "PREPARADO / requiere OAuth",
            "Telegram": "PREPARADO / requiere bot token",
            "GitHub": "PREPARADO / requiere autorización",
            "Noticias": "LISTO / fuente web configurable",
            "Clima": "LISTO / ubicación configurable",
        }

    def reminder_loop(self, notify: Callable[[ReminderItem], None], stop_event: threading.Event) -> None:
        while not stop_event.wait(2.0):
            for reminder in self.due_reminders():
                notify(reminder)
