"""ThreadingHTTPServer + 라우트 표 + 정적 파일(web/dist).

MIME은 mimetypes에 맡기지 않는다(Windows 레지스트리 때문에 .js가 text/plain이 될 수 있음, 계약 C6).
"""
import contextlib
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from malttara.agent.llm import client_from_env
from malttara.config import load_config
from malttara.db import connect
from malttara.server.routes import ROUTES, ApiError

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
        ".json": "application/json", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff",
        ".png": "image/png", ".jpg": "image/jpeg", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8",
        ".map": "application/json"}
NO_FRONT = ("<!doctype html><meta charset='utf-8'><title>말따라 제주</title>"
            "<p>프론트 빌드(web/dist)가 없습니다. API는 /api/health 에서 확인할 수 있습니다.</p>")
MAX_BODY = 64 * 1024


class Ctx:
    def __init__(self, db_path, map_path, static_dir, env):
        self.db_path = db_path
        self.static_dir = os.path.realpath(static_dir) if static_dir else None
        self.settings = load_config("settings")
        self.interests = load_config("interests")
        self.regions = load_config("regions")
        self.llm = client_from_env(env, self.settings)
        self.batches = {}
        self.map_data = None
        if map_path and os.path.exists(map_path):
            with open(map_path, encoding="utf-8") as f:
                self.map_data = json.load(f)

    @contextlib.contextmanager
    def db(self):
        conn = connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "malttara"

    def log_message(self, fmt, *args):  # 콘솔을 조용히(오류만 표준 에러로)
        pass

    def _send(self, status, payload, content_type=None):
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            content_type = content_type or "application/json; charset=utf-8"
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
            content_type = content_type or "text/html; charset=utf-8"
        else:
            data = payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self, method):
        ctx = self.server.ctx
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            return self._static(path) if method == "GET" else self._send(405, {"error": "허용되지 않는 요청입니다"})
        query = {k: v[-1] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "요청이 너무 큽니다"})
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw.decode("utf-8") or "null")
            except (UnicodeDecodeError, ValueError):
                return self._send(400, {"error": "요청 본문이 올바른 JSON이 아닙니다"})
        for m_, pattern, fn in ROUTES:
            mt = pattern.match(path)
            if mt and m_ == method:
                try:
                    status, payload = fn(ctx, mt, query, body)
                except ApiError as e:
                    return self._send(e.status, {"error": e.message})
                except Exception as e:
                    return self._send(500, {"error": f"서버 오류가 났습니다 ({type(e).__name__})"})
                return self._send(status, payload)
        return self._send(404, {"error": "없는 API 경로입니다"})

    def _static(self, path):
        root = self.server.ctx.static_dir
        if not root or not os.path.isdir(root):
            return self._send(200, NO_FRONT)
        rel = urllib.parse.unquote(path).lstrip("/").replace("\\", "/")
        target = os.path.realpath(os.path.join(root, rel)) if rel else os.path.join(root, "index.html")
        if os.path.commonpath([root, target]) != root:
            return self._send(404, {"error": "없는 경로입니다"})
        if not os.path.isfile(target):
            target = os.path.join(root, "index.html")
            if not os.path.isfile(target):
                return self._send(200, NO_FRONT)
        with open(target, "rb") as f:
            data = f.read()
        ext = os.path.splitext(target)[1].lower()
        return self._send(200, data, MIME.get(ext, "application/octet-stream"))

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def make_server(db_path, map_path, static_dir, host, port, env) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    srv.ctx = Ctx(db_path, map_path, static_dir, env)
    return srv
