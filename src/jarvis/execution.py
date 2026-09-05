from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
AUDIT_FILE = DATA_DIR / "execution_log.jsonl"


class TaskState(str, Enum):
    IDLE = "IDLE"
    INTENT = "INTENT"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskRecord:
    command: str
    state: str
    started_at: float
    finished_at: float | None = None
    result: str = ""
    verified: bool = False


class ExecutionTracker:
    """Seguimiento de tareas, estado visible y auditoría local."""

    def __init__(self, path: Path = AUDIT_FILE) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.current: TaskRecord | None = None

    def start(self, command: str) -> TaskRecord:
        record = TaskRecord(command=command, state=TaskState.INTENT.value, started_at=time.time())
        with self._lock:
            self.current = record
        self._write(record, event="start")
        return record

    def set_state(self, state: TaskState) -> None:
        with self._lock:
            if self.current is None:
                return
            self.current.state = state.value
            record = self.current
        self._write(record, event="state")

    def finish(self, result: str, verified: bool, success: bool = True) -> None:
        with self._lock:
            if self.current is None:
                return
            self.current.result = result
            self.current.verified = verified
            self.current.finished_at = time.time()
            self.current.state = TaskState.COMPLETED.value if success else TaskState.FAILED.value
            record = self.current
        self._write(record, event="finish")

    def cancel(self, result: str = "") -> None:
        with self._lock:
            if self.current is None:
                return
            self.current.result = result
            self.current.finished_at = time.time()
            self.current.state = TaskState.CANCELLED.value
            record = self.current
        self._write(record, event="cancel")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self.current) if self.current else {"command": "", "state": TaskState.IDLE.value, "result": "", "verified": False}

    def _write(self, record: TaskRecord, event: str) -> None:
        payload: dict[str, Any] = {"event": event, **asdict(record), "timestamp": time.time()}
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except OSError:
                pass


class ActionVerifier:
    """Verificaciones sencillas y reales para evitar respuestas de 'fire and forget'."""

    @staticmethod
    def process_running(process_name: str) -> bool:
        try:
            import psutil
            wanted = process_name.lower()
            return any((p.info.get("name") or "").lower() == wanted for p in psutil.process_iter(["name"]))
        except Exception:
            return False

    @staticmethod
    def file_exists(path: str) -> bool:
        try:
            return Path(path).expanduser().exists()
        except OSError:
            return False

    @staticmethod
    def browser_target_opened(target: str) -> bool:
        return bool(target.strip())
