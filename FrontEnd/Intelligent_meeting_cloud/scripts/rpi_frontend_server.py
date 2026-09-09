#!/usr/bin/env python3
"""Serve the built Vue frontend on Raspberry Pi and proxy sensor endpoints."""

from __future__ import annotations

import mimetypes
import os
import posixpath
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = Path(os.environ.get("FRONTEND_DIST", BASE_DIR / "dist")).resolve()
PORT = int(os.environ.get("FRONTEND_PORT", "5173"))
SENSOR_TARGET = os.environ.get("SENSOR_TARGET", "http://127.0.0.1:5000")


class FrontendHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.route_request()

    def do_HEAD(self):
        self.route_request(head_only=True)

    def do_POST(self):
        self.route_request()

    def route_request(self, head_only: bool = False):
        if self.path.startswith("/sensor-api"):
            self.proxy("/sensor-api", "/api", head_only=head_only)
            return
        if self.path.startswith("/sensor-chart"):
            self.proxy("/sensor-chart", "/chart", head_only=head_only)
            return
        self.serve_static(head_only=head_only)

    def proxy(self, prefix: str, rewrite: str, head_only: bool = False):
        target_path = self.path.replace(prefix, rewrite, 1)
        target_url = urllib.parse.urljoin(SENSOR_TARGET, target_path)
        body = None
        if self.command not in {"GET", "HEAD"}:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else None

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "connection", "content-length"}
        }

        request = urllib.request.Request(target_url, data=body, method=self.command, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = b"" if head_only else response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in {"connection", "transfer-encoding"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if not head_only:
                    self.wfile.write(payload)
        except urllib.error.HTTPError as error:
            payload = b"" if head_only else error.read()
            self.send_response(error.code)
            self.send_header("Content-Type", error.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if not head_only:
                self.wfile.write(payload)
        except Exception as error:
            payload = f'{{"error":"sensor proxy failed: {error}"}}'.encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if not head_only:
                self.wfile.write(payload)

    def serve_static(self, head_only: bool = False):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = posixpath.normpath(urllib.parse.unquote(parsed.path)).lstrip("/")
        if clean_path in {"", "."}:
            clean_path = "index.html"

        file_path = (DIST_DIR / clean_path).resolve()
        if not str(file_path).startswith(str(DIST_DIR)) or not file_path.exists() or file_path.is_dir():
            file_path = DIST_DIR / "index.html"

        payload = b"" if head_only else file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            content_type = "text/javascript"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size if head_only else len(payload)))
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    if not DIST_DIR.exists():
        raise SystemExit(f"dist directory not found: {DIST_DIR}")

    server = ThreadingHTTPServer(("0.0.0.0", PORT), FrontendHandler)
    print(f"Frontend server: http://0.0.0.0:{PORT}")
    print(f"Sensor target: {SENSOR_TARGET}")
    server.serve_forever()
