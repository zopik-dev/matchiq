"""API route tests: match payload, replay controls, SSE stream (Phase 4)."""

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app

client = TestClient(app)


def setup_function(_):
    routes.reset_session()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_integrations_reports_offline_defaults(monkeypatch):
    from app.config import reload_settings

    for var in (
        "MATCHIQ_AZURE_ENDPOINT",
        "MATCHIQ_AZURE_API_KEY",
        "MATCHIQ_AZURE_DEPLOYMENT",
        "MATCHIQ_AZURE_FOUNDRY_ENDPOINT",
        "MATCHIQ_AZURE_FOUNDRY_API_KEY",
        "MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT",
        "MATCHIQ_AZURE_SPEECH_KEY",
        "MATCHIQ_COSMOS_ENDPOINT",
        "MATCHIQ_COSMOS_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    reload_settings()
    try:
        payload = client.get("/api/integrations").json()
        assert payload == {
            "llm": {"provider": "mock", "deployment": None},
            "speech": {"provider": "browser", "region": "westeurope"},
            "store": {"provider": "memory"},
        }
    finally:
        monkeypatch.undo()
        reload_settings()


def test_index_points_to_dashboard():
    payload = client.get("/").json()
    assert payload["service"] == "MatchIQ API"
    assert payload["dashboard"] == "http://localhost:5173"
    assert "GET /api/match" in payload["endpoints"]


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
    totals = payload["totals"]
    assert totals["xg_home"] > 0 and totals["xg_away"] > 0
    assert abs(totals["poss_home"] + totals["poss_away"] - 100) < 0.2
    # Cumulative series: 91 points, monotonic, finals match totals.
    xg = payload["xg_series"]
    poss = payload["poss_series"]
    assert [p["minute"] for p in xg] == list(range(91))
    assert [p["minute"] for p in poss] == list(range(91))
    for prev, cur in zip(xg, xg[1:], strict=False):
        assert cur["home"] >= prev["home"] and cur["away"] >= prev["away"]
    assert (xg[-1]["home"], xg[-1]["away"]) == (totals["xg_home"], totals["xg_away"])
    assert abs(poss[-1]["home"] - totals["poss_home"]) < 0.15
    # Minute 14 (0-0): only early chances counted, far from final totals.
    early = xg[14]
    assert early["home"] < totals["xg_home"] / 2
    assert early["away"] < 1.0
    # Moment titles show names, never raw ids.
    goal_titles = [m["title"] for m in payload["moments"] if m["type"] == "goal"]
    assert goal_titles and all("(" in t and ")" in t for t in goal_titles)
    assert not any("NGU_" in m["title"] or "EVR_" in m["title"] for m in payload["moments"])


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
