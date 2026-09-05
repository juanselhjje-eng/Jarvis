from __future__ import annotations

import os
import re
import threading
from typing import Optional

import numpy as np
import pyttsx3
import sounddevice as sd
from faster_whisper import WhisperModel

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv:
    load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_LANGUAGE = "es"
SAMPLE_RATE = 16000
WAKE_WORDS = tuple(
    word.strip().lower()
    for word in os.getenv("JARVIS_WAKE_WORDS", "jarvis,viernes").split(",")
    if word.strip()
)
VOICE_RATE = 175
VOICE_VOLUME = 1.0


class VoiceEngine:
    """Entrada y salida de voz local. No envía audio a servicios externos."""

    def __init__(self) -> None:
        self.tts = None
        self.whisper: Optional[WhisperModel] = None
        self._tts_lock = threading.Lock()
        self._load_tts()

    def _load_tts(self) -> None:
        try:
            self.tts = pyttsx3.init()
            self.tts.setProperty("rate", VOICE_RATE)
            self.tts.setProperty("volume", VOICE_VOLUME)
            voices = self.tts.getProperty("voices") or []
            for voice in voices:
                data = f"{voice.id} {voice.name}".lower()
                if "spanish" in data or "es_" in data or "español" in data or "es-" in data:
                    self.tts.setProperty("voice", voice.id)
                    break
            print("[VOICE] TTS listo.")
        except Exception as exc:
            print(f"[VOICE] No se pudo iniciar TTS: {exc}")

    def speak(self, text: str) -> None:
        if not text or self.tts is None:
            return
        with self._tts_lock:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as exc:
                print(f"[VOICE] Error TTS: {exc}")

    def load_whisper(self) -> None:
        if self.whisper is None:
            print(f"[VOICE] Cargando faster-whisper ({WHISPER_MODEL})...")
            self.whisper = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            print("[VOICE] Whisper listo.")

    def record(self, seconds: float = 7.0) -> np.ndarray:
        frames = int(seconds * SAMPLE_RATE)
        print("[VOICE] Escuchando...")
        audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        return audio.flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        self.load_whisper()
        segments, _ = self.whisper.transcribe(
            audio,
            language=WHISPER_LANGUAGE,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

    def listen(self, seconds: float = 7.0) -> str:
        return self.transcribe(self.record(seconds))

    def has_wake_word(self, text: str) -> bool:
        normalized = text.lower()
        return any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in WAKE_WORDS)

    def remove_wake_word(self, text: str) -> str:
        result = text
        for word in WAKE_WORDS:
            result = re.sub(rf"\b{re.escape(word)}\b", "", result, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", result).strip()

    def listen_for_command(self, seconds: float = 7.0) -> Optional[str]:
        text = self.listen(seconds)
        print(f"[VOICE] Reconocido: {text}")
        if not text or not self.has_wake_word(text):
            return None
        command = self.remove_wake_word(text)
        return command or None

    def shutdown(self) -> None:
        try:
            if self.tts:
                self.tts.stop()
        except Exception:
            pass
