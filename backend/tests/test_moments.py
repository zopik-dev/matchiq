"""Tests for key-moment detectors on the demo match (Phase 2, zero LLM)."""

from pathlib import Path

from app.engine import AnalyticsEngine
from app.simulator.generator import load_match

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


def _run():
    match = load_match(SAMPLE)
    home_id = match.meta.teams[0].id
    away_id = match.meta.teams[1].id
    engine = AnalyticsEngine(home_id, away_id)
    for event in match.events:
        engine.update(event)
    return engine, home_id, away_id


def _of_type(engine, kind):
    return [m for m in engine.moments if m.type == kind]


def test_goals_at_scripted_minutes_with_scores():
    engine, home_id, away_id = _run()
    goals = _of_type(engine, "goal")
    assert [(g.minute, g.team_id) for g in goals] == [
        (23, home_id),
        (57, away_id),
        (89, home_id),
    ]
    assert [g.evidence["score"] for g in goals] == ["1-0", "1-1", "2-1"]
    for goal in goals:
        assert goal.evidence["scorer"]
        assert goal.evidence["xg"] is not None


def test_all_demo_goals_are_big_chances():
    engine, _, _ = _run()
    chance_minutes = {m.minute for m in _of_type(engine, "big_chance")}
    assert {23, 57, 89} <= chance_minutes
    for chance in _of_type(engine, "big_chance"):
        assert chance.evidence["xg"] >= 0.25


def test_away_press_spike_opens_the_press_spell():
    engine, _, away_id = _run()
    spikes = [m for m in _of_type(engine, "pressure_spike") if m.team_id == away_id]
    assert any(24 <= m.minute <= 32 for m in spikes)
    for spike in spikes:
        assert spike.evidence["pressure_events"] >= 14


def test_home_tactical_shift_at_scenario_minute():
    engine, home_id, _ = _run()
    shifts = [m for m in _of_type(engine, "tactical_shift") if m.team_id == home_id]
    assert any(58 <= m.minute <= 62 for m in shifts)
    assert shifts[0].evidence["player_off"] != shifts[0].evidence["player_on"]


def test_goal_swings_follow_equaliser_and_winner():
    engine, home_id, away_id = _run()
    swings = _of_type(engine, "momentum_swing")
    assert any(m.team_id == away_id and abs(m.minute - 57) <= 5 for m in swings)
    assert any(m.team_id == home_id and abs(m.minute - 89) <= 5 for m in swings)
    for swing in swings:
        assert "momentum_home_after" in swing.evidence


def test_every_moment_carries_evidence():
    engine, _, _ = _run()
    assert engine.moments
    for moment in engine.moments:
        assert moment.title
        assert isinstance(moment.evidence, dict) and moment.evidence
