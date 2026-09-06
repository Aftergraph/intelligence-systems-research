from __future__ import annotations

from pathlib import Path
import socket
import subprocess
from time import sleep
from typing import Callable

from .runtime_bridge import resolve_fixture_url


class BrowserRuntimeError(RuntimeError):
    """Raised when a controlled browser runtime cannot be constructed or used exactly."""


def build_obscura_runtime_argv(
    executable: str | Path,
    port: int,
) -> list[str]:
    """Build the pinned Obscura server command for local-fixture benchmarking only."""
    port_number = int(port)
    if not 1 <= port_number <= 65535:
        raise ValueError("port must be between 1 and 65535")
    return [
        str(executable).replace("\\", "/"),
        "serve",
        "--port",
        str(port_number),
        "--host",
        "127.0.0.1",
        "--allow-private-network",
    ]


def _default_playwright_start():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserRuntimeError(
            "Playwright is required on the controlled host for browser treatments"
        ) from exc
    return sync_playwright().start()


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class PlaywrightPageBackend:
    """Stable benchmark operation surface around one fresh Playwright page."""

    def __init__(
        self,
        page,
        *,
        fixture_base_url: str,
        close_callback: Callable[[], None],
        evidence_root: str | Path | None = None,
    ):
        self.page = page
        self.fixture_base_url = str(fixture_base_url).rstrip("/")
        # Validate the origin at construction time, before any navigation occurs.
        resolve_fixture_url(self.fixture_base_url, self.fixture_base_url)
        self.close_callback = close_callback
        self.evidence_root = Path(evidence_root).resolve() if evidence_root else None
        self._closed = False

    def _screenshot_path(self, value: str) -> Path:
        if self.evidence_root is None:
            raise BrowserRuntimeError("screenshot requires a controlled evidence root")
        raw = Path(value)
        target = raw.resolve() if raw.is_absolute() else (self.evidence_root / raw).resolve()
        try:
            target.relative_to(self.evidence_root)
        except ValueError as exc:
            raise BrowserRuntimeError("screenshot path escapes controlled evidence root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def perform(self, operation: str, payload: dict | None = None) -> dict:
        if self._closed and operation != "close":
            raise BrowserRuntimeError("browser backend is closed")
        data = dict(payload or {})

        if operation == "start":
            return {"state": "started", "url": str(getattr(self.page, "url", ""))}

        if operation == "navigate":
            raw_url = data.get("url")
            if not isinstance(raw_url, str) or not raw_url:
                raise BrowserRuntimeError("navigate requires a non-empty url")
            try:
                url = resolve_fixture_url(raw_url, self.fixture_base_url)
            except Exception as exc:
                raise BrowserRuntimeError(str(exc)) from exc
            response = self.page.goto(url, wait_until="domcontentloaded")
            status = getattr(response, "status", None) if response is not None else None
            if callable(status):
                status = status()
            return {
                "url": str(getattr(self.page, "url", url)),
                "status": int(status) if status is not None else None,
            }

        if operation == "query":
            selector = data.get("selector")
            if not isinstance(selector, str) or not selector:
                raise BrowserRuntimeError("query requires a non-empty selector")
            locator = self.page.locator(selector)
            count = int(locator.count())
            text = locator.first.text_content() if count else None
            return {"selector": selector, "count": count, "text": text}

        if operation == "evaluate":
            script = data.get("script")
            if not isinstance(script, str) or not script:
                raise BrowserRuntimeError("evaluate requires a non-empty script")
            result = self.page.evaluate(script)
            return result if isinstance(result, dict) else {"value": result}

        if operation == "screenshot":
            path = data.get("path")
            if not isinstance(path, str) or not path:
                raise BrowserRuntimeError("screenshot requires a path")
            target = self._screenshot_path(path)
            self.page.screenshot(path=str(target))
            return {"path": str(target)}

        if operation == "close":
            if not self._closed:
                self._closed = True
                self.close_callback()
            return {"state": "closed"}

        raise BrowserRuntimeError(f"unsupported browser operation: {operation}")


class ChromiumBackendFactory:
    """Create a fresh headless Chromium process/page for every measured run."""

    def __init__(
        self,
        *,
        fixture_base_url: str,
        playwright_start: Callable[[], object] | None = None,
        executable_path: str | Path | None = None,
        evidence_root: str | Path | None = None,
    ):
        self.fixture_base_url = str(fixture_base_url)
        self.playwright_start = playwright_start or _default_playwright_start
        self.executable_path = str(executable_path) if executable_path else None
        self.evidence_root = evidence_root

    def __call__(self) -> PlaywrightPageBackend:
        playwright = self.playwright_start()
        browser = None
        context = None
        try:
            launch_kwargs: dict[str, object] = {"headless": True}
            if self.executable_path:
                launch_kwargs["executable_path"] = self.executable_path
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context()
            page = context.new_page()
        except Exception as exc:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass
            try:
                playwright.stop()
            except Exception:
                pass
            raise BrowserRuntimeError(
                f"unable to start controlled Chromium: {type(exc).__name__}: {exc}"
            ) from exc

        def close() -> None:
            for action in (context.close, browser.close, playwright.stop):
                try:
                    action()
                except Exception:
                    pass

        return PlaywrightPageBackend(
            page,
            fixture_base_url=self.fixture_base_url,
            close_callback=close,
            evidence_root=self.evidence_root,
        )


class ObscuraBackendFactory:
    """Create a fresh pinned Obscura CDP server and Playwright page per measured run."""

    def __init__(
        self,
        *,
        obscura_executable: str | Path,
        fixture_base_url: str,
        playwright_start: Callable[[], object] | None = None,
        popen_factory=subprocess.Popen,
        port_factory: Callable[[], int] | None = None,
        connect_attempts: int = 20,
        evidence_root: str | Path | None = None,
    ):
        self.obscura_executable = str(obscura_executable)
        self.fixture_base_url = str(fixture_base_url)
        self.playwright_start = playwright_start or _default_playwright_start
        self.popen_factory = popen_factory
        self.port_factory = port_factory or _free_loopback_port
        self.connect_attempts = int(connect_attempts)
        self.evidence_root = evidence_root
        if self.connect_attempts < 1:
            raise ValueError("connect_attempts must be >= 1")

    def __call__(self) -> PlaywrightPageBackend:
        port = int(self.port_factory())
        argv = build_obscura_runtime_argv(self.obscura_executable, port)
        try:
            process = self.popen_factory(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except Exception as exc:
            raise BrowserRuntimeError(
                f"unable to start Obscura server: {type(exc).__name__}: {exc}"
            ) from exc

        playwright = self.playwright_start()
        browser = None
        last_error: Exception | None = None
        endpoint = f"ws://127.0.0.1:{port}"
        for attempt in range(self.connect_attempts):
            if process.poll() is not None:
                last_error = BrowserRuntimeError(
                    f"Obscura exited before CDP connection with code {process.poll()}"
                )
                break
            try:
                browser = playwright.chromium.connect_over_cdp(endpoint, timeout=1000)
                break
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.connect_attempts:
                    sleep(0.1)

        if browser is None:
            try:
                playwright.stop()
            except Exception:
                pass
            self._reap_process(process)
            raise BrowserRuntimeError(
                f"unable to connect Playwright to Obscura CDP at {endpoint}: "
                f"{type(last_error).__name__ if last_error else 'Error'}: {last_error or ''}"
            )

        try:
            contexts = list(browser.contexts)
            context = contexts[0] if contexts else browser.new_context()
            page = context.new_page()
        except Exception as exc:
            try:
                browser.close()
            except Exception:
                pass
            try:
                playwright.stop()
            except Exception:
                pass
            self._reap_process(process)
            raise BrowserRuntimeError(
                f"unable to create Obscura CDP page: {type(exc).__name__}: {exc}"
            ) from exc

        def close() -> None:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            try:
                playwright.stop()
            except Exception:
                pass
            self._reap_process(process)

        return PlaywrightPageBackend(
            page,
            fixture_base_url=self.fixture_base_url,
            close_callback=close,
            evidence_root=self.evidence_root,
        )

    @staticmethod
    def _reap_process(process) -> None:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
