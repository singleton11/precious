# precious

[![CI](https://github.com/singleton11/precious/actions/workflows/ci.yml/badge.svg)](https://github.com/singleton11/precious/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/singleton11/precious/branch/main/graph/badge.svg)](https://codecov.io/gh/singleton11/precious)

Agent management MVP with:
- **FastAPI** backend (password-protected API)
- **React + Vite** web client for repositories and session management

## Quick start (server + client)

```bash
uv sync
uv run precious-dev        # starts both backend (:8000) and Vite client (:5173)
```

Open <http://localhost:5173>.

## Backend (Python / FastAPI)

```bash
uv sync
uv run precious-server --host 127.0.0.1 --port 8000
```

Set password (defaults to `changeme`):

```bash
export PRECIOUS_SERVER_PASSWORD="changeme"
```

## Client (React)

```bash
cd client
npm install
npm run dev       # dev server at http://localhost:5173, proxies /api to :8000
npm run build     # production build into client/dist/ (served by FastAPI)
```

For production, run `npm run build` then start the server — FastAPI serves the
built client at `/`.

## API overview

- `GET /api/repositories`
- `POST /api/repositories`
- `GET /api/agents` — each agent exposes `supported_thinking_efforts` and `supported_modes`
- `GET /api/sessions`
- `POST /api/sessions`
- `PATCH /api/sessions/{id}`
- `GET /api/sessions/{id}/tool-calls`
- `POST /api/sessions/{id}/tool-calls`

All `/api/*` endpoints require header `X-Server-Password`.

## Tests

```bash
uv run python -m pytest tests/ -v
```
