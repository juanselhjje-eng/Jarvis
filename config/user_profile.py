from __future__ import annotations
import json
from pathlib import Path
from typing import Any

PROFILE_FILE = Path(__file__).resolve().parent / "user_profile.json"

DEFAULT_PROFILE = {
    "personality": {
        "name": "JARVIS",
        "tone": "Profesional, inteligente y directo",
        "style": "Respuestas claras y naturales, sin repetir información innecesaria.",
        "proactivity": 80,
        "creativity": 70,
        "humor": 35,
        "verbosity": 55,
    },
    "voice": {
        "enabled": True,
        "rate": 185,
        "volume": 1.0,
        "voice_id": "",
    },
    "reasoning": {
        "mode": "AUTO",
        "deep": True,
    },
    "learning": {
        "proactive_questions": True,
        "idle_seconds": 120,
        "mode": "ADAPTIVE",
    },
}

def load_profile() -> dict[str, Any]:
    try:
        if PROFILE_FILE.exists():
            data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
            merged = json.loads(json.dumps(DEFAULT_PROFILE))
            _merge(merged, data)
            return merged
    except Exception:
        pass
    return json.loads(json.dumps(DEFAULT_PROFILE))

def _merge(dst, src):
    if not isinstance(src, dict):
        return
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge(dst[k], v)
        else:
            dst[k] = v

def save_profile(profile: dict[str, Any]) -> None:
    PROFILE_FILE.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
