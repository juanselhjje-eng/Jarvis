"""Legacy entry point kept for compatibility.

The maintained interface lives in ui.modern_main_window. Keeping this shim small
prevents the retired UI from drifting or containing independent bugs.
"""

from ui.modern_main_window import ModernWindow, run_app

__all__ = ["ModernWindow", "run_app"]
