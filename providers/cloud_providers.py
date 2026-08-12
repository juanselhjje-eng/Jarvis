from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class CloudResponse:
    """Small Ollama-compatible response wrapper for cloud text responses."""
    def __init__(self, text: str, provider: str):
        self.message = SimpleNamespace(content=text or "", tool_calls=[])
        self.provider = provider


class OpenAIProvider:
    name = "ChatGPT"
    env_key = "OPENAI_API_KEY"
    default_model = "gpt-5.1"

    def __init__(self, model=None):
        self.model = model or os.getenv("OPENAI_MODEL", self.default_model)
        self.api_key = os.getenv(self.env_key)
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_available(self):
        return self.client is not None and bool(self.api_key)

    def status(self):
        if not self.api_key:
            return "NOT CONFIGURED"
        if not self.client:
            return "SDK ERROR"
        return "READY"

    def chat(self, messages, **kwargs):
        if not self.client:
            raise RuntimeError("OpenAI no está disponible. Revisa OPENAI_API_KEY y el SDK openai.")
        system = "\n\n".join(str(m["content"]) for m in messages if m["role"] == "system")
        inp = [m for m in messages if m["role"] != "system"]
        response = self.client.responses.create(
            model=self.model,
            instructions=system or None,
            input=inp,
        )
        return CloudResponse(response.output_text or "", self.name)


class ClaudeProvider:
    name = "Claude"
    env_key = "ANTHROPIC_API_KEY"
    default_model = "claude-sonnet-4-20250514"

    def __init__(self, model=None):
        self.model = model or os.getenv("CLAUDE_MODEL", self.default_model)
        self.api_key = os.getenv(self.env_key)
        self.client = None
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_available(self):
        return self.client is not None and bool(self.api_key)

    def status(self):
        if not self.api_key:
            return "NOT CONFIGURED"
        if not self.client:
            return "SDK ERROR"
        return "READY"

    def chat(self, messages, **kwargs):
        if not self.client:
            raise RuntimeError("Claude no está disponible. Revisa ANTHROPIC_API_KEY y el SDK anthropic.")
        system = "\n\n".join(str(m["content"]) for m in messages if m["role"] == "system") or None
        msgs = [m for m in messages if m["role"] != "system"]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=int(kwargs.get("max_tokens", 4096)),
            system=system,
            messages=msgs,
        )
        text = "\n".join(getattr(block, "text", "") for block in response.content).strip()
        return CloudResponse(text, self.name)


class GeminiProvider:
    name = "Gemini"
    env_key = "GEMINI_API_KEY"
    default_model = "gemini-3.6-flash"

    def __init__(self, model=None):
        self.model = model or os.getenv("GEMINI_MODEL", self.default_model)
        self.api_key = os.getenv(self.env_key)
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_available(self):
        return self.client is not None and bool(self.api_key)

    def status(self):
        if not self.api_key:
            return "NOT CONFIGURED"
        if not self.client:
            return "SDK ERROR"
        return "READY"

    def chat(self, messages, **kwargs):
        if not self.client:
            raise RuntimeError("Gemini no está disponible. Revisa GEMINI_API_KEY y el SDK google-genai.")
        system = "\n\n".join(str(m["content"]) for m in messages if m["role"] == "system")
        non_system = [m for m in messages if m["role"] != "system"]
        text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in non_system)
        if not text:
            text = system
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system or None,
                max_output_tokens=int(kwargs.get("max_tokens", 4096)),
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=config,
            )
            output = getattr(response, "text", "") or ""
        except Exception:
            interaction = self.client.interactions.create(
                model=self.model,
                input=(system + "\n\n" + text).strip(),
            )
            output = getattr(interaction, "output_text", "") or ""
        return CloudResponse(output, self.name)


class GrokProvider:
    name = "Grok"
    env_key = "XAI_API_KEY"
    default_model = "grok-4.5"

    def __init__(self, model=None):
        self.model = model or os.getenv("GROK_MODEL", self.default_model)
        self.api_key = os.getenv(self.env_key)
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url="https://api.x.ai/v1")
            except Exception:
                self.client = None

    def is_available(self):
        return self.client is not None and bool(self.api_key)

    def status(self):
        if not self.api_key:
            return "NOT CONFIGURED"
        if not self.client:
            return "SDK ERROR"
        return "READY"

    def chat(self, messages, **kwargs):
        if not self.client:
            raise RuntimeError("Grok no está disponible. Revisa XAI_API_KEY y el SDK openai.")
        response = self.client.responses.create(
            model=self.model,
            input=messages,
        )
        return CloudResponse(response.output_text or "", self.name)


