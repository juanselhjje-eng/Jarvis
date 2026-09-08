"""J.A.R.V.I.S. package.

The package initializer intentionally stays side-effect free. Importing a submodule
such as ``src.jarvis.brain`` must never boot the runtime or import the UI; this avoids
circular imports during startup and keeps the package composable for tests/tools.
"""

__all__: list[str] = []
