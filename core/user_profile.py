from __future__ import annotations

"""Local user profile and durable memory.

The profile lives outside the Git repository by default. This makes JARVIS
commercializable: every installation gets its own identity and memory instead
of accidentally sharing users' conversations through GitHub.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone


APP_DIR = Path(os.getenv("JARVIS_DATA_DIR", Path.home() / ".jarvis"))
PROFILE_FILE = APP_DIR / "profile.json"
MEMORY_FILE = APP_DIR / "memory.jsonl"


def _ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_profile() -> dict:
    _ensure_dir()
    if not PROFILE_FILE.exists():
        return {"preferred_name": "", "created_at": datetime.now(timezone.utc).isoformat()}
    try:
        return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"preferred_name": ""}


def save_profile(profile: dict) -> None:
    _ensure_dir()
    PROFILE_FILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def set_preferred_name(name: str) -> str:
    profile = load_profile()
    profile["preferred_name"] = str(name).strip()
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_profile(profile)
    return profile["preferred_name"]


def remember(kind: str, content: str, metadata: dict | None = None) -> None:
    if not str(content).strip():
        return
    _ensure_dir()
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "kind": str(kind),
        "content": str(content),
        "metadata": metadata or {},
    }
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def recent_memory(limit: int = 100) -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()[-max(1, int(limit)):]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return result
