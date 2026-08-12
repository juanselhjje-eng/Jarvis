from __future__ import annotations

"""Capability layer for JARVIS cloud/local AI providers.

Keeps provider-specific multimodal features behind one small interface. API keys are
read only from environment variables; they are never stored in the repository.
The module intentionally returns concise observations rather than private model
reasoning.
"""

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any


def _read_image(path: str | Path) -> tuple[str, str]:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Imagen no encontrada: {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        raise ValueError("El archivo no es una imagen compatible")
    return mime, base64.b64encode(p.read_bytes()).decode("ascii")


def _openai_client(api_key: str | None):
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception:
        return None


class CapabilityGateway:
    """Use the APIs for capabilities that go beyond ordinary text chat."""

    def __init__(self, providers: dict[str, Any] | None = None):
        self.providers = providers or {}

    def capabilities(self) -> dict[str, dict[str, bool]]:
        return {
            "ChatGPT": {
                "text": bool(os.getenv("OPENAI_API_KEY")),
                "vision": bool(os.getenv("OPENAI_API_KEY")),
                "image_generation": bool(os.getenv("OPENAI_API_KEY")),
            },
            "Claude": {
                "text": bool(os.getenv("ANTHROPIC_API_KEY")),
                "vision": bool(os.getenv("ANTHROPIC_API_KEY")),
                "image_generation": False,
            },
            "Gemini": {
                "text": bool(os.getenv("GEMINI_API_KEY")),
                "vision": bool(os.getenv("GEMINI_API_KEY")),
                "image_generation": bool(os.getenv("GEMINI_API_KEY")),
            },
            "Grok": {
                "text": bool(os.getenv("XAI_API_KEY")),
                "vision": bool(os.getenv("XAI_API_KEY")),
                "image_generation": bool(os.getenv("XAI_API_KEY")),
            },
            "Ollama": {
                "text": True,
                "vision": True,
                "image_generation": False,
            },
        }

    def vision(self, image_path: str | Path, instruction: str, preferred: str = "AUTO") -> dict[str, Any]:
        """Ask an available multimodal model to inspect one screenshot/image.

        The caller receives a normal observation and provider name. The model is
        never asked for hidden chain-of-thought.
        """
        mime, data = _read_image(image_path)
        order = self._provider_order(preferred)
        errors: list[str] = []
        for name in order:
            try:
                if name == "ChatGPT":
                    text = self._openai_vision(mime, data, instruction)
                elif name == "Claude":
                    text = self._claude_vision(mime, data, instruction)
                elif name == "Gemini":
                    text = self._gemini_vision(mime, data, instruction)
                elif name == "Grok":
                    text = self._xai_vision(mime, data, instruction)
                else:
                    continue
                if text:
                    return {"ok": True, "provider": name, "observation": text}
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return {"ok": False, "provider": None, "observation": "", "errors": errors}

    def generate_image(self, prompt: str, output_path: str | Path, preferred: str = "AUTO") -> dict[str, Any]:
        """Generate an image using a configured image-capable cloud provider."""
        target = Path(output_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        order = self._provider_order(preferred)
        errors: list[str] = []
        for name in order:
            try:
                if name == "ChatGPT":
                    data = self._openai_image(prompt)
                elif name == "Grok":
                    data = self._xai_image(prompt)
                elif name == "Gemini":
                    data = self._gemini_image(prompt)
                else:
                    continue
                if data:
                    target.write_bytes(data)
                    return {"ok": True, "provider": name, "path": str(target)}
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return {"ok": False, "provider": None, "path": None, "errors": errors}

    def _provider_order(self, preferred: str) -> list[str]:
        if preferred and preferred.upper() != "AUTO":
            return [preferred]
        return ["ChatGPT", "Gemini", "Grok", "Claude", "Ollama"]

    @staticmethod
    def _openai_vision(mime: str, data: str, instruction: str) -> str:
        client = _openai_client(os.getenv("OPENAI_API_KEY"))
        if not client:
            raise RuntimeError("SDK OpenAI no disponible")
        model = os.getenv("OPENAI_VISION_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.1"))
        response = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": instruction},
                {"type": "input_image", "image_url": f"data:{mime};base64,{data}"},
            ]}],
        )
        return str(response.output_text or "").strip()

    @staticmethod
    def _claude_vision(mime: str, data: str, instruction: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=os.getenv("CLAUDE_VISION_MODEL", os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")),
            max_tokens=2200,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
                {"type": "text", "text": instruction},
            ]}],
        )
        return "\n".join(getattr(block, "text", "") for block in response.content).strip()

    @staticmethod
    def _gemini_vision(mime: str, data: str, instruction: str) -> str:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))
        response = client.models.generate_content(
            model=model,
            contents=[types.Part.from_bytes(data=base64.b64decode(data), mime_type=mime), instruction],
        )
        return str(getattr(response, "text", "") or "").strip()

    @staticmethod
    def _xai_vision(mime: str, data: str, instruction: str) -> str:
        client = _openai_client(os.getenv("XAI_API_KEY"))
        if not client:
            raise RuntimeError("SDK OpenAI/xAI no disponible")
        model = os.getenv("GROK_VISION_MODEL", os.getenv("GROK_MODEL", "grok-4.5"))
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": instruction},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
            ]}],
        )
        return str(response.choices[0].message.content or "").strip()

    @staticmethod
    def _openai_image(prompt: str) -> bytes:
        client = _openai_client(os.getenv("OPENAI_API_KEY"))
        if not client:
            raise RuntimeError("SDK OpenAI no disponible")
        response = client.images.generate(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            prompt=prompt,
        )
        item = response.data[0]
        if getattr(item, "b64_json", None):
            return base64.b64decode(item.b64_json)
        raise RuntimeError("OpenAI no devolvió una imagen base64")

    @staticmethod
    def _xai_image(prompt: str) -> bytes:
        raise RuntimeError("La generación de imágenes de xAI depende del modelo/API habilitado en la cuenta; no se asume disponibilidad.")

    @staticmethod
    def _gemini_image(prompt: str) -> bytes:
        raise RuntimeError("La generación de imágenes de Gemini requiere un modelo de imagen habilitado; configura GEMINI_IMAGE_MODEL para activarla.")
