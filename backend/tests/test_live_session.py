"""Tests for the live SSE replay session (state, seek, paced streaming)."""

import asyncio

import pytest

from app.agents import PersonalizeProfile
from app.api.live import LiveSession
from app.models.events import EventType
from app.simulator.generator import generate_match


def _match():
    return generate_match(42, "demo")


def _profile(**over):
    args = {"mode": "fan", "language": "en", "favorite_club": None, "player_focus": None}
    args.update(over)
    return PersonalizeProfile(**args)  # type: ignore[arg-type]


def _collect(session: LiveSession, profile) -> list[tuple[str, dict]]:
    async def _all():
        return [(kind, payload) async for kind, payload in session.stream(profile)]

    return asyncio.run(_all())


def test_state_score_counts_all_goals():
    match = _match()
    session = LiveSession(match)
    session.index = len(match.events)
    score = session.state()["score"]
    home_id = match.meta.teams[0].id
    expected = {"home": 0, "away": 0}
    for event in match.events:
        if event.type == EventType.GOAL and event.team_id:
            expected["home" if event.team_id == home_id else "away"] += 1
    assert score == expected
    assert expected["home"] + expected["away"] >= 1


def test_controls_roundtrip_and_validation():
    session = LiveSession(_match())
    assert session.play()["playing"] is True
    assert session.pause()["playing"] is False
    with pytest.raises(ValueError):
        session.set_speed(-1)
    with pytest.raises(ValueError):
        session.seek(-1)
    state = session.seek(80)
    assert state["minute"] >= 79.9
    assert state["index"] > 0
    assert session.timestamps[state["index"]] / 60 >= 80


def test_stream_yields_state_events_moments_then_done():
    session = LiveSession(_match())
    session.set_speed(0)  # instant pacing for tests
    session.play()
    kinds = _collect(session, _profile())
    names = [kind for kind, _ in kinds]
    assert names[0] == "state"
    assert "event" in names
    assert "moment" in names  # the demo scenario always fires moments
    assert names[-1] == "done"
    events = [p for k, p in kinds if k == "event"]
    assert len(events) == len(session.events)
    final = [p for k, p in kinds if k == "done"][0]
    assert final["score"]["home"] + final["score"]["away"] >= 1


def test_goal_events_carry_live_state_updates():
    session = LiveSession(_match())
    session.set_speed(0)
    session.play()
    kinds = _collect(session, _profile())
    states = [p for k, p in kinds if k == "state"]
    # The clock/score must stream during playback, not only at connect.
    assert len(states) > 2
    minutes = [s["minute"] for s in states]
    assert minutes == sorted(minutes)
    assert minutes[-1] >= 89


def test_prepare_caches_per_profile():
    session = LiveSession(_match())
    first = session.prepare(_profile())
    assert session.prepare(_profile()) is first
    assert session.prepare(_profile(mode="analyst")) is not first
