"""OnshapeSession — transport layer over an authenticated browser session.

Uses a persistent Playwright context so the login survives between runs
(stored in `user_data_dir`). Reads the JS-readable `XSRF-TOKEN` cookie and
sends it as the `X-XSRF-TOKEN` header on writes; without it, writes return 401.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from .constants import API_VERSION, DEFAULT_BASE_URL


class OnshapeError(RuntimeError):
    """An Onshape API call returned a non-2xx status (or auth is missing)."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Onshape API error {status}: {body[:400]}")


class OnshapeSession:
    """Authenticated transport. Use as a context manager.

    with OnshapeSession() as session:
        data = session.get("/documents/d/<did>/w/<wid>/elements")
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        user_data_dir: str = ".browser-data",
        headless: bool = False,
        login_timeout_s: int = 180,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.login_timeout_s = login_timeout_s
        self._pw = None
        self._context = None
        self._page = None

    # ── lifecycle ────────────────────────────────────────────────────────
    def start(self) -> OnshapeSession:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(Path(self.user_data_dir).resolve()),
            headless=self.headless,
            viewport={"width": 1600, "height": 1000},
        )
        self._page = self._context.new_page()
        self._ensure_logged_in()
        return self

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._pw is not None:
            self._pw.stop()
            self._pw = None

    def __enter__(self) -> OnshapeSession:
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.close()

    # ── auth ─────────────────────────────────────────────────────────────
    def _ensure_logged_in(self) -> None:
        page = self._page
        page.goto(f"{self.base_url}/documents", wait_until="load")
        if not self._is_login_page(page.url):
            return
        print("*** Log in to Onshape in the browser window (type your password there). ***")
        waited = 0
        while waited < self.login_timeout_s:
            page.wait_for_timeout(3000)
            waited += 3
            if not self._is_login_page(page.url):
                print("Login detected — continuing.")
                return
        raise OnshapeError(0, "Login was not completed within the timeout.")

    @staticmethod
    def _is_login_page(url: str) -> bool:
        low = url.lower()
        return "signin" in low or "login" in low

    def _xsrf_token(self) -> str:
        for cookie in self._context.cookies():
            if cookie.get("name") == "XSRF-TOKEN":
                return unquote(cookie.get("value", ""))
        raise OnshapeError(0, "XSRF-TOKEN cookie not found — session is not logged in.")

    # ── requests ─────────────────────────────────────────────────────────
    def request(self, method: str, path: str, body: dict | None = None) -> Any:
        """Call `/api/<version><path>`; returns parsed JSON (or None/str).

        Raises OnshapeError on non-2xx. `path` must start with '/' and already
        contain the /d/{did}/w/{wid}/... fragment.
        """
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body)
        if method.upper() != "GET":
            headers["X-XSRF-TOKEN"] = self._xsrf_token()

        url = f"{self.base_url}/api/{API_VERSION}{path}"
        response = self._context.request.fetch(url, method=method, headers=headers, data=data)
        if not response.ok:
            raise OnshapeError(response.status, response.text())

        text = response.text()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, body: dict) -> Any:
        return self.request("POST", path, body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    # ── observation ──────────────────────────────────────────────────────
    def screenshot(self, path: str, document_url: str | None = None) -> str:
        """Capture the current view (or `document_url` if given) to `path`."""
        if document_url:
            self._page.goto(document_url, wait_until="load")
        self._page.wait_for_timeout(1500)
        self._page.screenshot(path=path)
        return path
