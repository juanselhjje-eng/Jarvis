from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Capability:
    name: str
    description: str
    category: str
    enabled: bool = True
    handler: Callable[..., Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Central registry for JARVIS capabilities.

    A capability can be a local tool, an API-backed integration, an MCP adapter,
    or a higher-level agent. Registration is deliberately lightweight so optional
    integrations never prevent JARVIS from starting.
    """

    def __init__(self) -> None:
        self._items: dict[str, Capability] = {}

    def register(self, capability: Capability) -> Capability:
        self._items[capability.name] = capability
        return capability

    def enable(self, name: str, enabled: bool = True) -> bool:
        item = self._items.get(name)
        if not item:
            return False
        item.enabled = enabled
        return True

    def get(self, name: str) -> Capability | None:
        return self._items.get(name)

    def available(self, category: str | None = None) -> list[Capability]:
        return [
            item for item in self._items.values()
            if item.enabled and (category is None or item.category == category)
        ]

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "enabled": item.enabled,
                "metadata": item.metadata,
            }
            for item in self._items.values()
        ]

    def prompt_summary(self) -> str:
        rows = [
            f"- {item.name}: {item.description}"
            for item in self.available()
        ]
        return "CAPACIDADES DISPONIBLES:\n" + "\n".join(rows)


capability_registry = CapabilityRegistry()


def register_builtin_capabilities() -> CapabilityRegistry:
    """Register the capabilities JARVIS can expose when their dependencies exist."""
    specs = [
        ("computer_control", "Controlar teclado, ratón, ventanas y acciones del escritorio.", "computer"),
        ("screen_vision", "Capturar pantalla y analizar contenido visual/OCR.", "vision"),
        ("web_research", "Consultar información web cuando se necesite conocimiento actual.", "research"),
        ("browser_automation", "Abrir y controlar el navegador mediante herramientas del escritorio.", "computer"),
        ("file_workspace", "Leer, crear y organizar archivos y documentos del workspace.", "files"),
        ("document_generation", "Crear documentos, hojas de cálculo, presentaciones y PDF.", "documents"),
        ("image_generation", "Generar imágenes mediante proveedores compatibles y configurados.", "creative"),
        ("multimodal_ai", "Enviar texto e imágenes a los proveedores de IA compatibles.", "ai"),
        ("multi_ai_council", "Comparar propuestas de varios modelos y sintetizar una respuesta.", "ai"),
        ("persistent_memory", "Guardar y recuperar contexto, preferencias, conocimiento y experiencias.", "memory"),
        ("learning_loop", "Convertir resultados verificados y correcciones en conocimiento reutilizable.", "learning"),
        ("voice_input", "Entrada de voz cuando el motor STT está configurado.", "voice"),
        ("voice_output", "Respuesta hablada mediante TTS neural o local.", "voice"),
        ("camera_vision", "Analizar imágenes de cámara cuando está disponible.", "vision"),
        ("scheduler", "Ejecutar rutinas programadas y tareas periódicas.", "automation"),
        ("self_recovery", "Detectar fallos, intentar recuperación y registrar el resultado.", "reliability"),
        ("mcp_integrations", "Punto de extensión para servidores MCP autorizados por el usuario.", "integrations"),
        ("api_integrations", "Punto de extensión para APIs autorizadas y configuradas en .env.", "integrations"),
    ]
    for name, description, category in specs:
        capability_registry.register(Capability(name, description, category))
    return capability_registry


register_builtin_capabilities()
