"""Tests for the storyline segmenter on the demo match (Phase 2, zero LLM)."""

from pathlib import Path

from app.engine import AnalyticsEngine, build_storyline
from app.simulator.generator import load_match

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


def _segments():
    match = load_match(SAMPLE)
    home_id = match.meta.teams[0].id
    away_id = match.meta.teams[1].id
    engine = AnalyticsEngine(home_id, away_id)
    for event in match.events:
        engine.update(event)
    segments = build_storyline(engine.samples, engine.moments, home_id, away_id)
    return segments, home_id, away_id


def test_home_control_covers_opening_spell():
    segments, home_id, _ = _segments()
    controls = [s for s in segments if s.label == "control" and s.team_id == home_id]
    assert any(s.start_minute <= 5 and s.end_minute >= 20 for s in controls)


def test_away_press_segment_covers_press_spell():
    segments, _, away_id = _segments()
    presses = [s for s in segments if s.label == "high_press" and s.team_id == away_id]
    assert any(s.start_minute <= 30 and s.end_minute >= 40 for s in presses)


def test_home_shift_segment_covers_minute_60():
    segments, home_id, _ = _segments()
    shifts = [s for s in segments if s.label == "tactical_shift" and s.team_id == home_id]
    assert any(s.start_minute <= 60 <= s.end_minute for s in shifts)


def test_segments_cover_full_match_without_overlap():
    segments, _, _ = _segments()
    assert segments[0].start_minute == 0
    assert segments[-1].end_minute == 90
    for prev, current in zip(segments, segments[1:], strict=False):
        assert current.start_minute == prev.end_minute + 1
    for segment in segments:
        assert segment.start_minute <= segment.end_minute
        assert segment.title
        assert "avg_possession_home" in segment.evidence
