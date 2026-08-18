"""
Shared test fixtures.

These tests hit the RUNNING backend (Docker or uvicorn).
Start the backend first, then run: pytest -v
"""

import pytest
import httpx

BASE = "http://localhost:8000"


@pytest.fixture(scope="session")
def client():
    """HTTP client pointed at the running backend."""
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


@pytest.fixture
def turn(client):
    """Helper to send a turn. Returns response dict."""
    def _send(text, session_id=None):
        body = {"text": text}
        if session_id:
            body["session_id"] = session_id
        r = client.post("/api/turns", json=body)
        assert r.status_code == 200, f"Turn failed: {r.text}"
        return r.json()
    return _send


@pytest.fixture
def new_chat(turn):
    """Start a fresh conversation and return (response, session_id)."""
    def _start(text):
        result = turn(text)
        return result, result["session_id"]
    return _start
