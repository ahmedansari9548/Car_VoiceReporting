"""Test 9: WebSocket connection and message flow."""

import json
import pytest


def test_websocket_connect_and_search():
    """Test WebSocket: connect, send a search, get results."""
    import websockets.sync.client as ws

    with ws.connect("ws://localhost:8000/ws") as conn:
        # receive connected message
        msg = json.loads(conn.recv(timeout=5))
        assert msg["type"] == "connected"

        # send a search
        conn.send(json.dumps({"text": "Corolla Lahore 40 lakh"}))

        # receive turn response
        msg = json.loads(conn.recv(timeout=30))
        assert msg["type"] == "turn"
        assert msg["session_id"] is not None
        assert msg["reply"] is not None
        assert msg["phase"] == "searching"
        assert msg["cars"] is not None


def test_websocket_multi_turn():
    """Test WebSocket: multiple turns keep the same session."""
    import websockets.sync.client as ws

    with ws.connect("ws://localhost:8000/ws") as conn:
        # skip connected message
        conn.recv(timeout=5)

        # turn 1
        conn.send(json.dumps({"text": "Honda cars in Lahore"}))
        msg1 = json.loads(conn.recv(timeout=30))
        sid = msg1["session_id"]

        # turn 2 — same session
        conn.send(json.dumps({"text": "under 40 lakh"}))
        msg2 = json.loads(conn.recv(timeout=30))
        assert msg2["session_id"] == sid, "Session changed between turns"
