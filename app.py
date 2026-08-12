from core.context_bridge import install as install_context_bridge
from tools.computer_bridge import install as install_computer_controls

# Initialize deterministic infrastructure before the UI creates its Orchestrator.
install_context_bridge()
install_computer_controls()

# V27: Spanish command deck + conversational continuity + human-like desktop controls.
from ui.modern_main_window import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
