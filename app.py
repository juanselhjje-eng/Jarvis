from core.context_bridge import install as install_context_bridge

# Install conversation-state continuity before the UI creates its Orchestrator.
install_context_bridge()

from ui.main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
