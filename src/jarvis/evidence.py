from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EVIDENCE_FILE = DATA_DIR / "evidence.json"


@dataclass
class EvidenceItem:
    title: str
    query: str = ""
    status: str = "ACTIVE"
    findings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    conclusion: str = ""
    created_at: float = field(default_factory=time.time)


class EvidenceBoard:
    """Tablero local de evidencias para investigaciones y tareas de JARVIS."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.items: list[EvidenceItem] = []
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
            self.items = [EvidenceItem(**item) for item in raw[-30:]]
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            self.items = []

    def _save(self) -> None:
        EVIDENCE_FILE.write_text(
            json.dumps([asdict(item) for item in self.items[-30:]], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def start(self, title: str, query: str = "") -> EvidenceItem:
        item = EvidenceItem(title=title, query=query)
        self.items.append(item)
        self._save()
        return item

    def update(self, item: EvidenceItem, *, status: str | None = None, findings: list[str] | None = None, sources: list[str] | None = None, conclusion: str | None = None) -> EvidenceItem:
        if status is not None:
            item.status = status
        if findings is not None:
            item.findings = findings
        if sources is not None:
            item.sources = sources
        if conclusion is not None:
            item.conclusion = conclusion
        self._save()
        return item

    def latest(self) -> EvidenceItem | None:
        return self.items[-1] if self.items else None

    def snapshot(self) -> dict[str, Any]:
        item = self.latest()
        if item is None:
            return {"status": "IDLE", "title": "Sin investigación activa", "findings": [], "sources": []}
        return asdict(item)

    def clear(self) -> None:
        self.items.clear()
        self._save()
