from __future__ import annotations

"""Extended AI manager used by the JARVIS orchestrator.

The existing MultiAIManager remains responsible for text/tool routing and the
multi-model council. This subclass adds a single capability surface for vision,
image generation and provider capability inspection without changing the public
chat API used by the rest of JARVIS.
"""

from providers.cloud_providers import MultiAIManager
from providers.capability_gateway import CapabilityGateway


class AIGatewayManager(MultiAIManager):
    def __init__(self, ollama_provider):
        super().__init__(ollama_provider)
        self.capability_gateway = CapabilityGateway(self.providers)

    def capability_status(self):
        """Return capability availability without exposing API keys."""
        return self.capability_gateway.capabilities()

    def inspect_image(self, image_path: str, instruction: str = "Describe lo importante de esta imagen de forma útil para JARVIS.", preferred: str = "AUTO"):
        return self.capability_gateway.vision(image_path, instruction, preferred)

    def create_image(self, prompt: str, output_path: str, preferred: str = "AUTO"):
        return self.capability_gateway.generate_image(prompt, output_path, preferred)
