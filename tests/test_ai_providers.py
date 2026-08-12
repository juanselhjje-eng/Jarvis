from dotenv import load_dotenv
load_dotenv()

from providers.ollama_provider import OllamaProvider
from providers.cloud_providers import MultiAIManager

manager = MultiAIManager(OllamaProvider())
print("Estados:", manager.statuses())
print("Disponibles:", manager.available())
print("Modo:", manager.mode)
