from __future__ import annotations

import http.client
import json
import threading
import unittest

from server.app import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.password = "test-pass"
        cls.server = make_server("127.0.0.1", 0, cls.password)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method: str, path: str, payload: dict | None = None, password: str | None = None, raw_body: bytes | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"X-Server-Password": password or self.password}
        body = None
        if raw_body is not None:
            body = raw_body
            headers["Content-Type"] = "application/json"
        elif payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"

        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read().decode("utf-8")
        data = json.loads(raw) if raw else None
        connection.close()
        return response.status, data

    # --- Auth ---

    def test_requires_password(self) -> None:
        status, data = self.request("GET", "/api/repositories", password="wrong")
        self.assertEqual(status, 401)
        self.assertEqual(data["error"], "Unauthorized")

    def test_health_does_not_require_password(self) -> None:
        status, data = self.request("GET", "/health", password="wrong")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    # --- Validation ---

    def test_post_repository_requires_url(self) -> None:
        status, data = self.request("POST", "/api/repositories", {})
        self.assertEqual(status, 400)
        self.assertIn("URL", data["error"])

    def test_post_session_requires_agent_id(self) -> None:
        status, data = self.request("POST", "/api/sessions", {"model": "gpt-5-mini"})
        self.assertEqual(status, 400)
        self.assertIn("agent_id", data["error"])

    def test_post_session_rejects_invalid_thinking_effort(self) -> None:
        status, data = self.request("POST", "/api/sessions", {"agent_id": "acp-coder", "thinking_effort": "extreme"})
        self.assertEqual(status, 400)
        self.assertIn("thinking_effort", data["error"])

    def test_post_session_rejects_invalid_mode(self) -> None:
        status, data = self.request("POST", "/api/sessions", {"agent_id": "acp-coder", "mode": "yolo"})
        self.assertEqual(status, 400)
        self.assertIn("mode", data["error"])

    def test_patch_session_rejects_invalid_thinking_effort(self) -> None:
        _, session = self.request("POST", "/api/sessions", {"agent_id": "acp-coder"})
        status, data = self.request("PATCH", f"/api/sessions/{session['id']}", {"thinking_effort": "ultra"})
        self.assertEqual(status, 400)
        self.assertIn("thinking_effort", data["error"])

    def test_patch_nonexistent_session(self) -> None:
        status, data = self.request("PATCH", "/api/sessions/nonexistent-id", {"model": "x"})
        self.assertEqual(status, 404)

    def test_malformed_json_returns_400(self) -> None:
        status, data = self.request("POST", "/api/repositories", raw_body=b"not json{{{")
        self.assertEqual(status, 400)
        self.assertIn("Invalid JSON", data["error"])

    def test_tool_call_on_nonexistent_session(self) -> None:
        status, data = self.request("POST", "/api/sessions/fake-id/tool-calls", {"name": "bash"})
        self.assertEqual(status, 404)

    # --- Full flow ---

    def test_repository_and_session_flow(self) -> None:
        status, repository = self.request("POST", "/api/repositories", {"url": "https://github.com/singleton11/precious"})
        self.assertEqual(status, 201)

        status, sessions = self.request(
            "POST",
            "/api/sessions",
            {
                "repository_id": repository["id"],
                "agent_id": "acp-coder",
                "model": "gpt-5-mini",
                "thinking_effort": "high",
                "mode": "build",
            },
        )
        self.assertEqual(status, 201)

        status, updated = self.request(
            "PATCH",
            f"/api/sessions/{sessions['id']}",
            {"model": "gpt-5.4", "thinking_effort": "low", "allowed_tools": ["bash", "view"]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["model"], "gpt-5.4")
        self.assertEqual(updated["thinking_effort"], "low")
        self.assertEqual(updated["allowed_tools"], ["bash", "view"])

        status, log = self.request(
            "POST",
            f"/api/sessions/{sessions['id']}/tool-calls",
            {"name": "bash", "status": "completed", "arguments": {"command": "echo hi"}},
        )
        self.assertEqual(status, 201)
        self.assertEqual(log["name"], "bash")

        status, logs = self.request("GET", f"/api/sessions/{sessions['id']}/tool-calls")
        self.assertEqual(status, 200)
        self.assertEqual(len(logs), 1)

    def test_agents_endpoint(self) -> None:
        status, agents = self.request("GET", "/api/agents")
        self.assertEqual(status, 200)
        self.assertTrue(len(agents) >= 2)
        ids = {a["id"] for a in agents}
        self.assertIn("acp-coder", ids)
        self.assertIn("acp-reviewer", ids)

    def test_not_found_routes(self) -> None:
        status, _ = self.request("GET", "/api/nonexistent")
        self.assertEqual(status, 404)

        status, _ = self.request("POST", "/api/nonexistent")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
