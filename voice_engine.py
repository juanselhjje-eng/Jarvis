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

try:
    from elevenlabs.client import ElevenLabs
except ImportError:  # pragma: no cover
    ElevenLabs = None

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

TTS_PROVIDER = os.getenv("JARVIS_TTS", "elevenlabs").strip().lower()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2").strip()
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "pcm_44100").strip()
VOICE_RATE = 175
VOICE_VOLUME = 1.0


class VoiceEngine:
    """Entrada por voz local y salida TTS con ElevenLabs o pyttsx3 de respaldo."""

    def __init__(self) -> None:
        self.tts = None
        self.elevenlabs = None
        self.whisper: Optional[WhisperModel] = None
        self._tts_lock = threading.Lock()
        self._load_tts()

    def _load_tts(self) -> None:
        if TTS_PROVIDER == "elevenlabs":
            if ElevenLabs is None:
                print("[VOICE] Falta el paquete 'elevenlabs'. Se usará pyttsx3.")
            elif not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
                print("[VOICE] ElevenLabs no está configurado. Se usará pyttsx3.")
            else:
                try:
                    self.elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                    print(f"[VOICE] ElevenLabs listo. Modelo: {ELEVENLABS_MODEL}")
                    return
                except Exception as exc:
                    print(f"[VOICE] No se pudo iniciar ElevenLabs: {exc}")

        self._load_pyttsx3()

    def _load_pyttsx3(self) -> None:
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
            print("[VOICE] TTS local de respaldo listo.")
        except Exception as exc:
            print(f"[VOICE] No se pudo iniciar TTS local: {exc}")

    def _speak_elevenlabs(self, text: str) -> bool:
        if self.elevenlabs is None:
            return False

        try:
            audio = self.elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id=ELEVENLABS_MODEL,
                output_format=ELEVENLABS_OUTPUT_FORMAT,
            )
            audio_bytes = b"".join(audio) if not isinstance(audio, bytes) else audio
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            if samples.size == 0:
                return False
            sd.play(samples, samplerate=44100, blocking=True)
            return True
        except Exception as exc:
            print(f"[VOICE] ElevenLabs falló: {exc}")
            return False

    def speak(self, text: str) -> None:
        if not text:
            return

        with self._tts_lock:
            if TTS_PROVIDER == "elevenlabs" and self._speak_elevenlabs(text):
                return

            if self.tts is None:
                return
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as exc:
                print(f"[VOICE] Error TTS local: {exc}")

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
            sd.stop()
            if self.tts:
                self.tts.stop()
        except Exception:
            pass
