from core.context_bridge import install as install_context_bridge
from tools.computer_bridge import install as install_computer_controls
from core.computer_mode import install as install_computer_mode
from plugins.registry import register_builtin_capabilities

install_context_bridge()
install_computer_controls()
install_computer_mode()
register_builtin_capabilities()

# Fast command router: common greetings, websites and app launches never wait
# for an LLM or the multi-model council.
try:
    from core.orchestrator import Orchestrator as _Orchestrator
    from core.fast_router import fast_route as _fast_route
    _original_handle = _Orchestrator.handle

    def _responsive_handle(self, text, deep=None):
        fast = _fast_route(text)
        if fast is not None:
            self._last_user_activity = __import__("time").time()
            try:
                self._schedule_reflection(str(text), str(fast))
            except Exception:
                pass
            return fast
        return _original_handle(self, text, deep=deep)

    _Orchestrator.handle = _responsive_handle
except Exception:
    pass

# Extended AI gateway: multimodal capabilities remain behind the existing API
# configuration and optional SDKs never block local startup.
try:
    import core.orchestrator as _orchestrator
    from providers.ai_gateway_manager import AIGatewayManager
    _orchestrator.MultiAIManager = AIGatewayManager
except Exception:
    pass

from ui.modern_main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
