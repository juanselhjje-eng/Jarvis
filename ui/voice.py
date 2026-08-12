from PySide6.QtCore import QObject, Signal
import threading
import queue

class Speaker(QObject):
    state_changed = Signal(bool)
    speaking_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.enabled = True
        self._engine = None
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._rate = 185
        self._volume = 1.0
        self._voice_id = ""
        self._thread = threading.Thread(target=self._speech_loop, daemon=True, name="JARVIS-TTS")
        self._thread.start()
        self._ready.wait(timeout=5)

    def _speech_loop(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            self._engine = engine
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            self._ready.set()
        except Exception:
            self._ready.set()
            return

        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            text, rate, volume, voice_id = item
            try:
                engine.setProperty("rate", rate)
                engine.setProperty("volume", volume)
                if voice_id:
                    try:
                        engine.setProperty("voice", voice_id)
                    except Exception:
                        pass
                self.speaking_changed.emit(True)
                engine.say(str(text))
                engine.runAndWait()
            except Exception:
                # Keep the TTS worker alive even if one utterance fails.
                try:
                    engine.stop()
                except Exception:
                    pass
            finally:
                self.speaking_changed.emit(False)
                self._queue.task_done()

    @property
    def available(self):
        return self._engine is not None

    def configure(self, cfg):
        try:
            self._rate = int(cfg.get("rate", 185))
            self._volume = float(cfg.get("volume", 1.0))
            self._voice_id = cfg.get("voice_id", "") or ""
        except Exception:
            pass

    def speak(self, text):
        text = str(text or "").strip()
        if not self.enabled or not text:
            return False
        if not self._ready.wait(timeout=5) or self._engine is None:
            return False
        self._queue.put((text, self._rate, self._volume, self._voice_id))
        return True

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
        threading.Thread(target=worker, daemon=True).start()
