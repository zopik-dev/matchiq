"""Tests for player telemetry and goal X-Ray endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.engine.telemetry import goal_xray, player_telemetry
from app.main import app
from app.simulator.generator import load_match

client = TestClient(app)


def _match():
    from pathlib import Path

    return load_match(
        Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"
    )


def _scorer_id():
    match = _match()
    goal = next(e for e in match.events if e.type.value == "goal")
    assert goal.player_id is not None
    return goal.player_id


def test_telemetry_shape_and_ranges():
    dossier = player_telemetry(_match(), _scorer_id())
    assert dossier["goals"] >= 1
    assert dossier["xg"] > 0
    assert 0 <= dossier["pass_accuracy"] <= 100
    assert 0 <= dossier["top_speed_kmh"] <= 36
    assert dossier["distance_m"] >= 0
    assert dossier["touches"] > 0
    assert dossier["name"] in dossier["insight"]


def test_telemetry_modes_differ():
    pid = _scorer_id()
    match = _match()
    en = player_telemetry(match, pid, lang="en", mode="analyst")["insight"]
    fan = player_telemetry(match, pid, lang="en", mode="fan")["insight"]
    assert en != fan


def test_telemetry_unknown_player():
    with pytest.raises(KeyError):
        player_telemetry(_match(), "NOPE_99")


def test_telemetry_endpoint():
    pid = _scorer_id()
    res = client.get(f"/api/players/{pid}/telemetry?mode=fan&lang=en")
    assert res.status_code == 200
    assert res.json()["player_id"] == pid
    assert client.get("/api/players/NOPE_99/telemetry").status_code == 404
    assert client.get(f"/api/players/{pid}/telemetry?lang=de").status_code == 422


def _goal_moment_id():
    payload = client.get("/api/match").json()
    goal = next(m for m in payload["moments"] if m["type"] == "goal")
    return goal["id"]


def test_xray_steps_are_ordered_and_grounded():
    from app.engine import AnalyticsEngine

    match = _match()
    names = match.meta.display_names()
    engine = AnalyticsEngine(match.meta.teams[0].id, match.meta.teams[1].id, names)
    for event in match.events:
        engine.update(event)
    mid = _goal_moment_id()
    xr = goal_xray(match, engine.moments, mid)
    assert xr["moment_id"] == mid
    assert len(xr["steps"]) >= 2
    assert xr["steps"][-1]["type"] == "goal"
    assert xr["steps"][-1]["step_label"] == "Finish"
    assert xr["steps"][-2]["step_label"] == "Key Pass"
    stamps = [s["timestamp_s"] for s in xr["steps"]]
    assert stamps == sorted(stamps)
    assert xr["xg"] is not None and xr["xg"] >= 0.25


def test_xray_endpoint_and_errors():
    mid = _goal_moment_id()
    res = client.get(f"/api/moments/{mid}/xray")
    assert res.status_code == 200
    assert res.json()["steps"][-1]["type"] == "goal"
    assert client.get("/api/moments/m9999/xray").status_code == 404
    payload = client.get("/api/match").json()
    non_goal = next(m for m in payload["moments"] if m["type"] != "goal")
    assert client.get(f"/api/moments/{non_goal['id']}/xray").status_code == 400