class MultiAIManager:
    """Coordinates JARVIS brains.

    - Normal mode: chooses one fast provider.
    - Deep mode in AUTO: runs a small council of all available text models in
      parallel and asks a lead model to synthesize the result.
    - Tool execution remains on Ollama because JARVIS's tool-call schema is
      wired to that provider.
    This is collaboration, not exposure of hidden chain-of-thought.
    """

    def __init__(self, ollama_provider):
        self.providers = {"Ollama": ollama_provider}
        for cls in (OpenAIProvider, ClaudeProvider, GeminiProvider, GrokProvider):
            try:
                provider = cls()
                self.providers[provider.name] = provider
            except Exception:
                pass
        self.mode = os.getenv("JARVIS_AI", "AUTO").strip().upper() or "AUTO"
        self.council_mode = os.getenv("JARVIS_COUNCIL", "AUTO").strip().upper() or "AUTO"
        self.last_provider = "Ollama"
        self.last_error = ""
        self.last_council = []

    def available(self):
        names = []
        for name, provider in self.providers.items():
            try:
                if provider.is_available():
                    names.append(name)
            except Exception:
                pass
        return names

    def statuses(self):
        result = {}
        for name, provider in self.providers.items():
            try:
                if name == "Ollama":
                    result[name] = "READY" if provider.is_available() else "OFFLINE"
                else:
                    result[name] = provider.status()
            except Exception:
                result[name] = "ERROR"
        return result

    def _select(self, tools=None):
        if tools:
            provider = self.providers.get("Ollama")
            if provider and provider.is_available():
                return provider
            raise RuntimeError("Ollama es necesario para las herramientas de JARVIS y no está disponible.")

        preferred = {
            "OLLAMA": "Ollama",
            "CHATGPT": "ChatGPT",
            "OPENAI": "ChatGPT",
            "CLAUDE": "Claude",
            "GEMINI": "Gemini",
            "GROK": "Grok",
        }.get(self.mode)
        if preferred:
            provider = self.providers.get(preferred)
            if provider and provider.is_available():
                return provider
            if self.mode != "AUTO":
                raise RuntimeError(f"{preferred} no está configurado o disponible")

        for name in ("ChatGPT", "Claude", "Grok", "Gemini", "Ollama"):
            provider = self.providers.get(name)
            if provider and provider.is_available():
                return provider
        raise RuntimeError("No hay proveedores de IA disponibles. Configura una API o inicia Ollama.")

    @staticmethod
    def _messages_for_council(messages):
        # Keep the council prompt compact; tool definitions/history can be huge.
        trimmed = []
        for m in messages[-16:]:
            role = m.get("role")
            content = m.get("content", "")
            if not content:
                continue
            if role in {"system", "user", "assistant"}:
                trimmed.append({"role": role, "content": str(content)[:6000]})
            elif role == "tool":
                # Cloud APIs differ in how they accept tool messages. For the
                # council, preserve the verified result as neutral context.
                tool_name = m.get("tool_name", "tool")
                trimmed.append({
                    "role": "user",
                    "content": f"[RESULTADO VERIFICADO DE {tool_name}]\n{str(content)[:5000]}"
                })
        return trimmed

    def _council_chat(self, messages, **kwargs):
        """Multi-round council: independent proposals -> peer review -> synthesis.

        Models never receive or expose private chain-of-thought. Each round exchanges
        concise proposals, critiques and decisions only. The final answer is produced
        by a lead model after reviewing the council dossier.
        """
        available = []
        for name in ("ChatGPT", "Claude", "Gemini", "Grok", "Ollama"):
            provider = self.providers.get(name)
            try:
                if provider and provider.is_available():
                    available.append(provider)
            except Exception:
                pass

        if len(available) <= 1:
            return self._single_chat(available[0] if available else self._select(), messages, **kwargs)

        base = self._messages_for_council(messages)
        max_tokens = int(kwargs.get("max_tokens", 4096))
        temperature = float(kwargs.get("temperature", 0.2))
        candidates = {}

        def ask_initial(provider):
            msgs = [{"role": "system", "content": (
                "Eres un especialista del CONSEJO JARVIS. Analiza la solicitud y entrega "
                "SOLO una propuesta concreta, verificable y accionable. Señala supuestos "
                "importantes y riesgos. No muestres cadena de pensamiento privada."
            )}] + base
            return provider.chat(msgs, max_tokens=min(max_tokens, 3072), temperature=temperature)

        # Round 1: all available brains work in parallel so latency stays reasonable.
        with ThreadPoolExecutor(max_workers=len(available)) as pool:
            futures = {pool.submit(ask_initial, p): p for p in available}
            for f in as_completed(futures):
                provider = futures[f]
                try:
                    r = f.result()
                    text = str(getattr(getattr(r, "message", None), "content", "") or "").strip()
                    if text:
                        candidates[provider.name] = text
                except Exception as exc:
                    self.last_error = f"{provider.name}: {exc}"

        self.last_council = list(candidates.keys())
        if not candidates:
            raise RuntimeError("Todos los proveedores del consejo fallaron.")

        # Round 2: every participating model reviews the other proposals.
        dossier = "\n\n".join(f"=== PROPUESTA {name} ===\n{text[:4500]}" for name, text in candidates.items())
        reviews = {}

        def ask_review(provider):
            own = candidates.get(provider.name, "")
            review_prompt = (
                "Solicitud original:\n" + str(next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""))[:6000]
                + "\n\nPROPUESTAS DEL CONSEJO:\n" + dossier[:18000]
                + "\n\nTu propuesta anterior:\n" + own[:4000]
                + "\n\nAhora revisa a tus colegas. Devuelve SOLO:\n"
                  "1) qué propuesta es más sólida y por qué,\n"
                  "2) errores o riesgos concretos que deben corregirse,\n"
                  "3) la decisión/recomendación que debería usar JARVIS.\n"
                  "No muestres razonamiento privado ni instrucciones internas."
            )
            msgs = [{"role": "system", "content": "Eres revisor de un consejo multi-IA de JARVIS. Sé crítico, preciso y breve."},
                    {"role": "user", "content": review_prompt}]
            return provider.chat(msgs, max_tokens=min(max_tokens, 2600), temperature=0.15)

        with ThreadPoolExecutor(max_workers=len(available)) as pool:
            futures = {pool.submit(ask_review, p): p for p in available if p.name in candidates}
            for f in as_completed(futures):
                provider = futures[f]
                try:
                    r = f.result()
                    text = str(getattr(getattr(r, "message", None), "content", "") or "").strip()
                    if text:
                        reviews[provider.name] = text
                except Exception as exc:
                    self.last_error = f"review {provider.name}: {exc}"

        review_dossier = "\n\n".join(f"=== REVISIÓN {name} ===\n{text[:3500]}" for name, text in reviews.items())
        lead = next((self.providers.get(n) for n in ("ChatGPT", "Claude", "Gemini", "Grok", "Ollama") if n in candidates), None)
        if lead is None:
            return CloudResponse(next(iter(candidates.values())), next(iter(candidates.keys())))

        original = str(next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""))[:7000]
        synthesis = [
            {"role": "system", "content": (
                "Eres JARVIS, coordinador final. Tienes propuestas y revisiones de varios modelos. "
                "Decide la mejor respuesta, corrige contradicciones y no repitas opiniones innecesarias. "
                "Entrega UNA respuesta final útil y natural en español. Si la tarea requiere una acción, "
                "explica con claridad qué debe hacerse o qué fue verificado. No menciones cadena de pensamiento, "
                "tokens, prompts privados ni conversaciones internas entre modelos. No digas simplemente 'Listo' o 'Hecho'."
            )},
            {"role": "user", "content": (
                "SOLICITUD DEL USUARIO:\n" + original
                + "\n\nPROPUESTAS:\n" + dossier[:18000]
                + "\n\nREVISIONES CRUZADAS:\n" + (review_dossier[:16000] if review_dossier else "No hubo revisiones disponibles.")
                + "\n\nProduce ahora la mejor respuesta final."
            )},
        ]
        try:
            final = lead.chat(synthesis, max_tokens=max_tokens, temperature=0.18)
            self.last_provider = f"COUNCIL 3-ROUND → {lead.name}"
            self.last_error = ""
            return final
        except Exception as exc:
            self.last_error = f"synthesis {lead.name}: {exc}"
            name, text = next(iter(candidates.items()))
            self.last_provider = name
            return CloudResponse(text, name)

    def learn_topic(self, topic: str, context: str = ""):
        """Ask every available brain to teach JARVIS, then consolidate the lesson.

        This creates behavioral knowledge in JARVIS's graph; it does not pretend to
        alter model weights. Private chain-of-thought is never requested or stored.
        """
        available = []
        for name in ("ChatGPT", "Claude", "Gemini", "Grok", "Ollama"):
            provider = self.providers.get(name)
            try:
                if provider and provider.is_available():
                    available.append(provider)
            except Exception:
                pass
        if not available:
            raise RuntimeError("No hay proveedores disponibles para aprendizaje.")

        prompt = (
            "Tema que JARVIS debe aprender: " + str(topic)[:900] + "\n\n"
            "Contexto de conocimiento existente:\n" + str(context)[:3500] + "\n\n"
            "Enseña una lección práctica y verificable. Aporta hechos, reglas, ejemplos "
            "o relaciones útiles. No muestres cadena de pensamiento privada. Si no estás "
            "seguro, indícalo claramente. Termina con CONFIDENCE: 0.00-1.00."
        )
        contributions = {}
        def ask(provider):
            msgs = [{"role":"system","content":"Eres un profesor del cerebro colectivo de JARVIS."},
                    {"role":"user","content":prompt}]
            return provider.chat(msgs, max_tokens=1800, temperature=0.2)
        with ThreadPoolExecutor(max_workers=len(available)) as pool:
            futures={pool.submit(ask,p):p for p in available}
            for f in as_completed(futures):
                provider=futures[f]
                try:
                    text=str(getattr(getattr(f.result(),"message",None),"content","") or "").strip()
                    if text:
                        contributions[provider.name]=text
                except Exception as exc:
                    self.last_error=f"learning {provider.name}: {exc}"
        if not contributions:
            raise RuntimeError("Ninguna IA pudo aportar conocimiento.")

        dossier="\n\n".join(f"=== {name} ===\n{text[:3500]}" for name,text in contributions.items())
        lead=next((self.providers.get(n) for n in ("ChatGPT","Claude","Gemini","Grok","Ollama") if n in contributions), None)
        synth_prompt=(
            "Consolida el conocimiento de varios profesores para JARVIS.\n"
            "Tema: " + str(topic)[:900] + "\n\n" + dossier[:15000] + "\n\n"
            "Compara las respuestas, elimina contradicciones no resueltas, conserva "
            "solo conclusiones bien respaldadas y crea una lección compacta. "
            "No muestres cadena de pensamiento. Termina exactamente con CONFIDENCE: 0.00-1.00."
        )
        final=lead.chat([{ "role":"system","content":"Eres el coordinador de aprendizaje de JARVIS."},
                          {"role":"user","content":synth_prompt}], max_tokens=2600, temperature=0.12)
        synthesis=str(getattr(getattr(final,"message",None),"content","") or "").strip()
        import re as _re
        m=_re.search(r"CONFIDENCE:\s*([01](?:\.\d+)?)", synthesis, _re.I)
        confidence=float(m.group(1)) if m else 0.65
        self.last_council=list(contributions.keys())
        return synthesis, confidence, contributions

    @staticmethod
    def _single_chat(provider, messages, **kwargs):
        return provider.chat(messages, **kwargs)

    def chat(self, messages, tools=None, **kwargs):
        """Route requests intelligently.

        AUTO + think=True uses the multi-model council for substantive text.
        Tool execution stays on Ollama for reliable structured tool calls, but
        the council can be used as a lightweight planner before tool execution
        when JARVIS_COUNCIL=PLANNER.
        """
        deep = bool(kwargs.get("think", False))

        # Deep text reasoning: let the available cloud/local models collaborate.
        if not tools and self.mode == "AUTO" and deep and self.council_mode != "OFF":
            try:
                return self._council_chat(messages, **kwargs)
            except Exception as exc:
                self.last_error = str(exc)

        # Planning phase for tool tasks. In AUTO it is enabled by default so the
        # available brains coordinate before JARVIS touches Windows. PLANNER can
        # still be used explicitly; OFF disables council planning.
        if tools and self.mode == "AUTO" and deep and self.council_mode != "OFF":
            try:
                plan_prompt = list(messages[-6:])
                plan_prompt.insert(0, {"role": "system", "content": (
                    "Eres el planificador de JARVIS. Da SOLO un plan accionable de 1-4 pasos "
                    "para que otro agente ejecute la tarea con herramientas. No ejecutes nada, "
                    "no inventes resultados y no muestres razonamiento interno."
                )})
                planner = self._council_chat(plan_prompt, max_tokens=900, temperature=0.15, think=True)
                plan_text = str(getattr(getattr(planner, "message", None), "content", "") or "").strip()
                if plan_text:
                    messages = list(messages) + [{"role": "system", "content": "PLAN DEL CONSEJO (solo como guía, verifica todo con herramientas):\n" + plan_text[:3000]}]
            except Exception as exc:
                self.last_error = f"planner: {exc}"

        provider = self._select(tools=tools)
        current = getattr(provider, "name", "Unknown")
        try:
            response = provider.chat(messages, tools=tools, **kwargs)
            self.last_provider = current
            self.last_error = ""
            return response
        except Exception as exc:
            self.last_error = f"{current}: {exc}"
            if not tools and self.mode == "AUTO":
                for name in ("ChatGPT", "Claude", "Grok", "Gemini", "Ollama"):
                    if name == current:
                        continue
                    candidate = self.providers.get(name)
                    if candidate and candidate.is_available():
                        try:
                            response = candidate.chat(messages, **kwargs)
                            self.last_provider = name
                            self.last_error = ""
                            return response
                        except Exception as fallback_exc:
                            self.last_error = f"{name}: {fallback_exc}"
            raise

