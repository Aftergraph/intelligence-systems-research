from __future__ import annotations

from .browser_base import DelegatingBrowserAdapter


class ChromiumAdapter(DelegatingBrowserAdapter):
    """Control browser adapter. Host code supplies the Chromium backend."""
