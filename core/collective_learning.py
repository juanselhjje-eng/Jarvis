from __future__ import annotations

"""Privacy-first collective learning for JARVIS.

This does NOT retrain provider models on every message. Instead it extracts
small, reusable lessons from successful/failed tool executions and stores them
locally. A future optional server can aggregate only approved, sanitized
lessons. Raw conversations and API keys are never uploaded by this module.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path.home() / ".jarvis"
LESSONS = ROOT / "collective_lessons.jsonl"


@dataclass
class Lesson:
    kind: str
    situation: str
    solution: str
    source: str = "local"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class CollectiveLearning:
    """Turns verified experiences into compact reusable lessons."""

    def __init__(self) -> None:
        ROOT.mkdir(parents=True, exist_ok=True)
        self.lessons = LESSONS

    @staticmethod
    def sanitize(text: str) -> str:
        text = re.sub(r"sk-[A-Za-z0-9_-]+", "[API_KEY]", str(text))
        text = re.sub(r"(?:password|passwd|token|secret)\s*[=:]\s*\S+", "[SECRET]", text, flags=re.I)
        return text[:2000]

    def learn(self, kind: str, situation: str, solution: str, source: str = "local") -> str:
        lesson = Lesson(kind, self.sanitize(situation), self.sanitize(solution), source)
        payload = json.dumps(asdict(lesson), ensure_ascii=False)
        with self.lessons.open("a", encoding="utf-8") as f:
            f.write(payload + "\n")
        return hashlib.sha256(payload.encode()).hexdigest()[:12]

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.lessons.exists():
            return []
        lines = self.lessons.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(x) for x in lines if x.strip()]

    def context(self, limit: int = 8) -> str:
        return "\n".join(
            f"- {x['situation']} -> {x['solution']}"
            for x in self.recent(limit)
        )


collective_learning = CollectiveLearning()
