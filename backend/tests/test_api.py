"""API route tests: match payload, replay controls, SSE stream (Phase 4)."""

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app

client = TestClient(app)


def setup_function(_):
    routes.reset_session()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_match_payload_shape():
    payload = client.get("/api/match").json()
    assert payload["meta"]["match_id"] == "match_42_demo"
    assert len(payload["meta"]["teams"]) == 2
    assert len(payload["meta"]["teams"][0]["roster"]) == 16
    assert payload["total_events"] >= 1200
    assert len(payload["moments"]) > 0
    types = {m["type"] for m in payload["moments"]}
    assert {"goal", "tactical_shift", "momentum_swing"} <= types
    assert payload["segments"]
    assert len(payload["momentum_series"]) == 91
    assert payload["state"]["playing"] is False


def test_replay_controls_roundtrip():
    assert client.post("/api/replay/play").json()["playing"] is True
    state = client.post("/api/replay/speed", json={"speed": 10}).json()
    assert state["speed"] == 10
    state = client.post("/api/replay/seek", json={"minute": 57}).json()
    assert 56 <= state["minute"] <= 58 and state["index"] > 0
    assert client.post("/api/replay/pause").json()["playing"] is False
    state = client.get("/api/replay/state").json()
    assert state["playing"] is False and state["speed"] == 10


def test_replay_rejects_bad_input():
    assert client.post("/api/replay/speed", json={"speed": -1}).status_code == 422
    assert client.post("/api/replay/seek", json={"minute": -5}).status_code == 422
    assert client.get("/api/replay/stream?mode=coach").status_code == 422
    assert client.get("/api/replay/stream?lang=de").status_code == 422


def test_sse_stream_completes_instant():
    response = client.get("/api/replay/stream?speed=0&mode=fan&lang=en")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "event: done" in body
    assert "event: moment" in body
    assert "match_42_demo" in body


def test_sse_stream_respects_profile():
    response = client.get("/api/replay/stream?speed=0&mode=fan&lang=en&player_focus=NGU_11")
    assert "event: done" in response.text
