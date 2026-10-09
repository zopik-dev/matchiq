"""Tests for the deterministic synthetic match generator."""

import math
from collections import Counter

from app.simulator.generator import generate_match

RESET_TYPES = {
    "kickoff",
    "half_time",
    "full_time",
    "substitution",
    "corner",
    "goal",
    "goal_kick",
}


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


def _chain_continuity_violations(match):
    """Pairs where the ball teleports instead of travelling.

    Shots/goals fly from the ball (origin recorded in metadata); everything
    else must start where the previous event ended.
    """
    bad = []
    events = match.events
    for prev, cur in zip(events, events[1:], strict=False):
        if prev.type.value in RESET_TYPES or cur.type.value in RESET_TYPES:
            continue
        if cur.metadata.get("arc") == "restart":
            continue
        if cur.type.value in ("shot", "goal"):
            origin = cur.metadata.get("from") or [cur.x, cur.y]
            d0 = math.hypot(prev.x - origin[0], prev.y - origin[1])
            d1 = math.hypot(origin[0] - cur.x, origin[1] - cur.y)
            if d0 > 12 or d1 > 62:
                bad.append((prev, cur, d0, d1))
        elif prev.type.value in ("shot", "goal"):
            d = math.hypot(prev.x - cur.x, prev.y - cur.y)
            if d > 42:  # aftermath scatter plus one full pass
                bad.append((prev, cur, d, None))
        else:
            d = math.hypot(prev.x - cur.x, prev.y - cur.y)
            if d > 32:
                bad.append((prev, cur, d, None))
    return bad


def test_possession_chain_continuity():
    for seed, scenario in ((42, "demo"), (7, "default")):
        match = generate_match(seed, scenario)
        bad = _chain_continuity_violations(match)
        assert bad == [], [(a.minute, a.type.value, b.type.value, c) for a, b, c, *_ in bad[:3]]


def test_passes_have_logical_receivers():
    match = generate_match(42, "demo")
    complete = [e for e in match.events if e.type.value == "pass" and e.outcome.value == "complete"]
    assert len(complete) > 400
    with_target = [e for e in complete if e.target_player_id and e.target_player_id != e.player_id]
    assert len(with_target) / len(complete) > 0.9


def test_goal_buildups_are_coherent():
    match = generate_match(42, "demo")
    for goal in [e for e in match.events if e.type.value == "goal"]:
        leadup = [
            e
            for e in match.events
            if e.team_id == goal.team_id
            and e.type.value == "pass"
            and e.outcome.value == "complete"
            and goal.timestamp_s - 60 <= e.timestamp_s < goal.timestamp_s
        ]
        assert len(leadup) >= 3, f"goal at {goal.minute}' has only {len(leadup)} lead-up passes"
        assert goal.metadata.get("from") is not None  # shot origin recorded
