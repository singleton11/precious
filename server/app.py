from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent registry – each agent advertises its own supported modes and
# thinking-effort levels so the client can adapt dynamically.
# ---------------------------------------------------------------------------

class AgentDefinition(BaseModel):
    id: str
    name: str
    supported_thinking_efforts: list[str]
    supported_modes: list[str]


AGENT_REGISTRY: list[AgentDefinition] = [
    AgentDefinition(
        id="acp-coder",
        name="ACP Coder",
        supported_thinking_efforts=["low", "medium", "high"],
        supported_modes=["plan", "build", "chat"],
    ),
    AgentDefinition(
        id="acp-reviewer",
        name="ACP Reviewer",
        supported_thinking_efforts=["low", "medium", "high"],
        supported_modes=["plan", "chat"],
    ),
]

_AGENTS_BY_ID: dict[str, AgentDefinition] = {a.id: a for a in AGENT_REGISTRY}


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RepositoryCreate(BaseModel):
    url: str = Field(..., min_length=1)


class SessionCreate(BaseModel):
    agent_id: str = Field(..., min_length=1)
    repository_id: str | None = None
    model: str = "gpt-5-mini"
    thinking_effort: str = "medium"
    mode: str = "plan"
    allowed_tools: list[str] = Field(default_factory=list)


class SessionUpdate(BaseModel):
    model: str | None = None
    thinking_effort: str | None = None
    mode: str | None = None
    allowed_tools: list[str] | None = None


class ToolCallCreate(BaseModel):
    name: str = "unknown"
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

class AppState:
    def __init__(self) -> None:
        self.repositories: list[dict[str, Any]] = []
        self.sessions: list[dict[str, Any]] = []
        self.tool_calls: dict[str, list[dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(password: str | None = None) -> FastAPI:
    server_password = password or os.environ.get("PRECIOUS_SERVER_PASSWORD", "changeme")
    state = AppState()
    app = FastAPI(title="Precious Agent Management")

    # --- Auth dependency ---------------------------------------------------

    async def require_password(x_server_password: str = Header("")):
        if not x_server_password or x_server_password != server_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    # --- Helpers -----------------------------------------------------------

    def _validate_agent_fields(agent_id: str, thinking_effort: str | None, mode: str | None) -> None:
        agent = _AGENTS_BY_ID.get(agent_id)
        if agent is None:
            raise HTTPException(status_code=400, detail=f"Unknown agent_id: {agent_id}")
        if thinking_effort is not None and thinking_effort not in agent.supported_thinking_efforts:
            raise HTTPException(
                status_code=400,
                detail=f"thinking_effort must be one of {agent.supported_thinking_efforts}",
            )
        if mode is not None and mode not in agent.supported_modes:
            raise HTTPException(
                status_code=400,
                detail=f"mode must be one of {agent.supported_modes}",
            )

    def _find_session(session_id: str) -> dict[str, Any]:
        for s in state.sessions:
            if s["id"] == session_id:
                return s
        raise HTTPException(status_code=404, detail="Session not found")

    # --- Health (no auth) --------------------------------------------------

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # --- Repositories ------------------------------------------------------

    @app.get("/api/repositories", dependencies=[Depends(require_password)])
    async def list_repositories():
        return state.repositories

    @app.post("/api/repositories", status_code=201, dependencies=[Depends(require_password)])
    async def create_repository(body: RepositoryCreate):
        item = {"id": str(uuid.uuid4()), "url": body.url.strip(), "created_at": _now_iso()}
        state.repositories.append(item)
        return item

    # --- Agents ------------------------------------------------------------

    @app.get("/api/agents", dependencies=[Depends(require_password)])
    async def list_agents():
        return [a.model_dump() for a in AGENT_REGISTRY]

    # --- Sessions ----------------------------------------------------------

    @app.get("/api/sessions", dependencies=[Depends(require_password)])
    async def list_sessions():
        return state.sessions

    @app.post("/api/sessions", status_code=201, dependencies=[Depends(require_password)])
    async def create_session(body: SessionCreate):
        _validate_agent_fields(body.agent_id, body.thinking_effort, body.mode)
        session = {
            "id": str(uuid.uuid4()),
            "repository_id": body.repository_id,
            "agent_id": body.agent_id,
            "model": body.model,
            "thinking_effort": body.thinking_effort,
            "mode": body.mode,
            "allowed_tools": body.allowed_tools,
            "status": "running",
            "created_at": _now_iso(),
        }
        state.sessions.append(session)
        state.tool_calls[session["id"]] = []
        return session

    @app.patch("/api/sessions/{session_id}", dependencies=[Depends(require_password)])
    async def update_session(session_id: str, body: SessionUpdate):
        session = _find_session(session_id)
        # Validate against the agent's supported values
        _validate_agent_fields(
            session["agent_id"],
            body.thinking_effort,
            body.mode,
        )
        for field_name in ("model", "thinking_effort", "mode", "allowed_tools"):
            value = getattr(body, field_name)
            if value is not None:
                session[field_name] = value
        session["updated_at"] = _now_iso()
        return session

    # --- Tool calls --------------------------------------------------------

    @app.get("/api/sessions/{session_id}/tool-calls", dependencies=[Depends(require_password)])
    async def list_tool_calls(session_id: str):
        if session_id not in state.tool_calls:
            raise HTTPException(status_code=404, detail="Session not found")
        return state.tool_calls[session_id]

    @app.post("/api/sessions/{session_id}/tool-calls", status_code=201, dependencies=[Depends(require_password)])
    async def create_tool_call(session_id: str, body: ToolCallCreate):
        if session_id not in state.tool_calls:
            raise HTTPException(status_code=404, detail="Session not found")
        tool_call = {
            "id": str(uuid.uuid4()),
            "name": body.name,
            "arguments": body.arguments,
            "status": body.status,
            "created_at": _now_iso(),
        }
        state.tool_calls[session_id].append(tool_call)
        return tool_call

    # --- Static files (serve React build) ----------------------------------

    client_dist = Path(__file__).resolve().parent.parent / "client" / "dist"
    if client_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(client_dist), html=True), name="client")

    return app


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run precious agent management server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
