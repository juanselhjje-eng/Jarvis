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

from ui.modern_main_window import ModernWindow, run_app


# ---------------------------------------------------------------------------
# First-class browser workspace
# ---------------------------------------------------------------------------
# The browser lives inside JARVIS. It is not Chrome launched from a command:
# it is another workspace the agent can use for web research, WebGL games,
# browser audio and normal site interaction.
try:
    from ui.jarvis_browser import JarvisBrowser
    from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

    _original_window_init = ModernWindow.__init__

    def _jarvis_window_init(self):
        _original_window_init(self)
        self.browser = JarvisBrowser(self)
        self.pages.addWidget(self.browser)

        # Add a real NAVIGATOR item before the diagnostics/stretch area.
        # Existing page indices and navigation keys stay aligned because the
        # browser page is appended after the existing pages.
        browser_btn = self.nav.get("browser")
        if browser_btn is None:
            browser_btn = __import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton("◉  NAVEGADOR")
            browser_btn.setObjectName("nav")
            browser_btn.setCheckable(True)
            browser_btn.clicked.connect(lambda checked: self.show_page("browser"))
            self.nav["browser"] = browser_btn
            side_layout = next(iter(self.nav.values())).parentWidget().layout()
            side_layout.insertWidget(len(self.nav) - 1, browser_btn)

        # Make the browser available to other runtime components without
        # requiring an external browser process.
        try:
            self.router.browser = self.browser
        except Exception:
            pass

    ModernWindow.__init__ = _jarvis_window_init

    _original_show_page = ModernWindow.show_page

    def _show_page(self, key):
        if key == "browser":
            keys = list(self.nav.keys())
            if key in keys:
                self.pages.setCurrentIndex(keys.index(key))
                for k, b in self.nav.items():
                    b.setChecked(k == key)
                return
        return _original_show_page(self, key)

    ModernWindow.show_page = _show_page
except Exception:
    # Browser remains optional: the normal JARVIS UI must still boot if
    # QtWebEngine is unavailable.
    pass


if __name__ == "__main__":
    raise SystemExit(run_app())
