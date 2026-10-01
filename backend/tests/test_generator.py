"""Tests for the deterministic synthetic match generator."""

from collections import Counter

from app.simulator.generator import generate_match


def test_determinism_by_seed():
    first = generate_match(42, "demo")
    second = generate_match(42, "demo")
    assert first.model_dump_json() == second.model_dump_json()


def test_different_seeds_differ():
    assert (
        generate_match(1, "default").model_dump_json()
        != generate_match(2, "default").model_dump_json()
    )


def test_ordering_and_timestamps():
    match = generate_match(7, "default")
    stamps = [e.timestamp_s for e in match.events]
    assert stamps == sorted(stamps)
    assert stamps[0] == 0.0
    assert stamps[-1] == 5400.0
    for event in match.events:
        assert abs(event.timestamp_s - (event.minute * 60 + event.second)) <= 600


def test_plausible_totals_across_seeds():
    for seed in (1, 7, 42, 99, 123):
        match = generate_match(seed, "default")
        assert 1200 <= len(match.events) <= 1800
        goals = sum(1 for e in match.events if e.type.value == "goal")
        assert 0 <= goals <= 4
        types = Counter(e.type.value for e in match.events)
        assert types["pass"] > types["shot"] > 0
        assert types["kickoff"] == 2
        assert match.meta.teams[0].id != match.meta.teams[1].id


def test_demo_scenario_has_scripted_story_beats():
    match = generate_match(42, "demo")
    goals = [(e.minute, e.team_id) for e in match.events if e.type.value == "goal"]
    assert [minute for minute, _ in goals] == [23, 57, 89]
    arcs = {e.metadata["arc"] for e in match.events}
    assert {"counter", "press"} <= arcs


def test_invented_data_only():
    match = generate_match(42, "demo")
    names = [p.name for t in match.meta.teams for p in t.roster]
    assert len(set(names)) == len(names)  # all players distinct
    assert match.meta.stadium == "Meridian Park"
