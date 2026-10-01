"""Deterministic synthetic match generator (Phase 1).

Same ``seed`` + same scenario file always produces the same :class:`MatchData`.
All clubs, players and the stadium come from :mod:`app.simulator.teams` and are
invented. Arcs (possession spells, press spells, counter bursts, a tactical
shift and post-goal momentum swings) are configured per scenario JSON file.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from app.models.events import (
    Event,
    EventOutcome,
    EventType,
    MatchData,
    MatchMeta,
    Player,
    Position,
    Team,
)
from app.simulator.teams import STADIUM, build_teams

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"

#: Base per-event type weights (system events and goals are scheduled separately).
BASE_WEIGHTS: dict[EventType, float] = {
    EventType.PASS: 52.0,
    EventType.PRESSURE: 12.0,
    EventType.POSSESSION_CHANGE: 8.0,
    EventType.TACKLE: 6.0,
    EventType.INTERCEPTION: 5.0,
    EventType.SHOT: 3.5,
    EventType.FOUL: 4.0,
    EventType.CORNER: 2.0,
}

#: Fallback goal-count distribution when the scenario fixes no minutes.
GOAL_COUNT_WEIGHTS: dict[int, float] = {0: 1.0, 1: 2.5, 2: 3.0, 3: 2.5, 4: 1.0}

MIN_EVENTS = 1200
MAX_EVENTS = 1800
PITCH_LENGTH_M = 105.0  # real pitch length mapped onto the 0-100 x grid


def available_scenarios() -> list[str]:
    """Return sorted scenario names found in the scenarios directory."""
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


def load_scenario(name_or_path: str) -> dict:
    """Load a scenario dict by name (``demo``) or file path (JSON)."""
    candidate = Path(name_or_path)
    if candidate.suffix == ".json":
        path = candidate
    else:
        path = SCENARIOS_DIR / f"{name_or_path}.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "name" not in data:
        raise ValueError(f"invalid scenario file: {path}")
    return data


def _active_spell(spells: list[dict], minute: int) -> dict | None:
    for spell in spells:
        if spell["start_minute"] <= minute <= spell["end_minute"]:
            return spell
    return None


def _pick_player(rng: random.Random, squad: list[Player], kind: str) -> Player:
    """Pick a player from the active squad, biased by event kind."""
    weights: list[float] = []
    for player in squad:
        if kind == "shot":
            weights.append(
                {Position.FW: 5.5, Position.MF: 3.5, Position.DF: 0.8, Position.GK: 0.05}[
                    player.position
                ]
            )
        elif kind in ("tackle", "interception"):
            weights.append(
                {Position.DF: 5.0, Position.MF: 3.5, Position.FW: 1.0, Position.GK: 0.3}[
                    player.position
                ]
            )
        else:
            weights.append(
                {Position.GK: 0.6, Position.DF: 2.5, Position.MF: 4.0, Position.FW: 2.8}[
                    player.position
                ]
            )
    return rng.choices(squad, weights=weights, k=1)[0]


def _goal_minutes(rng: random.Random, scenario: dict) -> list[tuple[int, str]]:
    """Return ``(minute, team_key)`` goal slots for the match."""
    if scenario.get("goal_minutes"):
        minutes: list[int] = list(scenario["goal_minutes"])
        teams: list[str] = list(
            scenario.get("goal_teams", ["home", "away", "home"][: len(minutes)])
        )
        while len(teams) < len(minutes):
            teams.append(rng.choice(["home", "away"]))
        return sorted(zip(minutes, teams, strict=True))
    target = scenario.get("target_goals", {"min": 0, "max": 4})
    options = [
        n
        for n in GOAL_COUNT_WEIGHTS
        if target.get("min", 0) <= n <= target.get("max", 4)
    ]
    count = rng.choices(options, weights=[GOAL_COUNT_WEIGHTS[n] for n in options])[0]
    minutes = set()
    while len(minutes) < count:
        minutes.add(rng.randint(4, 90))
    ordered = sorted(minutes)
    return [(m, rng.choice(["home", "away"])) for m in ordered]


def _plan_substitutions(
    rng: random.Random, home: Team, away: Team
) -> list[tuple[int, int, Team, Player, Player]]:
    """Pre-schedule 3-6 substitutions as ``(minute, second, team, off, on)``."""
    plans: list[tuple[int, int, Team, Player, Player]] = []
    for team in (home, away):
        starters = team.roster[:11]
        subs = team.roster[11:]
        n_subs = rng.randint(1, 3)
        minutes = sorted(rng.sample(range(55, 86), k=n_subs))
        # Substitute attackers/midfielders first, keep it plausible.
        off_candidates = [p for p in starters if p.position != Position.GK]
        for minute, off in zip(minutes, rng.sample(off_candidates, k=n_subs)):
            on = subs[len([s for s in plans if s[2].id == team.id]) % len(subs)]
            plans.append((minute, rng.randint(0, 59), team, off, on))
    plans.sort(key=lambda s: (s[0], s[1]))
    return plans


def generate_match(seed: int, scenario: str | dict = "default") -> MatchData:
    """Generate a deterministic synthetic match.

    Args:
        seed: RNG seed; identical seeds + scenario give identical matches.
        scenario: scenario name, path to a scenario JSON file, or scenario dict.
    """
    scenario_dict = load_scenario(scenario) if isinstance(scenario, str) else scenario
    scenario_name = str(scenario_dict.get("name", "custom"))
    rng = random.Random(seed)

    home, away = build_teams()
    match_id = f"match_{seed}_{scenario_name}"
    meta = MatchMeta(
        match_id=match_id,
        teams=[home, away],
        stadium=STADIUM,
        kickoff_time=datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc),
    )

    tempo = float(scenario_dict.get("tempo", 1.0))
    total = min(
        MAX_EVENTS, max(MIN_EVENTS, round(rng.randint(MIN_EVENTS, MAX_EVENTS) * tempo))
    )
    goals = _goal_minutes(rng, scenario_dict)
    subs = _plan_substitutions(rng, home, away)

    n_system = 4 + len(subs)  # kickoffs, half/full time + substitutions
    n_ball = total - n_system - len(goals)

    squads: dict[str, list[Player]] = {
        "home": list(home.roster[:11]),
        "away": list(away.roster[:11]),
    }
    team_of = {"home": home, "away": away}

    raw: list[dict] = []  # unsorted event payloads with a sort key
    ball = [50.0, 50.0]

    def emit(clock_s: float, team_key: str | None, builder: dict) -> None:
        minute = min(90, int(clock_s // 60))
        second = min(59, int(clock_s % 60))
        payload = {
            "clock": clock_s,
            "minute": minute,
            "second": second,
            "period": 1 if minute <= 45 else 2,
            "team_key": team_key,
            **builder,
        }
        raw.append(payload)

    # Opening kickoff.
    emit(0.0, "home", {"type": EventType.KICKOFF, "outcome": EventOutcome.NEUTRAL})

    step = 5390.0 / max(1, n_ball)
    clock = 5.0
    sub_idx = 0
    goal_idx = 0
    pending_goals = sorted(goals)
    last_goal: tuple[int, str] | None = None

    def arc_label(minute: int) -> str:
        if _active_spell(scenario_dict.get("counter_bursts", []), minute):
            return "counter"
        if _active_spell(scenario_dict.get("press_spells", []), minute):
            return "press"
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        if spell:
            return f"possession-{spell['team']}"
        return "open-play"

    emitted = 0
    while emitted < n_ball and clock < 5390.0:
        minute = min(90, int(clock // 60))
        # Scheduled substitutions take priority at their clock time.
        while sub_idx < len(subs) and subs[sub_idx][0] * 60 + subs[sub_idx][1] <= clock:
            s_min, s_sec, s_team, off, on = subs[sub_idx]
            active = squads["home" if s_team.id == home.id else "away"]
            if off in active:
                active.remove(off)
                active.append(on)
            emit(
                s_min * 60 + s_sec,
                "home" if s_team.id == home.id else "away",
                {
                    "type": EventType.SUBSTITUTION,
                    "outcome": EventOutcome.SUCCESS,
                    "player": off,
                    "target": on,
                    "at": (50.0, 50.0),
                    "arc": "tactical-shift",
                },
            )
            sub_idx += 1

        weights = dict(BASE_WEIGHTS)
        press = _active_spell(scenario_dict.get("press_spells", []), minute)
        counter = _active_spell(scenario_dict.get("counter_bursts", []), minute)
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        home_share = 0.5
        if spell:
            home_share = spell["share"] if spell["team"] == "home" else 1 - spell["share"]
        if press:
            weights[EventType.PRESSURE] *= 1.8
            weights[EventType.TACKLE] *= 1.5
            weights[EventType.INTERCEPTION] *= 1.4
            weights[EventType.FOUL] *= 1.5
        if counter:
            weights[EventType.SHOT] *= 1.8
            weights[EventType.CORNER] *= 1.3
        shift = scenario_dict.get("tactical_shift")
        if shift and minute >= int(shift["minute"]):
            weights[EventType.SHOT] *= 1.25
        if last_goal and minute - last_goal[0] <= 10:
            # Momentum swing: the scorer keeps attacking, the concedes presses.
            weights[EventType.SHOT] *= 1.3
            weights[EventType.PRESSURE] *= 1.2
        # Never schedule a random goal; scripted goals are inserted below.
        team_key = "home" if rng.random() < home_share else "away"
        kind = rng.choices(list(weights), weights=list(weights.values()))[0]
        builder = _build_open_play(
            rng, team_key, squads[team_key], kind, ball, minute, arc_label(minute)
        )
        emit(clock, team_key, builder)
        emitted += 1
        clock += rng.uniform(0.4, 1.6) * step
        # Advance scripted-goal pointer past elapsed minutes (inserted later).
        while goal_idx < len(pending_goals) and pending_goals[goal_idx][0] < minute:
            last_goal = pending_goals[goal_idx]
            goal_idx += 1

    # Remaining substitutions that fall after the loop clock.
    while sub_idx < len(subs):
        s_min, s_sec, s_team, off, on = subs[sub_idx]
        emit(
            s_min * 60 + s_sec,
            "home" if s_team.id == home.id else "away",
            {
                "type": EventType.SUBSTITUTION,
                "outcome": EventOutcome.SUCCESS,
                "player": off,
                "target": on,
                "at": (50.0, 50.0),
                "arc": "tactical-shift",
            },
        )
        sub_idx += 1

    # Scripted goals: guaranteed story beats at exact minutes.
    for goal_minute, goal_team in goals:
        scorer = _pick_player(rng, squads[goal_team], "shot")
        goal_x = 100.0 if goal_team == "home" else 0.0
        # Home attacks x=100 in period 1, x=0 in period 2 (sides switch).
        if (min(90, goal_minute) <= 45 and goal_team == "away") or (
            min(90, goal_minute) > 45 and goal_team == "home"
        ):
            goal_x = 100.0 - goal_x
        emit(
            goal_minute * 60 + rng.randint(0, 59),
            goal_team,
            {
                "type": EventType.GOAL,
                "outcome": EventOutcome.GOAL,
                "player": scorer,
                "at": (min(99.0, max(1.0, goal_x + rng.uniform(-6, 2))), 50 + rng.uniform(-18, 18)),
                "xg": round(rng.uniform(0.15, 0.65), 3),
                "shot_speed": round(rng.uniform(75, 125), 1),
                "arc": "goal",
            },
        )

    emit(45 * 60.0, None, {"type": EventType.HALF_TIME, "outcome": EventOutcome.NEUTRAL})
    emit(46 * 60.0, "away", {"type": EventType.KICKOFF, "outcome": EventOutcome.NEUTRAL})
    emit(90 * 60.0, None, {"type": EventType.FULL_TIME, "outcome": EventOutcome.NEUTRAL})

    raw.sort(key=lambda p: (p["clock"], p["type"].value))
    events: list[Event] = []
    for idx, payload in enumerate(raw):
        team_key = payload["team_key"]
        team = team_of[team_key] if team_key else None
        player: Player | None = payload.get("player")
        target: Player | None = payload.get("target")
        x, y = payload.get("at", (50.0, 50.0))
        events.append(
            Event(
                event_id=f"{match_id}_e{idx:05d}",
                match_id=match_id,
                period=payload["period"],
                minute=payload["minute"],
                second=payload["second"],
                timestamp_s=round(payload["clock"], 2),
                type=payload["type"],
                team_id=team.id if team else None,
                player_id=player.id if player else None,
                target_player_id=target.id if target else None,
                x=round(float(x), 2),
                y=round(float(y), 2),
                outcome=payload["outcome"],
                pass_distance_m=payload.get("pass_distance"),
                pass_difficulty=payload.get("pass_difficulty"),
                ball_speed_kmh=payload.get("ball_speed"),
                shot_speed_kmh=payload.get("shot_speed"),
                xg=payload.get("xg"),
                metadata={
                    "scenario": scenario_name,
                    "arc": payload.get("arc", "open-play"),
                },
            )
        )
    return MatchData(meta=meta, events=events)


def _build_open_play(
    rng: random.Random,
    team_key: str,
    squad: list[Player],
    kind: EventType,
    ball: list[float],
    minute: int,
    arc: str,
) -> dict:
    """Build one open-play event payload, advancing the tracked ball position."""
    goal_x = 100.0 if team_key == "home" else 0.0
    if minute > 45:  # sides switch at half-time
        goal_x = 100.0 - goal_x

    if kind == EventType.PASS:
        player = _pick_player(rng, squad, "pass")
        mates = [p for p in squad if p.id != player.id] or squad
        target = rng.choice(mates)
        dx = rng.uniform(-25, 30 if ball[0] < goal_x else -5)
        dy = rng.uniform(-25, 25)
        nx, ny = min(99.0, max(1.0, ball[0] + dx)), min(99.0, max(1.0, ball[1] + dy))
        dist_units = ((nx - ball[0]) ** 2 + (ny - ball[1]) ** 2) ** 0.5
        ball[0], ball[1] = nx, ny
        outcome = rng.choices(
            [EventOutcome.COMPLETE, EventOutcome.INCOMPLETE, EventOutcome.BLOCKED],
            weights=[0.82, 0.13, 0.05],
        )[0]
        return {
            "type": kind,
            "outcome": outcome,
            "player": player,
            "target": target if outcome == EventOutcome.COMPLETE else None,
            "at": (nx, ny),
            "pass_distance": round(dist_units * PITCH_LENGTH_M / 100, 1),
            "pass_difficulty": round(min(0.95, dist_units / 60 + rng.uniform(0, 0.3)), 2),
            "ball_speed": round(rng.uniform(20, 60), 1),
            "arc": arc,
        }
    if kind == EventType.SHOT:
        player = _pick_player(rng, squad, "shot")
        nx = min(99.0, max(60.0, goal_x + rng.uniform(-22, -2) if goal_x == 100.0 else rng.uniform(2, 22)))
        ny = 50 + rng.uniform(-22, 22)
        ball[0], ball[1] = nx, ny
        dist = abs(goal_x - nx)
        outcome = rng.choices(
            [EventOutcome.SAVED, EventOutcome.BLOCKED, EventOutcome.OFF_TARGET],
            weights=[0.35, 0.3, 0.35],
        )[0]
        return {
            "type": kind,
            "outcome": outcome,
            "player": player,
            "at": (nx, ny),
            "shot_speed": round(rng.uniform(70, 130), 1),
            "xg": round(max(0.02, min(0.4, 0.35 - dist / 120 + rng.uniform(-0.03, 0.05))), 3),
            "arc": arc,
        }
    if kind == EventType.CORNER:
        player = _pick_player(rng, squad, "pass")
        nx = goal_x - 3 if goal_x == 100.0 else goal_x + 3
        ball[0], ball[1] = nx, 99.0 if rng.random() < 0.5 else 1.0
        return {
            "type": kind,
            "outcome": rng.choice([EventOutcome.COMPLETE, EventOutcome.INCOMPLETE]),
            "player": player,
            "at": (nx, ball[1]),
            "arc": arc,
        }
    if kind in (EventType.TACKLE, EventType.INTERCEPTION, EventType.PRESSURE):
        player = _pick_player(rng, squad, "tackle")
        ball[0] = min(99.0, max(1.0, ball[0] + rng.uniform(-8, 8)))
        ball[1] = min(99.0, max(1.0, ball[1] + rng.uniform(-8, 8)))
        outcome = (
            rng.choice([EventOutcome.WON, EventOutcome.LOST])
            if kind == EventType.TACKLE
            else rng.choice([EventOutcome.SUCCESS, EventOutcome.NEUTRAL])
        )
        return {
            "type": kind, "outcome": outcome, "player": player, "at": tuple(ball), "arc": arc
        }
    if kind == EventType.POSSESSION_CHANGE:
        player = _pick_player(rng, squad, "pass")
        return {
            "type": kind,
            "outcome": EventOutcome.SUCCESS,
            "player": player,
            "at": tuple(ball),
            "arc": arc,
        }
    # FOUL and any future physical duel type.
    player = _pick_player(rng, squad, "tackle")
    return {
        "type": kind,
        "outcome": EventOutcome.NEUTRAL,
        "player": player,
        "at": tuple(ball),
        "arc": arc,
    }


def save_match(match: MatchData, path: str | Path) -> Path:
    """Write a match to JSON and return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        match.model_dump_json(indent=1), encoding="utf-8"
    )
    return target


def load_match(path: str | Path) -> MatchData:
    """Read a match JSON file back into a validated MatchData."""
    return MatchData.model_validate_json(Path(path).read_text(encoding="utf-8"))
