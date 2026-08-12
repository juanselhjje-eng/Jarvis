from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading
import time
from pathlib import Path


DEFAULT_VOICE = "es-CO-GonzaloNeural"


def _clean_text(text: str) -> str:
    text = re.sub(r"\[[^\]]{0,120}\]", " ", str(text or ""))
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:6500]


def _prosody(text: str) -> tuple[str, str, str]:
    """Return rate, pitch and volume for a natural conversational delivery."""
    low = text.lower()
    rate = "+4%"
    pitch = "-2Hz"
    volume = "+0%"
    if len(text) < 90:
        rate = "+7%"
    if "?" in text or "¿" in text:
        rate = "+2%"
        pitch = "+1Hz"
    if any(x in low for x in ("error", "problema", "falló", "fallo", "no pude")):
        rate = "-4%"
        pitch = "-3Hz"
    if any(x in low for x in ("excelente", "perfecto", "encontré", "hecho", "completado")):
        pitch = "+1Hz"
    return rate, pitch, volume


class NeuralTTS:
    """Optional cloud neural TTS with a local pyttsx3 fallback.

    The default Microsoft neural voice is Colombian Spanish. It is a stock
    synthetic voice, not a clone of a real creator's voice. Prosody changes
    slightly with context so JARVIS sounds conversational instead of reading
    every response with identical cadence.
    """

    def __init__(self, queue, stop_event, speaking_changed, engine_factory):
        self.queue = queue
        self.stop_event = stop_event
        self.speaking_changed = speaking_changed
        self.engine_factory = engine_factory
        self.voice = os.getenv("JARVIS_TTS_VOICE", DEFAULT_VOICE)
        self.enabled = os.getenv("JARVIS_TTS_BACKEND", "neural").lower() != "local"
        self._pygame_ready = False
        self._lock = threading.RLock()
        self._temp_files: set[str] = set()

    def _play(self, path: str) -> None:
        import pygame
        with self._lock:
            if not self._pygame_ready:
                pygame.mixer.init()
                self._pygame_ready = True
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        while pygame.mixer.music.get_busy() and not self.stop_event.is_set():
            time.sleep(0.04)
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    async def _synthesize(self, text: str, path: str) -> None:
        import edge_tts
        rate, pitch, volume = _prosody(text)
        communicator = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        await communicator.save(path)

    def speak_neural(self, text: str) -> bool:
        path = ""
        try:
            fd, path = tempfile.mkstemp(prefix="jarvis_voice_", suffix=".mp3")
            os.close(fd)
            self._temp_files.add(path)
            asyncio.run(self._synthesize(text, path))
            if self.stop_event.is_set():
                return False
            self._play(path)
            return True
        except Exception:
            return False
        finally:
            if path:
                self._temp_files.discard(path)
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception:
                    pass

    def cleanup(self) -> None:
        try:
            import pygame
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        for path in list(self._temp_files):
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        self._temp_files.clear()
