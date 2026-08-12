from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR, WORKSPACE_DIR
from memory.learning import get_learning_engine

REPAIR_DIR = BASE_DIR / "memory" / "repair_backups"
REPAIR_DIR.mkdir(parents=True, exist_ok=True)

SAFE_CODE_ROOTS = (BASE_DIR, WORKSPACE_DIR)
CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json"}


def _safe_path(value: str) -> Path:
    p = Path(str(value).strip().strip('"')).expanduser()
    if not p.is_absolute():
        p = BASE_DIR / p
    p = p.resolve()
    if not any(p == root.resolve() or root.resolve() in p.parents for root in SAFE_CODE_ROOTS):
        raise ValueError("La reparación solo puede actuar dentro del proyecto JARVIS o su workspace.")
    if p.suffix.lower() not in CODE_EXTENSIONS:
        raise ValueError("Ese archivo no es un archivo de código/configuración permitido.")
    return p


def _extract_code(text: str) -> str:
    text = str(text).strip()
    fenced = re.findall(r"```(?:python|py|javascript|typescript|json|html|css)?\s*\n?(.*?)```", text, flags=re.I | re.S)
    if fenced:
        return max(fenced, key=len).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and isinstance(obj.get("content"), str):
                return obj["content"].strip()
        except Exception:
            pass
    return text


def _python_compile(path: Path) -> tuple[bool, str]:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        return True, "Python syntax OK"
    except SyntaxError as exc:
        return False, f"SyntaxError line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, str(exc)


def _make_backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target_dir = REPAIR_DIR / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    shutil.copy2(path, target)
    return target


class SelfRepairEngine:
    """Conservative self-repair loop: backup -> ask local model -> validate -> test -> rollback."""

    def __init__(self, provider=None):
        self.provider = provider
        self.learning = get_learning_engine()
        self.last_event = "READY"

    def _provider(self):
        if self.provider is None:
            from providers.ollama_provider import OllamaProvider
            self.provider = OllamaProvider()
        return self.provider

    def _generate_patch(self, path: Path, error: str) -> str:
        source = path.read_text(encoding="utf-8")
        prompt = f"""Corrige este archivo de código.

ARCHIVO: {path}
ERROR:
{error}

REGLAS:
- Devuelve SOLO el contenido completo corregido del archivo.
- Conserva la funcionalidad existente.
- No inventes dependencias innecesarias.
- No uses comandos shell.
- No elimines funcionalidades que no estén relacionadas con el error.
- Si el error no puede corregirse con seguridad, devuelve exactamente: NO_SAFE_FIX

CONTENIDO ACTUAL:
{source}
"""
        response = self._provider().chat(
            [
                {"role": "system", "content": "Eres el motor de reparación de software de JARVIS. Corriges código y solo devuelves el archivo solicitado."},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            think=True,
        )
        content = getattr(getattr(response, "message", None), "content", "") or ""
        return _extract_code(content)

    def audit_project(self, repair: bool = True, max_repairs: int = 2) -> str:
        """Audits Python files; optionally repairs only verified syntax failures."""
        failures = []
        repair_attempts = 0
        for path in sorted(BASE_DIR.rglob("*.py")):
            if any(part in {".venv", "__pycache__", "repair_backups"} for part in path.parts):
                continue
            ok, detail = _python_compile(path)
            if ok:
                continue
            if repair and repair_attempts < max_repairs:
                repair_attempts += 1
                result = self.repair(str(path), detail, test=True)
                ok_after, detail_after = _python_compile(path)
                if ok_after:
                    continue
                failures.append((path, detail_after or result))
            else:
                failures.append((path, detail))
        if not failures:
            self.last_event = "AUDIT CLEAN"
            return "SELF-AUDIT: proyecto Python sin errores de sintaxis."
        self.last_event = f"AUDIT {len(failures)} ERRORS"
        return "SELF-AUDIT: " + " | ".join(f"{p.name}: {d}" for p,d in failures)

    def repair(self, path: str, error: str, test: bool = True) -> str:
        try:
            target = _safe_path(path)
            if not target.is_file():
                return f"SELF-REPAIR: archivo inexistente: {target}"
            if target == Path(__file__).resolve():
                return "SELF-REPAIR: no reparo el propio motor de reparación durante una ejecución activa."
            backup = _make_backup(target)
            self.last_event = f"BACKUP {backup.name}"
            candidate = self._generate_patch(target, error)
            if not candidate or candidate.strip() == "NO_SAFE_FIX":
                self.last_event = "NO SAFE FIX"
                return "SELF-REPAIR: no encontré una corrección segura; el archivo original permanece intacto."
            target.write_text(candidate, encoding="utf-8")
            if target.suffix.lower() == ".py":
                ok, detail = _python_compile(target)
                if not ok:
                    shutil.copy2(backup, target)
                    self.last_event = "ROLLBACK SYNTAX"
                    self.learning.record(path, "repair_rollback", detail, success=False, error=True)
                    return f"SELF-REPAIR: la corrección falló la validación ({detail}). Hice rollback automático."
                if test:
                    proc = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(target)],
                        capture_output=True, text=True, timeout=20,
                    )
                    if proc.returncode != 0:
                        shutil.copy2(backup, target)
                        self.last_event = "ROLLBACK TEST"
                        detail = (proc.stderr or proc.stdout or "test failed")[-1200:]
                        self.learning.record(path, "repair_rollback", detail, success=False, error=True)
                        return f"SELF-REPAIR: prueba fallida; rollback automático. {detail}"
            self.last_event = "REPAIRED + VERIFIED"
            detail = f"Reparado {target.name}; backup={backup}"
            self.learning.record(path, "repair_success", detail, success=True, error=False)
            return f"SELF-REPAIR: corregí {target.name}, validé el archivo y conservé un respaldo."
        except Exception as exc:
            self.last_event = "REPAIR ERROR"
            return f"SELF-REPAIR: no pude completar la reparación: {exc}"
