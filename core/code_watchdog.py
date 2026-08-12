from __future__ import annotations

"""Continuous code-health loop.

This module watches the project for changes and coordinates available AI
providers to review them. It creates repair proposals/reports; it never
silently deletes files or applies destructive changes.
"""

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import os
import time
from typing import Callable


@dataclass
class Review:
    path: str
    fingerprint: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    providers: list[str] = field(default_factory=list)


class CodeWatchdog:
    def __init__(self, root: str | Path, reviewer: Callable[[str, str], Review] | None = None):
        self.root = Path(root).resolve()
        self.reviewer = reviewer
        self.cache: dict[str, str] = {}
        self.reports: list[Review] = []
        self.running = False

    def _files(self):
        ignored = {'.git', '.venv', '__pycache__', 'node_modules', '.mypy_cache', '.pytest_cache'}
        for p in self.root.rglob('*'):
            if p.is_file() and not any(part in ignored for part in p.parts):
                if p.suffix.lower() in {'.py', '.json', '.toml', '.yaml', '.yml', '.md'}:
                    yield p

    @staticmethod
    def fingerprint(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    def scan(self) -> list[Path]:
        changed = []
        for p in self._files():
            fp = self.fingerprint(p)
            key = str(p.relative_to(self.root))
            if self.cache.get(key) != fp:
                self.cache[key] = fp
                changed.append(p)
        return changed

    def review_file(self, path: Path) -> Review:
        rel = str(path.relative_to(self.root))
        text = path.read_text(encoding='utf-8', errors='replace')
        fp = self.fingerprint(path)
        if self.reviewer:
            result = self.reviewer(rel, text)
            result.fingerprint = fp
            return result
        return Review(rel, fp, providers=['local-watchdog'])

    def run_once(self) -> list[Review]:
        results = []
        for path in self.scan():
            review = self.review_file(path)
            self.reports.append(review)
            results.append(review)
        return results

    def save_report(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.root / '.jarvis' / 'code_reviews.jsonl'
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('a', encoding='utf-8') as f:
            for report in self.reports:
                f.write(json.dumps(report.__dict__, ensure_ascii=False) + '\n')
        self.reports.clear()
        return target

    def watch(self, interval: float = 5.0, on_review: Callable[[Review], None] | None = None):
        self.running = True
        while self.running:
            for review in self.run_once():
                if on_review:
                    on_review(review)
            time.sleep(max(1.0, interval))

    def stop(self):
        self.running = False
