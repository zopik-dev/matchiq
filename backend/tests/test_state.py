"""Tests for incremental rolling-window state (Phase 2, zero LLM)."""

from pathlib import Path

from app.engine import AnalyticsEngine
from app.engine.state import WINDOWS
from app.simulator.generator import load_match

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


def _engine():
    match = load_match(SAMPLE)
    home_id = match.meta.teams[0].id
    away_id = match.meta.teams[1].id
    engine = AnalyticsEngine(home_id, away_id)
    return match, engine, home_id, away_id


def test_windows_supported():
    assert WINDOWS == (1, 5, 10)


def test_early_home_dominance_in_5min_window():
    match, engine, home_id, away_id = _engine()
    for event in match.events:
        engine.update(event)
        if event.minute >= 10 and event.timestamp_s >= 10 * 60:
            break
    stats = engine.state.window_stats(5)
    assert stats.teams[home_id].possession_pct >= 60
    assert stats.teams[home_id].xg_sum > stats.teams[away_id].xg_sum
    assert stats.momentum[home_id] > 0
    assert stats.tempo_per_min > 10


def test_away_on_top_after_equaliser_spell():
    match, engine, home_id, away_id = _engine()
    # Feed only up to 62:00: the trailing state must reflect the match
    # as played so far (the deque only retains the last 10 minutes).
    for event in match.events:
        engine.update(event)
        if event.timestamp_s >= 62 * 60:
            break
    stats = engine.state.window_stats(5)
    assert stats.momentum[away_id] > 0
    assert stats.teams[away_id].xg_sum > stats.teams[home_id].xg_sum


def test_window_stats_are_well_formed():
    match, engine, home_id, away_id = _engine()
    for event in match.events:
        engine.update(event)
    for minutes in WINDOWS:
        stats = engine.state.window_stats(minutes)
        home = stats.teams[home_id]
        away = stats.teams[away_id]
        assert home.possession_pct + away.possession_pct == 100.0 or (
            home.possession_pct == 50.0 and away.possession_pct == 50.0
        )
        assert 0 <= home.pass_accuracy_pct <= 100
        assert home.pressure_events >= 0 and home.high_turnovers >= 0
        assert stats.momentum[home_id] == round(-stats.momentum[away_id], 2)
        assert -100 <= stats.momentum[home_id] <= 100


def test_incremental_feeding_is_deterministic():
    first = _engine()[1]
    second = _engine()[1]
    match = load_match(SAMPLE)
    for event in match.events:
        first.update(event)
        second.update(event)
    assert [m.id for m in first.moments] == [m.id for m in second.moments]
    assert first.state.score == second.state.score == {"NGU": 2, "EVR": 1}
