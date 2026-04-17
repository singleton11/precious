from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app

PASSWORD = "test-pass"


@pytest.fixture()
def client():
    app = create_app(password=PASSWORD)
    return TestClient(app)


def auth(pw: str = PASSWORD) -> dict[str, str]:
    return {"X-Server-Password": pw}


# --- Auth -----------------------------------------------------------------

def test_requires_password(client: TestClient) -> None:
    r = client.get("/api/repositories", headers=auth("wrong"))
    assert r.status_code == 401


def test_health_does_not_require_password(client: TestClient) -> None:
    r = client.get("/health", headers=auth("wrong"))
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# --- Validation -----------------------------------------------------------

def test_post_repository_requires_url(client: TestClient) -> None:
    r = client.post("/api/repositories", json={}, headers=auth())
    assert r.status_code == 422  # Pydantic validation


def test_post_session_requires_agent_id(client: TestClient) -> None:
    r = client.post("/api/sessions", json={"model": "gpt-5-mini"}, headers=auth())
    assert r.status_code == 422


def test_post_session_rejects_invalid_thinking_effort(client: TestClient) -> None:
    r = client.post(
        "/api/sessions",
        json={"agent_id": "acp-coder", "thinking_effort": "extreme"},
        headers=auth(),
    )
    assert r.status_code == 400
    assert "thinking_effort" in r.json()["detail"]


def test_post_session_rejects_invalid_mode(client: TestClient) -> None:
    r = client.post(
        "/api/sessions",
        json={"agent_id": "acp-coder", "mode": "yolo"},
        headers=auth(),
    )
    assert r.status_code == 400
    assert "mode" in r.json()["detail"]


def test_patch_session_rejects_invalid_thinking_effort(client: TestClient) -> None:
    r = client.post("/api/sessions", json={"agent_id": "acp-coder"}, headers=auth())
    sid = r.json()["id"]
    r = client.patch(f"/api/sessions/{sid}", json={"thinking_effort": "ultra"}, headers=auth())
    assert r.status_code == 400
    assert "thinking_effort" in r.json()["detail"]


def test_patch_nonexistent_session(client: TestClient) -> None:
    r = client.patch("/api/sessions/nonexistent-id", json={"model": "x"}, headers=auth())
    assert r.status_code == 404


def test_malformed_json_returns_422(client: TestClient) -> None:
    r = client.post(
        "/api/repositories",
        content=b"not json{{{",
        headers={**auth(), "Content-Type": "application/json"},
    )
    assert r.status_code == 422


def test_tool_call_on_nonexistent_session(client: TestClient) -> None:
    r = client.post(
        "/api/sessions/fake-id/tool-calls",
        json={"name": "bash"},
        headers=auth(),
    )
    assert r.status_code == 404


# --- Full flow ------------------------------------------------------------

def test_repository_and_session_flow(client: TestClient) -> None:
    r = client.post("/api/repositories", json={"url": "https://github.com/singleton11/precious"}, headers=auth())
    assert r.status_code == 201
    repo = r.json()

    r = client.post(
        "/api/sessions",
        json={
            "repository_id": repo["id"],
            "agent_id": "acp-coder",
            "model": "gpt-5-mini",
            "thinking_effort": "high",
            "mode": "build",
        },
        headers=auth(),
    )
    assert r.status_code == 201
    session = r.json()

    r = client.patch(
        f"/api/sessions/{session['id']}",
        json={"model": "gpt-5.4", "thinking_effort": "low", "allowed_tools": ["bash", "view"]},
        headers=auth(),
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["model"] == "gpt-5.4"
    assert updated["thinking_effort"] == "low"
    assert updated["allowed_tools"] == ["bash", "view"]

    r = client.post(
        f"/api/sessions/{session['id']}/tool-calls",
        json={"name": "bash", "status": "completed", "arguments": {"command": "echo hi"}},
        headers=auth(),
    )
    assert r.status_code == 201
    assert r.json()["name"] == "bash"

    r = client.get(f"/api/sessions/{session['id']}/tool-calls", headers=auth())
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_agents_endpoint(client: TestClient) -> None:
    r = client.get("/api/agents", headers=auth())
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) >= 2
    ids = {a["id"] for a in agents}
    assert "acp-coder" in ids
    assert "acp-reviewer" in ids
    # Agents should expose their supported configs
    coder = next(a for a in agents if a["id"] == "acp-coder")
    assert "supported_thinking_efforts" in coder
    assert "supported_modes" in coder


def test_agents_expose_per_agent_capabilities(client: TestClient) -> None:
    r = client.get("/api/agents", headers=auth())
    agents = r.json()
    reviewer = next(a for a in agents if a["id"] == "acp-reviewer")
    # Reviewer supports fewer modes than coder
    assert "build" not in reviewer["supported_modes"]
    assert "plan" in reviewer["supported_modes"]


def test_session_validates_against_agent_capabilities(client: TestClient) -> None:
    # acp-reviewer doesn't support "build" mode
    r = client.post(
        "/api/sessions",
        json={"agent_id": "acp-reviewer", "mode": "build"},
        headers=auth(),
    )
    assert r.status_code == 400
    assert "mode" in r.json()["detail"]


def test_not_found_routes(client: TestClient) -> None:
    r = client.get("/api/nonexistent", headers=auth())
    assert r.status_code in (404, 405)  # FastAPI returns 404 for undefined routes
