"""Disposable browser-test server. Never opens the user's real photo library."""

import tempfile

import uvicorn

from qc.main import create_app

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="qc-e2e-") as data:
        uvicorn.run(create_app(data), host="127.0.0.1", port=8000)
