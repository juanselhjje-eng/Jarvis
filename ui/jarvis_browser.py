from __future__ import annotations

import os
import re
import urllib.parse
import webbrowser
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QToolButton
)

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None
    QWebEngineProfile = None
    QWebEnginePage = None
    QWebEngineSettings = None


HOME_URL = "https://www.google.com/"
BLOXD_URL = "https://bloxd.io/"


class JarvisBrowser(QWidget):
    """Persistent Chromium/WebEngine browser embedded in the JARVIS UI.

    It is a normal browser surface, not a collection of site-specific commands.
    The JARVIS agent can therefore navigate to arbitrary authorized web sites,
    play browser audio, run JavaScript/WebGL pages, and keep a persistent web
    session without launching Chrome.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("jarvisBrowser")
        self._profile = None
        self.view = None
        self.address = None
        self.status = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        bar = QHBoxLayout()
        bar.setContentsMargins(8, 7, 8, 0)
        self.back = self._button("‹", "Atrás")
        self.forward = self._button("›", "Adelante")
        self.reload = self._button("⟳", "Recargar")
        self.home = self._button("⌂", "Inicio")
        for b in (self.back, self.forward, self.reload, self.home):
            bar.addWidget(b)

        self.address = QLineEdit()
        self.address.setPlaceholderText("Buscar o escribir una dirección...")
        self.address.setClearButtonEnabled(True)
        self.address.returnPressed.connect(self.navigate_from_bar)
        bar.addWidget(self.address, 1)

        self.stop = self._button("×", "Detener")
        bar.addWidget(self.stop)
        root.addLayout(bar)

        self.status = QLabel("NAVEGADOR JARVIS // PREPARANDO")
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        if not WEBENGINE_AVAILABLE:
            message = QLabel(
                "Qt WebEngine no está instalado.\n\n"
                "Instala las dependencias con:\n"
                "pip install -r requirements-webengine.txt"
            )
            message.setAlignment(Qt.AlignCenter)
            message.setObjectName("muted")
            root.addWidget(message, 1)
            return

        storage = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JARVIS" / "browser"
        storage.mkdir(parents=True, exist_ok=True)
        cache = storage / "cache"

        self._profile = QWebEngineProfile("JARVIS", self)
        self._profile.setPersistentStoragePath(str(storage))
        self._profile.setCachePath(str(cache))
        self._profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self.view = QWebEngineView(self)
        self.view.setPage(QWebEnginePage(self._profile, self.view))
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)

        self.view.urlChanged.connect(self._url_changed)
        self.view.titleChanged.connect(self._title_changed)
        self.view.loadStarted.connect(lambda: self.status.setText("NAVEGADOR JARVIS // CARGANDO"))
        self.view.loadProgress.connect(lambda n: self.status.setText(f"NAVEGADOR JARVIS // {n}%"))
        self.view.loadFinished.connect(self._loaded)
        self.view.page().fullScreenRequested.connect(self._fullscreen)
        self.view.page().windowCloseRequested.connect(self._window_close_requested)
        self.view.page().geometryChangeRequested.connect(self._geometry_change_requested)
        self._profile.downloadRequested.connect(self._download_requested)

        self.back.clicked.connect(self.view.back)
        self.forward.clicked.connect(self.view.forward)
        self.reload.clicked.connect(self.view.reload)
        self.home.clicked.connect(lambda: self.open_url(HOME_URL))
        self.stop.clicked.connect(self.view.stop)
        root.addWidget(self.view, 1)

        self.open_url(HOME_URL)

    def _button(self, text, tip):
        b = QToolButton(self)
        b.setText(text)
        b.setToolTip(tip)
        b.setFixedWidth(34)
        return b

    @property
    def available(self):
        return self.view is not None

    def _normalize(self, text: str) -> str:
        text = text.strip()
        if not text:
            return HOME_URL
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
            return text
        if re.match(r"^[\w.-]+\.[A-Za-z]{2,}([/:].*)?$", text):
            return "https://" + text
        return "https://www.google.com/search?q=" + urllib.parse.quote_plus(text)

    def navigate_from_bar(self):
        self.open_url(self._normalize(self.address.text()))

    def open_url(self, url: str):
        if not self.view:
            self.status.setText("NAVEGADOR NO DISPONIBLE: instala Qt WebEngine")
            return False
        self.view.setUrl(QUrl(self._normalize(url)))
        return True

    def search(self, query: str):
        return self.open_url("https://www.google.com/search?q=" + urllib.parse.quote_plus(query))

    def open_bloxd(self):
        return self.open_url(BLOXD_URL)

    def run_javascript(self, script: str, callback=None):
        if not self.view:
            return False
        self.view.page().runJavaScript(script, callback)
        return True

    def page_text(self, callback=None):
        return self.run_javascript(
            "document.body ? document.body.innerText : ''",
            callback,
        )

    def click_text(self, text: str):
        safe = text.replace("\\", "\\\\").replace("'", "\\'")
        script = f"""
        (() => {{
          const target = '{safe}'.trim().toLowerCase();
          const els = [...document.querySelectorAll('button,a,[role=button],input,textarea,[tabindex]')];
          const el = els.find(e => ((e.innerText || e.value || e.getAttribute('aria-label') || e.title || '')
            .trim().toLowerCase() === target));
          if (!el) return false;
          el.scrollIntoView({{block:'center', inline:'center'}});
          el.click();
          return true;
        }})()
        """
        result = {"value": False}
        self.run_javascript(script, lambda v: result.__setitem__("value", bool(v)))
        return result

    def _url_changed(self, url):
        self.address.setText(url.toString())

    def _title_changed(self, title):
        self.status.setText("NAVEGADOR JARVIS // " + (title[:80] or "SIN TÍTULO"))

    def _loaded(self, ok):
        self.status.setText("NAVEGADOR JARVIS // LISTO" if ok else "NAVEGADOR JARVIS // ERROR DE CARGA")
        self.address.setText(self.view.url().toString())

    def _fullscreen(self, request):
        request.accept()
        if request.toggleOn():
            self.view.showFullScreen()
        else:
            self.view.showNormal()

    def _window_close_requested(self):
        if self.view:
            self.view.stop()

    def _geometry_change_requested(self, request):
        request.accept()
        rect = request.requestedGeometry()
        self.view.setGeometry(rect)

    def _download_requested(self, item):
        # Keep downloads inside the JARVIS workspace rather than silently
        # opening an external application.
        dest = Path.home() / "Downloads"
        dest.mkdir(parents=True, exist_ok=True)
        name = item.downloadFileName() or "download"
        item.setDownloadDirectory(str(dest))
        item.setDownloadFileName(name)
        item.accept()
        self.status.setText(f"DESCARGA: {name}")
