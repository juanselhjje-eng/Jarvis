"""Legacy GUI entry point kept as a compatibility shim.

The rebuilt project is intentionally started through main.py so the core
runtime is independent from the previous GUI/orchestrator stack.
"""

from main import main


if __name__ == "__main__":
    raise SystemExit(main())
