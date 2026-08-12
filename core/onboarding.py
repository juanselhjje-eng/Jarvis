from __future__ import annotations

from core.user_profile import load_profile, set_preferred_name


def needs_onboarding() -> bool:
    return not bool(load_profile().get("preferred_name", "").strip())


def welcome_message() -> str:
    return "Bienvenido. Antes de empezar, ¿cómo quieres que te llame?"


def complete_onboarding(name: str) -> str:
    clean = str(name).strip()
    if not clean:
        raise ValueError("El nombre no puede estar vacío")
    return set_preferred_name(clean)
