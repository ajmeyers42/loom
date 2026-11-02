"""Local HTTP server for the Loom UI (127.0.0.1, token auth, stdlib only)."""

from __future__ import annotations

import json
import mimetypes
import re
import secrets
import socket
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .adapter import AdapterError, LoomAdapter, assert_root_allowed, default_root

STATIC_DIR = Path(__file__).resolve().parent / "static"
SLUG_SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class LoomUIServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, *, adapter: LoomAdapter, token: str, approver: str):
        super().__init__(addr, handler)
        self.adapter = adapter
        self.token = token
        self.approver = approver
        self.daemon_threads = True


class LoomUIHandler(BaseHTTPRequestHandler):
    server_version = "LoomUI/0.1"

    def log_message(self, fmt, *args):
        # Never log request bodies (keys/*); path-only access log
        if args and isinstance(args[0], str) and "/keys/" in args[0]:
            return
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    @property
    def loom(self) -> LoomUIServer:
        return self.server  # type: ignore[return-value]

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost", "")

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin or origin == "null":
            # Embedded browsers (e.g. Cursor MCP) may send Origin: null for same-host fetches.
            return True
        parsed = urlparse(origin)
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            return False
        if parsed.port is None:
            return True
        return parsed.port == self.server.server_address[1]

    def _token_ok(self) -> bool:
        qs = parse_qs(urlparse(self.path).query)
        if qs.get("t") and qs["t"][0] == self.loom.token:
            return True
        if self.headers.get("X-Loom-Token") == self.loom.token:
            return True
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("loom_token=") and part.split("=", 1)[1] == self.loom.token:
                return True
        return False

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if parse_qs(urlparse(self.path).query).get("t"):
            self.send_header("Set-Cookie", f"loom_token={self.loom.token}; Path=/; HttpOnly; SameSite=Strict")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, message: str):
        self._json(status, {"ok": False, "error": {"code": code, "message": message}})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            raise AdapterError("invalid_json", "Request body must be JSON", http=400)

    def _guard(self) -> bool:
        if not self._host_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad_host", "Forbidden")
            return False
        if not self._origin_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad_origin", "Forbidden")
            return False
        if not self._token_ok():
            self._error(HTTPStatus.UNAUTHORIZED, "unauthorized", "Missing or invalid token")
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        if ".." in path:
            self._error(HTTPStatus.BAD_REQUEST, "bad_path", "Invalid path")
            return
        try:
            if path == "/api/engagements":
                self._json(HTTPStatus.OK, self.loom.adapter.get_engagements())
                return
            if path == "/api/hygiene":
                self._json(HTTPStatus.OK, self.loom.adapter.get_hygiene())
                return
            if path == "/api/keys/siblings":
                slug = parse_qs(urlparse(self.path).query).get("slug", [""])[0]
                if not slug or not SLUG_SEGMENT.match(slug):
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_slug", "Query slug required")
                    return
                self._json(HTTPStatus.OK, self.loom.adapter.keys_siblings(slug))
                return
            if path == "/api/meta":
                self._json(HTTPStatus.OK, {
                    "ok": True,
                    "data": {"approver": self.loom.approver, "root": str(self.loom.adapter.root)},
                    "warnings": ([self.loom.adapter.cloud_sync_warning()] if self.loom.adapter.cloud_sync_warning() else []),
                    "state": None,
                })
                return
            m = re.match(r"^/api/e/([^/]+)/next$", path)
            if m:
                slug = m.group(1)
                if not SLUG_SEGMENT.match(slug):
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_slug", "Invalid slug")
                    return
                fs = parse_qs(urlparse(self.path).query).get("fs", ["1"])[0] != "0"
                self._json(HTTPStatus.OK, self.loom.adapter.get_next(slug, fs=fs))
                return
            m = re.match(r"^/api/e/([^/]+)/keys$", path)
            if m:
                slug = m.group(1)
                if not SLUG_SEGMENT.match(slug):
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_slug", "Invalid slug")
                    return
                self._json(HTTPStatus.OK, self.loom.adapter.keys_status(slug))
                return
            m = re.match(r"^/api/e/([^/]+)/keys/siblings$", path)
            if m:
                slug = m.group(1)
                self._json(HTTPStatus.OK, self.loom.adapter.keys_siblings(slug))
                return
            m = re.match(r"^/api/e/([^/]+)/listen/plan$", path)
            if m:
                self._json(HTTPStatus.OK, self.loom.adapter.listen_plan(m.group(1)))
                return
            m = re.match(r"^/api/e/([^/]+)/gaps$", path)
            if m:
                self._json(HTTPStatus.OK, self.loom.adapter.gaps_list(m.group(1)))
                return
            if path == "/" or path.startswith("/static/"):
                self._serve_static(path if path != "/" else "/index.html")
                return
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Not found")
        except AdapterError as e:
            self._error(e.http, e.code, e.message)

    def do_POST(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        if ".." in path:
            self._error(HTTPStatus.BAD_REQUEST, "bad_path", "Invalid path")
            return
        try:
            body = self._read_json()
            if path == "/api/engagements":
                self._json(HTTPStatus.OK, self.loom.adapter.create_engagement(body))
                return
            if path == "/api/validate-public":
                self._json(HTTPStatus.OK, _envelope_public(self.loom.adapter.validate_public_fields(**body)))
                return
            m = re.match(r"^/api/e/([^/]+)/keys/(set|clone|defer|validate)$", path)
            if m:
                slug, action = m.group(1), m.group(2)
                if not SLUG_SEGMENT.match(slug):
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_slug", "Invalid slug")
                    return
                self._json(HTTPStatus.OK, self.loom.adapter.keys_action(slug, action, body))
                return
            m = re.match(r"^/api/e/([^/]+)/inputs$", path)
            if m:
                self._json(HTTPStatus.OK, self.loom.adapter.inputs_add(m.group(1), body))
                return
            m = re.match(r"^/api/e/([^/]+)/listen/record$", path)
            if m:
                self._json(HTTPStatus.OK, self.loom.adapter.listen_record(m.group(1)))
                return
            m = re.match(r"^/api/e/([^/]+)/gaps/respond$", path)
            if m:
                self._json(HTTPStatus.OK, self.loom.adapter.gaps_respond(m.group(1), body))
                return
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Not found")
        except AdapterError as e:
            self._error(e.http, e.code, e.message)

    def _serve_static(self, path: str):
        rel = path.lstrip("/")
        if rel == "index.html" or rel == "":
            rel = "index.html"
        if rel == "index.html":
            file_path = STATIC_DIR / "index.html"
        elif rel.startswith("static/"):
            file_path = STATIC_DIR / rel.removeprefix("static/")
        else:
            file_path = STATIC_DIR / rel
        if not file_path.is_file() or not file_path.resolve().is_relative_to(STATIC_DIR.resolve()):
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Not found")
            return
        data = file_path.read_bytes()
        ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if parse_qs(urlparse(self.path).query).get("t"):
            self.send_header("Set-Cookie", f"loom_token={self.loom.token}; Path=/; HttpOnly; SameSite=Strict")
        self.end_headers()
        self.wfile.write(data)


def _envelope_public(data: dict) -> dict:
    return {"ok": True, "data": data, "warnings": [], "state": None}


def pick_port(preferred: int) -> int:
    if preferred:
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(root: Path | None = None, port: int = 0, *, token: str | None = None) -> tuple[LoomUIServer, str]:
    from loomstate.core import default_approver

    root = Path(root or default_root()).expanduser().resolve()
    assert_root_allowed(root)
    adapter = LoomAdapter(root)
    token = token or secrets.token_urlsafe(24)
    approver = default_approver() or "unknown"
    port = pick_port(port)
    httpd = LoomUIServer(("127.0.0.1", port), LoomUIHandler, adapter=adapter, token=token, approver=approver)
    return httpd, token


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Loom local web UI")
    p.add_argument("--root", help="LOOM_ENGAGEMENTS_ROOT (default from env or ~/engagements)")
    p.add_argument("--port", type=int, default=0, help="Port (0 = random free port)")
    args = p.parse_args(argv)
    httpd, token = serve(Path(args.root) if args.root else None, args.port)
    warn = httpd.adapter.cloud_sync_warning()
    if warn:
        print(f"⚠️  {warn}", file=sys.stderr)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/?t={token}"
    print(url)
    print(f"Approver: {httpd.approver}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
