from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class IndexedItem:
    name: str
    path: str
    kind: str


class LocalIndexer:
    """Índice local ligero para encontrar archivos y aplicaciones sin enviar datos a la nube."""

    DEFAULT_ROOTS = (Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads")
    FILE_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".jpg", ".jpeg", ".png", ".mp4", ".py"}

    def __init__(self, roots: Iterable[Path] | None = None) -> None:
        self.roots = tuple(roots or self.DEFAULT_ROOTS)
        self.items: list[IndexedItem] = []

    def rebuild(self, limit: int = 5000) -> int:
        items: list[IndexedItem] = []
        for root in self.roots:
            if not root.exists():
                continue
            try:
                for path in root.rglob("*"):
                    if len(items) >= limit:
                        break
                    if not path.is_file() or path.suffix.lower() not in self.FILE_EXTENSIONS:
                        continue
                    try:
                        items.append(IndexedItem(path.name, str(path), "file"))
                    except OSError:
                        continue
            except (OSError, PermissionError):
                continue
        self.items = items
        return len(items)

    def search(self, query: str, limit: int = 10) -> list[IndexedItem]:
        terms = [part.lower() for part in query.split() if part.strip()]
        if not terms:
            return []
        scored: list[tuple[int, IndexedItem]] = []
        for item in self.items:
            haystack = f"{item.name} {item.path}".lower()
            score = sum(2 if term in item.name.lower() else 1 for term in terms if term in haystack)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].name.lower()))
        return [item for _, item in scored[:limit]]

    @staticmethod
    def common_locations() -> list[str]:
        return [str(path) for path in LocalIndexer.DEFAULT_ROOTS if path.exists()]
