from typing import List, Dict, Any
import ollama
import time
from config.settings import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_CONTEXT, OLLAMA_TEMPERATURE

class OllamaProvider:
    def __init__(self, model=OLLAMA_MODEL, host=OLLAMA_HOST):
        self.name = "Ollama"
        self.model = model
        self.host = host
        self.client = ollama.Client(host=host)
        self._availability_cache = None
        self._availability_checked = 0.0
        self._availability_ttl = 45.0

    def is_available(self):
        # Ollama /api/tags is relatively cheap, but polling it every UI tick
        # creates unnecessary traffic. Cache the health result briefly.
        now = time.monotonic()
        if self._availability_cache is not None and now - self._availability_checked < self._availability_ttl:
            return bool(self._availability_cache)
        try:
            self.client.list()
            self._availability_cache = True
        except Exception:
            self._availability_cache = False
        self._availability_checked = now
        return bool(self._availability_cache)

    def refresh_availability(self):
        self._availability_cache = None
        self._availability_checked = 0.0
        return self.is_available()

    def chat(self, messages: List[Dict[str, Any]], tools=None, temperature=OLLAMA_TEMPERATURE, think=False):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": bool(think),
            "options": {"temperature": temperature, "num_ctx": OLLAMA_CONTEXT},
        }
        if tools:
            kwargs["tools"] = tools
        return self.client.chat(**kwargs)

    def set_model(self, model):
        self.model = model
