from PySide6.QtCore import QObject, Signal
import threading
import queue
import time


class Speaker(QObject):
    state_changed = Signal(bool)
    speaking_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.enabled = True
        self._engine = None
        self._queue = queue.Queue(maxsize=32)
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._engine_lock = threading.RLock()
        self._rate = 185
        self._volume = 1.0
        self._voice_id = ""
        self._thread = threading.Thread(target=self._speech_loop, daemon=True, name="JARVIS-TTS")
        self._thread.start()
        self._ready.wait(timeout=8)

    def _create_engine(self):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        if self._voice_id:
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

    def _speech_loop(self):
        try:
            self._engine = self._create_engine()
        except Exception:
            self._engine = None
        finally:
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
                if self._engine is None and not self._restart_engine():
                    raise RuntimeError("TTS engine unavailable")
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
                    success = True
            except Exception:
                # pyttsx3 engines can become invalid after an utterance. Rebuild it
                # and retry once so later messages are not silently lost.
                try:
                    if self._restart_engine():
                        with self._engine_lock:
                            self.speaking_changed.emit(True)
                            self._engine.say(str(text))
                            self._engine.runAndWait()
                            success = True
                except Exception:
                    success = False
            finally:
                self.speaking_changed.emit(False)
                self._queue.task_done()

    @property
    def available(self):
        return self._engine is not None

    def configure(self, cfg):
        try:
            self._rate = max(80, min(300, int(cfg.get("rate", 185))))
            self._volume = max(0.0, min(1.0, float(cfg.get("volume", 1.0))))
            self._voice_id = cfg.get("voice_id", "") or ""
            if self._engine:
                self._restart_engine()
        except Exception:
            pass

    def speak(self, text):
        text = str(text or "").strip()
        if not self.enabled or not text:
            return False
        if not self._ready.wait(timeout=8):
            return False
        # Keep spoken replies useful instead of allowing a large backlog to form.
        if len(text) > 7000:
            text = text[:7000] + "…"
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
