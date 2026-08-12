from core.context_bridge import install as install_context_bridge
from tools.computer_bridge import install as install_computer_controls
from core.computer_mode import install as install_computer_mode
from plugins.registry import register_builtin_capabilities

# Initialize deterministic infrastructure before the UI creates its Orchestrator.
install_context_bridge()
install_computer_controls()
install_computer_mode()
register_builtin_capabilities()

# Extended AI gateway: keeps the existing text/tool council and adds multimodal
# capabilities (vision/image generation) behind the same API-key configuration.
try:
    import core.orchestrator as _orchestrator
    from providers.ai_gateway_manager import AIGatewayManager
    _orchestrator.MultiAIManager = AIGatewayManager
except Exception:
    # Optional SDKs must never prevent local/offline JARVIS from starting.
    pass

from ui.modern_main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
