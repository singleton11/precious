# precious

Minimal agent management MVP with:
- Python server (password-protected API)
- Web client (JS) for repositories and session management

## Use uv for Python tooling

```bash
uv sync
uv run precious-server --host 127.0.0.1 --port 8000
```

Set password (defaults to `changeme`):

```bash
export PRECIOUS_SERVER_PASSWORD="changeme"
```

Open <http://127.0.0.1:8000>.

## API overview

- `GET /api/repositories`
- `POST /api/repositories`
- `GET /api/agents`
- `GET /api/sessions`
- `POST /api/sessions`
- `PATCH /api/sessions/{id}`
- `GET /api/sessions/{id}/tool-calls`
- `POST /api/sessions/{id}/tool-calls`

All `/api/*` endpoints require header `X-Server-Password`.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
