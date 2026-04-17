"""Launch the FastAPI backend and the Vite dev server side-by-side.

Usage:
    uv run precious-dev          # defaults to 127.0.0.1:8000
    uv run precious-dev --port 9000
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run server + client together")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    client_dir = Path(__file__).resolve().parent.parent / "client"
    if not (client_dir / "package.json").exists():
        print(f"Client directory not found at {client_dir}", file=sys.stderr)
        sys.exit(1)

    # Install client deps if needed
    if not (client_dir / "node_modules").is_dir():
        print("→ Installing client dependencies …")
        subprocess.check_call(["npm", "install"], cwd=str(client_dir))

    env = os.environ.copy()

    # Start the FastAPI backend
    server_cmd = [
        sys.executable, "-m", "uvicorn",
        "server.app:create_app", "--factory",
        "--host", args.host,
        "--port", str(args.port),
        "--reload",
    ]
    print(f"→ Starting server on http://{args.host}:{args.port}")
    server_proc = subprocess.Popen(server_cmd, env=env)

    # Start the Vite dev server (proxies /api to the backend)
    print("→ Starting client dev server …")
    client_proc = subprocess.Popen(["npm", "run", "dev"], cwd=str(client_dir), env=env)

    def _shutdown(signum: int, frame: object) -> None:
        server_proc.terminate()
        client_proc.terminate()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        # Wait for either process to exit
        while True:
            srv_rc = server_proc.poll()
            cli_rc = client_proc.poll()
            if srv_rc is not None or cli_rc is not None:
                break
            try:
                server_proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
    finally:
        server_proc.terminate()
        client_proc.terminate()
        server_proc.wait()
        client_proc.wait()

    sys.exit(server_proc.returncode or client_proc.returncode or 0)


if __name__ == "__main__":
    main()
