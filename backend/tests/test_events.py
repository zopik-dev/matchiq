"""Tests for the Phase 1 event schema validation."""

import pytest
from pydantic import ValidationError

from app.models.events import Event, EventType, MatchMeta, Team
from app.simulator.teams import build_teams


def _base_event(**overrides):
    payload = {
        "event_id": "e1",
        "match_id": "m1",
        "period": 1,
        "minute": 10,
        "second": 5,
        "timestamp_s": 605.0,
        "type": EventType.PASS,
        "team_id": "NGU",
        "player_id": "NGU_8",
        "x": 50.0,
        "y": 30.0,
        "outcome": "complete",
    }
    payload.update(overrides)
    return Event(**payload)


def test_valid_event_passes():
    event = _base_event()
    assert event.type == EventType.PASS
    assert event.metadata == {}


def test_rejects_out_of_range_coordinates():
    with pytest.raises(ValidationError):
        _base_event(x=101.0)
    with pytest.raises(ValidationError):
        _base_event(y=-1.0)


def test_rejects_bad_period_and_minute():
    with pytest.raises(ValidationError):
        _base_event(minute=60, period=1)
    with pytest.raises(ValidationError):
        _base_event(minute=10, period=2)


def test_rejects_timestamp_far_from_clock():
    with pytest.raises(ValidationError):
        _base_event(minute=10, second=5, timestamp_s=3000.0)


def test_rejects_xg_on_non_shot():
    with pytest.raises(ValidationError):
        _base_event(xg=0.2)


def test_allows_xg_on_shot_and_goal():
    shot = _base_event(type=EventType.SHOT, outcome="saved", xg=0.25)
    assert shot.xg == 0.25
    goal = _base_event(type=EventType.GOAL, outcome="goal", xg=0.5)
    assert goal.xg == 0.5


def test_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        _base_event(type="bicycle_kick")


def test_system_events_need_no_player():
    half_time = _base_event(
        type=EventType.HALF_TIME,
        outcome="neutral",
        team_id=None,
        player_id=None,
        minute=45,
        second=0,
        timestamp_s=2700.0,
    )
    assert half_time.player_id is None


def test_open_play_requires_team_and_player():
    with pytest.raises(ValidationError):
        _base_event(team_id=None)
    with pytest.raises(ValidationError):
        _base_event(player_id=None)


def test_match_meta_has_two_invented_teams():
    home, away = build_teams()
    assert len(home.roster) == 16  # 11 starters + 5 subs
    assert len(away.roster) == 16
    meta = MatchMeta(
        match_id="m1",
        teams=[home, away],
        stadium="Meridian Park",
        kickoff_time="2026-09-12T15:00:00Z",
    )
    assert len(meta.teams) == 2


def test_team_rejects_duplicate_numbers():
    home, _ = build_teams()
    roster = list(home.roster)
    roster[1] = roster[1].model_copy(update={"number": roster[0].number})
    with pytest.raises(ValidationError):
        Team(id="X", name="X Utd", formation="4-4-2", roster=roster)
