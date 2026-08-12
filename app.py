from core.context_bridge import install as install_context_bridge

# Load conversational continuity before the UI creates its Orchestrator.
install_context_bridge()

# V26: redesigned command deck. The legacy UI remains available as ui.main_window,
# but the application now starts from the repaired Spanish interface.
from ui.modern_main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
