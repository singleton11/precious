from __future__ import annotations

import argparse
import hmac
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass
class AppState:
    repositories: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


DEFAULT_AGENTS = [
    {"id": "acp-coder", "name": "ACP Coder"},
    {"id": "acp-reviewer", "name": "ACP Reviewer"},
]


def now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def make_handler(state: AppState, server_password: str):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8")) if raw else {}

        def _require_password(self) -> bool:
            if not self.path.startswith("/api/"):
                return True
            provided = self.headers.get("X-Server-Password", "")
            if hmac.compare_digest(provided, server_password):
                return True
            self._send_json({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
            return False

        def _serve_client(self, path: str) -> bool:
            root = Path(__file__).resolve().parent.parent / "client"
            if path in {"/", "/index.html"}:
                file_path = root / "index.html"
                content_type = "text/html; charset=utf-8"
            elif path == "/app.js":
                file_path = root / "app.js"
                content_type = "application/javascript; charset=utf-8"
            else:
                return False

            if not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return True

            data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return True

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if self._serve_client(path):
                return

            if not self._require_password():
                return

            if path == "/health":
                self._send_json({"status": "ok"})
            elif path == "/api/repositories":
                with state.lock:
                    self._send_json(state.repositories)
            elif path == "/api/agents":
                self._send_json(DEFAULT_AGENTS)
            elif path == "/api/sessions":
                with state.lock:
                    self._send_json(state.sessions)
            elif path.startswith("/api/sessions/") and path.endswith("/tool-calls"):
                session_id = path.split("/")[3]
                with state.lock:
                    self._send_json(state.tool_calls.get(session_id, []))
            else:
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            if not self._require_password():
                return
            parsed = urlparse(self.path)
            path = parsed.path
            data = self._read_json()

            if path == "/api/repositories":
                repo_url = data.get("url", "").strip()
                if not repo_url:
                    self._send_json({"error": "Repository URL is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                item = {"id": str(uuid.uuid4()), "url": repo_url, "created_at": now_iso()}
                with state.lock:
                    state.repositories.append(item)
                self._send_json(item, status=HTTPStatus.CREATED)
                return

            if path == "/api/sessions":
                agent_id = data.get("agent_id", "").strip()
                if not agent_id:
                    self._send_json({"error": "agent_id is required"}, status=HTTPStatus.BAD_REQUEST)
                    return

                session = {
                    "id": str(uuid.uuid4()),
                    "repository_id": data.get("repository_id"),
                    "agent_id": agent_id,
                    "model": data.get("model", "gpt-5-mini"),
                    "thinking_effort": data.get("thinking_effort", "medium"),
                    "mode": data.get("mode", "plan"),
                    "allowed_tools": data.get("allowed_tools", []),
                    "status": "running",
                    "created_at": now_iso(),
                }
                with state.lock:
                    state.sessions.append(session)
                    state.tool_calls[session["id"]] = []
                self._send_json(session, status=HTTPStatus.CREATED)
                return

            if path.startswith("/api/sessions/") and path.endswith("/tool-calls"):
                session_id = path.split("/")[3]
                tool_call = {
                    "id": str(uuid.uuid4()),
                    "name": data.get("name", "unknown"),
                    "arguments": data.get("arguments", {}),
                    "status": data.get("status", "completed"),
                    "created_at": now_iso(),
                }
                with state.lock:
                    if session_id not in state.tool_calls:
                        self._send_json({"error": "Session not found"}, status=HTTPStatus.NOT_FOUND)
                        return
                    state.tool_calls[session_id].append(tool_call)
                self._send_json(tool_call, status=HTTPStatus.CREATED)
                return

            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_PATCH(self) -> None:  # noqa: N802
            if not self._require_password():
                return
            parsed = urlparse(self.path)
            path = parsed.path
            if not path.startswith("/api/sessions/"):
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return

            session_id = path.split("/")[3]
            updates = self._read_json()
            allowed_fields = {"model", "thinking_effort", "mode", "allowed_tools"}

            with state.lock:
                for session in state.sessions:
                    if session["id"] == session_id:
                        for key in allowed_fields:
                            if key in updates:
                                session[key] = updates[key]
                        session["updated_at"] = now_iso()
                        self._send_json(session)
                        return

            self._send_json({"error": "Session not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def make_server(host: str, port: int, password: str) -> ThreadingHTTPServer:
    state = AppState()
    handler = make_handler(state, password)
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run precious agent management server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    password = os.environ.get("PRECIOUS_SERVER_PASSWORD", "changeme")
    server = make_server(args.host, args.port, password)
    print(f"Server listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
