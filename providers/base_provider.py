from abc import ABC, abstractmethod
from typing import Iterator


class AIProvider(ABC):
    """
    Interfaz base para cualquier proveedor de inteligencia artificial.

    Todos los proveedores de JARVIS deberán implementar esta interfaz.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del proveedor."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Modelo utilizado por el proveedor."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
    ) -> str:
        """
        Envía una conversación al modelo y devuelve la respuesta completa.
        """
        pass

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
    ) -> Iterator[str]:
        """
        Versión por streaming.

        Los proveedores pueden sobrescribir este método si soportan
        generación progresiva de texto.
        """
        yield self.chat(messages, temperature)