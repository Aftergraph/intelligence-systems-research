from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import sleep
from urllib.parse import parse_qs, urlparse


class FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        return

    def _send(self, status: int, body: str, *, content_type: str = "text/html", headers: dict | None = None):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/static":
            self._send(200, "<html><body><div id='deterministic-marker'>alpha</div></body></html>")
            return
        if parsed.path == "/dynamic":
            self._send(200, "<html><body><div id='dynamic'>before</div><script>document.getElementById('dynamic').textContent='after';</script></body></html>")
            return
        if parsed.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/static")
            self.end_headers()
            return
        if parsed.path == "/form":
            query = parse_qs(parsed.query)
            value = query.get("value", [""])[0]
            self._send(200, f"<html><body><div id='form-value'>{value}</div></body></html>")
            return
        if parsed.path == "/cookie":
            received = self.headers.get("Cookie", "")
            self._send(200, f"<html><body><div id='cookie'>{received}</div></body></html>", headers={"Set-Cookie": "jar_exp_0013=1; Path=/"})
            return
        if parsed.path == "/slow":
            query = parse_qs(parsed.query)
            delay_ms = min(max(int(query.get("ms", ["25"])[0]), 0), 250)
            sleep(delay_ms / 1000)
            self._send(200, "<html><body>slow-ok</body></html>")
            return
        if parsed.path == "/error":
            self._send(500, "<html><body>deterministic-error</body></html>")
            return
        self._send(404, "not-found", content_type="text/plain")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/form":
            self._send(404, "not-found", content_type="text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        value = parse_qs(body).get("value", [""])[0]
        self._send(200, f"<html><body><div id='form-value'>{value}</div></body></html>")


@contextmanager
def fixture_server():
    """Run the deterministic local browser fixture server on an ephemeral port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
