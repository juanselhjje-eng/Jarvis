from core.context_bridge import install as install_context_bridge
from tools.computer_bridge import install as install_computer_controls
from core.computer_mode import install as install_computer_mode
from plugins.registry import register_builtin_capabilities

# Initialize deterministic infrastructure before the UI creates its Orchestrator.
install_context_bridge()
install_computer_controls()
install_computer_mode()
register_builtin_capabilities()

# Extended AI gateway: keeps multimodal capabilities and the multi-model council,
# while using an adaptive fast path for ordinary conversation.
try:
    import core.orchestrator as _orchestrator
    from core.latency_manager import LatencyAIGatewayManager
    _orchestrator.MultiAIManager = LatencyAIGatewayManager
except Exception:
    # Optional SDKs must never prevent local/offline JARVIS from starting.
    pass

from ui.modern_main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
