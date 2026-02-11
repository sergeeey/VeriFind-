"""Unit tests for WebSocket endpoint wiring and protocol basics."""

import json

from fastapi.testclient import TestClient

from src.api.main import app


def test_websocket_ping_pong():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"action": "ping"}))
        message = json.loads(websocket.receive_text())
        assert message["type"] == "pong"


def test_websocket_subscribe_ack():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"action": "subscribe", "query_id": "q-123"}))
        message = json.loads(websocket.receive_text())
        assert message["type"] == "subscribed"
        assert message["query_id"] == "q-123"
