"""
Shared Playwright Manager - single Playwright instance for all watchers
"""
import threading
import logging

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightManager:
    _instance = None
    _lock = threading.Lock()
    _playwright = None
    _refcount = 0

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def start(self):
        with self._lock:
            if not PLAYWRIGHT_AVAILABLE:
                raise ImportError("Playwright not installed")
            if self._playwright is None:
                self._playwright = sync_playwright().start()
                logger.info("Playwright manager started")
            self._refcount += 1
        return self._playwright

    def stop(self):
        with self._lock:
            self._refcount -= 1
            if self._refcount <= 0 and self._playwright:
                self._playwright.stop()
                self._playwright = None
                logger.info("Playwright manager stopped")

    def create_browser(self, headless=True, **kwargs):
        pw = self.start()
        return pw.chromium.launch(headless=headless, **kwargs)

    def create_context(self, session_path=None, headless=True, **kwargs):
        pw = self.start()
        if session_path:
            return pw.chromium.launch_persistent_context(
                str(session_path), headless=headless, **kwargs
            )
        return pw.chromium.launch(headless=headless, **kwargs)


manager = PlaywrightManager()
