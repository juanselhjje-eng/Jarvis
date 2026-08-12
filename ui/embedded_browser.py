from __future__ import annotations

"""Embedded Chromium-based web surface for JARVIS.

Keeps web pages inside the JARVIS window instead of launching Chrome/Google.
Qt WebEngine is optional so the rest of JARVIS can still start when the
package is not installed.
"""

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # optional dependency
    QWebEngineView = None


BLOXD_URL = "https://bloxd.io/"


class EmbeddedBrowser(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.view = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if QWebEngineView is None:
            return
        self.view = QWebEngineView(self)
        self.view.settings().setAttribute(self.view.settings().WebAttribute.JavascriptEnabled, True)
        self.view.settings().setAttribute(self.view.settings().WebAttribute.FullScreenSupportEnabled, True)
        self.view.settings().setAttribute(self.view.settings().WebAttribute.LocalStorageEnabled, True)
        layout.addWidget(self.view)

    @property
    def available(self) -> bool:
        return self.view is not None

    def open_url(self, url: str):
        if not self.view:
            raise RuntimeError("QtWebEngine no está instalado. Instala PySide6-WebEngine.")
        self.view.setUrl(QUrl(url))

    def open_bloxd(self):
        self.open_url(BLOXD_URL)
