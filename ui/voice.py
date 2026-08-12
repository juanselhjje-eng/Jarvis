from PySide6.QtCore import QObject, Signal
import os
import threading
import queue


class Speaker(QObject):
    """JARVIS TTS robusto: voz continua con fallback automático."""

    state_changed = Signal(bool)
    speaking_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.enabled = True
        self.backend = os.getenv("JARVIS_TTS_BACKEND", "neural").lower()
        self._engine = None
        self._neural = None
        self._queue = queue.Queue(maxsize=8)
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._engine_lock = threading.RLock()
        self._rate = 185
        self._volume = 1.0
        self._voice_id = os.getenv("JARVIS_TTS_VOICE", "es-CO-GonzaloNeural")
        self._thread = threading.Thread(target=self._speech_loop, daemon=True, name="JARVIS-TTS")
        self._thread.start()
        self._ready.wait(timeout=8)

    def _create_engine(self):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        if self._voice_id and self.backend == "local":
            try:
                engine.setProperty("voice", self._voice_id)
            except Exception:
                pass
        return engine

    def _restart_engine(self):
        with self._engine_lock:
            try:
                if self._engine:
                    self._engine.stop()
            except Exception:
                pass
            try:
                self._engine = self._create_engine()
                return True
            except Exception:
                self._engine = None
                return False

    def _init_neural(self):
        if self.backend == "local":
            return False
        try:
            from voice.neural_tts import NeuralTTS
            self._neural = NeuralTTS(
                queue=self._queue,
                stop_event=self._stop_event,
                speaking_changed=self.speaking_changed,
                engine_factory=self._create_engine,
            )
            return True
        except Exception:
            self._neural = None
            return False

    def _speak_local(self, text, rate, volume, voice_id):
        if self._engine is None and not self._restart_engine():
            raise RuntimeError("TTS local no disponible")
        with self._engine_lock:
            self._engine.setProperty("rate", rate)
            self._engine.setProperty("volume", volume)
            if voice_id:
                try:
                    self._engine.setProperty("voice", voice_id)
                except Exception:
                    pass
            self.speaking_changed.emit(True)
            self._engine.say(str(text))
            self._engine.runAndWait()

    def _try_neural(self, text):
        """Intenta voz neural sin convertir un fallo temporal en estado permanente."""
        if not self._neural or self.backend == "local":
            return False
        try:
            self.speaking_changed.emit(True)
            ok = bool(self._neural.speak_neural(text))
            return ok
        except Exception:
            return False
        finally:
            self.speaking_changed.emit(False)

    def _speech_loop(self):
        neural_ok = self._init_neural()
        if not neural_ok:
            self._restart_engine()
        self._ready.set()

        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                self._queue.task_done()
                break

            text, rate, volume, voice_id = item
            success = False
            try:
                # No desactives el backend neural después de un fallo: el fallo puede
                # ser temporal. Cada respuesta vuelve a intentarlo y luego cae a local.
                success = self._try_neural(text)
                if not success:
                    try:
                        self._speak_local(text, rate, volume, voice_id)
                        success = True
                    except Exception:
                        # pyttsx3 puede quedar bloqueado después de una reproducción;
                        # reconstruimos el motor y repetimos una sola vez.
                        if self._restart_engine():
                            self._speak_local(text, rate, volume, voice_id)
                            success = True
            except Exception:
                success = False
            finally:
                self.speaking_changed.emit(False)
                self._queue.task_done()

    @property
    def available(self):
        return bool(self._neural) or self._engine is not None

    def configure(self, cfg):
        try:
            self._rate = max(80, min(300, int(cfg.get("rate", 185))))
            self._volume = max(0.0, min(1.0, float(cfg.get("volume", 1.0))))
            self._voice_id = cfg.get("voice_id", "") or self._voice_id
            requested = str(cfg.get("backend", self.backend)).lower()
            if requested in {"neural", "local"}:
                self.backend = requested
            if self.backend == "local":
                self._restart_engine()
            elif self._neural is None:
                self._init_neural()
        except Exception:
            pass

    def speak(self, text):
        text = str(text or "").strip()
        if not self.enabled or not text:
            return False
        if not self._ready.wait(timeout=8):
            return False
        if len(text) > 6500:
            text = text[:6500] + "…"

        # Conserva siempre las respuestas más recientes; evita que una respuesta
        # lenta bloquee las siguientes durante una conversación larga.
        if self._queue.qsize() >= 5:
            try:
                while self._queue.qsize() >= 3:
                    self._queue.get_nowait()
                    self._queue.task_done()
            except queue.Empty:
                pass
        try:
            self._queue.put_nowait((text, self._rate, self._volume, self._voice_id))
            return True
        except queue.Full:
            return False

    def stop(self):
        try:
            while True:
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
        try:
            if self._neural:
                self._neural.cleanup()
        except Exception:
            pass

    def toggle(self):
        self.enabled = not self.enabled
        self.state_changed.emit(self.enabled)
        if not self.enabled:
            self.stop()
        return self.enabled

    def shutdown(self):
        self._stop_event.set()
        self.stop()
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass


class Listener(QObject):
    recognized = Signal(str)
    failed = Signal(str)

    def listen_once(self):
        def worker():
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=.2)
                    audio = r.listen(source, timeout=5, phrase_time_limit=12)
                text = r.recognize_google(audio, language="es-CO")
                self.recognized.emit(text)
            except Exception as exc:
                self.failed.emit(str(exc))
        threading.Thread(target=worker, daemon=True, name="JARVIS-STT").start()
