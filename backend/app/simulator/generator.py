"""Deterministic synthetic match generator (Phase 1), possession-chain edition.

Same ``seed`` + same scenario file always produces the same :class:`MatchData`.
All clubs, players and the stadium come from :mod:`app.simulator.teams` and are
invented. Arcs (possession spells, press spells, counter bursts, a tactical
shift and post-goal momentum swings) are configured per scenario JSON file.

Physics model: the match is a sequence of possession chains. A chain belongs
to one team; every event starts exactly where the previous one ended (no
teleports). Passes travel from the ball carrier to a nearby teammate chosen
near a progressive target point, so play flows back-to-front through
build-up (own third), progression (midfield) and creation (final third).
Turnovers flip possession to the defender standing at that exact spot.
Scripted goals grow a 4-6 pass buildup ending in a box finish.
"""

import json
import math
import random
from datetime import UTC, datetime
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
#: SHOT is raised vs. a naive mix because shots only fire from the final third.
BASE_WEIGHTS: dict[EventType, float] = {
    EventType.PASS: 52.0,
    EventType.PRESSURE: 12.0,
    EventType.POSSESSION_CHANGE: 8.0,
    EventType.TACKLE: 6.0,
    EventType.INTERCEPTION: 5.0,
    EventType.SHOT: 6.0,
    EventType.FOUL: 4.0,
    EventType.CORNER: 2.0,
}

#: Fallback goal-count distribution when the scenario fixes no minutes.
GOAL_COUNT_WEIGHTS: dict[int, float] = {0: 1.0, 1: 2.5, 2: 3.0, 3: 2.5, 4: 1.0}

MIN_EVENTS = 1200
MAX_EVENTS = 1800
PITCH_LENGTH_M = 105.0  # real pitch length mapped onto the 0-100 x grid

#: Attacking-coordinate phase boundaries (ax = distance from own goal, 0-100).
BUILDUP_AX = 35.0
CREATION_AX = 65.0
#: Shots only fire from this attacking-x onward (keeps finishes realistic).
SHOT_MIN_AX = 52.0
#: Minimum seconds between possession flips (after dead-ball restarts the
#: clock resets); stops chain ping-pong so windowed possession stays stable.
FLIP_COOLDOWN_S = 12.0


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
    options = [n for n in GOAL_COUNT_WEIGHTS if target.get("min", 0) <= n <= target.get("max", 4)]
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
        for minute, off in zip(minutes, rng.sample(off_candidates, k=n_subs), strict=True):
            on = subs[len([s for s in plans if s[2].id == team.id]) % len(subs)]
            plans.append((minute, rng.randint(0, 59), team, off, on))
    plans.sort(key=lambda s: (s[0], s[1]))
    return plans


def _spread_ys(n: int) -> list[float]:
    """Vertical formation slots on the 0-100 grid, centred on 50."""
    if n <= 1:
        return [50.0]
    gap = min(22.0, 76.0 / (n - 1))
    start = 50.0 - gap * (n - 1) / 2
    return [start + i * gap for i in range(n)]


def _anchor_grid(starters: list[Player], mirror: bool) -> dict[str, list[float]]:
    """Formation anchor per player id (absolute coords, home orientation unless mirrored)."""
    by_line: dict[Position, list[Player]] = {}
    for player in starters:
        by_line.setdefault(player.position, []).append(player)
    bases = {Position.GK: 8.0, Position.DF: 20.0, Position.MF: 36.0, Position.FW: 52.0}
    anchors: dict[str, list[float]] = {}
    for line, members in by_line.items():
        ys = _spread_ys(len(members))
        for player, y in zip(members, ys, strict=True):
            x = bases.get(line, 36.0)
            anchors[player.id] = [100.0 - x if mirror else x, y]
    return anchors


def _nearest(
    rng: random.Random,
    squad: list[Player],
    anchors: dict[str, list[float]],
    point: tuple[float, float],
    line_bonus: dict[Position, float] | None = None,
    exclude: set[str] | None = None,
    role_first: list[Position] | None = None,
    allow_gk: bool = False,
) -> Player:
    """Pick a nearby player, weighted toward the point with line preference.

    With ``role_first``, only players of the first available role group are
    considered (e.g. a forward always shoots ahead of a nearby goalkeeper).
    Goalkeepers are excluded unless ``allow_gk`` (backpasses, claimed crosses).
    """
    pool = [p for p in squad if not (exclude and p.id in exclude)]
    if not allow_gk:
        pool = [p for p in pool if p.position != Position.GK] or pool
    if role_first:
        for role in role_first:
            group = [p for p in pool if p.position == role]
            if group:
                pool = group
                break
    scored: list[tuple[float, Player]] = []
    for player in pool:
        anchor = anchors.get(player.id)
        if anchor is None:
            continue
        dist = math.hypot(anchor[0] - point[0], anchor[1] - point[1])
        bonus = (line_bonus or {}).get(player.position, 0.0)
        scored.append((dist - bonus, player))
    scored.sort(key=lambda item: item[0])
    best = scored[:4] or scored[:1]
    weights = [max(0.1, 12.0 - max(0.0, score)) for score, _ in best]
    return rng.choices([player for _, player in best], weights=weights, k=1)[0]


def _to_attacking(x: float, goal_x: float) -> float:
    """Attacking coordinate: distance from the team's own goal (0-100)."""
    return x if goal_x == 100.0 else 100.0 - x


def _to_absolute(ax: float, y: float, goal_x: float) -> tuple[float, float]:
    """Back to absolute grid coords from attacking coords."""
    return (ax if goal_x == 100.0 else 100.0 - ax, y)


def _jitter(rng: random.Random, point: tuple[float, float], amount: float) -> tuple[float, float]:
    return (
        min(99.0, max(1.0, point[0] + rng.uniform(-amount, amount))),
        min(99.0, max(1.0, point[1] + rng.uniform(-amount, amount))),
    )


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
        kickoff_time=datetime(2026, 9, 12, 15, 0, tzinfo=UTC),
    )

    tempo = float(scenario_dict.get("tempo", 1.0))
    total = min(MAX_EVENTS, max(MIN_EVENTS, round(rng.randint(MIN_EVENTS, MAX_EVENTS) * tempo)))
    goals = _goal_minutes(rng, scenario_dict)
    subs = _plan_substitutions(rng, home, away)
    # The shifting team makes its first substitution exactly at the tactical-shift
    # minute, so the shift is visible in the event stream (shifts come with subs).
    shift = scenario_dict.get("tactical_shift")
    if shift is not None:
        shift_team = {"home": home, "away": away}[str(shift["team"])]
        for i, (_mn, _sc, team, off, on) in enumerate(subs):
            if team.id == shift_team.id:
                subs[i] = (int(shift["minute"]), 0, team, off, on)
                break
        subs.sort(key=lambda s: (s[0], s[1]))

    n_system = 4 + len(subs)  # kickoffs, half/full time + substitutions
    n_ball = total - n_system - len(goals)

    squads: dict[str, list[Player]] = {
        "home": list(home.roster[:11]),
        "away": list(away.roster[:11]),
    }
    team_of = {"home": home, "away": away}
    anchors: dict[str, list[float]] = {}
    anchors.update(_anchor_grid(home.roster[:11], mirror=False))
    anchors.update(_anchor_grid(away.roster[:11], mirror=True))

    raw: list[dict] = []  # unsorted event payloads with a sort key

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

    def goal_x_of(team_key: str, minute: int) -> float:
        base = 100.0 if team_key == "home" else 0.0
        return base if minute <= 45 else 100.0 - base

    def possession_spell_team(minute: int) -> str | None:
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        return str(spell["team"]) if spell else None

    def pressing_team(minute: int) -> str | None:
        press = _active_spell(scenario_dict.get("press_spells", []), minute)
        return str(press["team"]) if press else None

    def counter_team(minute: int) -> str | None:
        burst = _active_spell(scenario_dict.get("counter_bursts", []), minute)
        return str(burst["team"]) if burst else None

    def arc_label(minute: int) -> str:
        if counter_team(minute):
            return "counter"
        if pressing_team(minute):
            return "press"
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        if spell:
            return f"possession-{spell['team']}"
        return "open-play"

    # -- chain state: who has the ball, where it is --------------------
    ball: list[float] = [50.0, 50.0]
    poss_key = "home"
    carrier: Player = _nearest(rng, squads["home"], anchors, (50.0, 50.0))
    flip_blocked_until = -1e9
    flip_blocked_team: str | None = None

    def reset_chain(team_key: str, at: tuple[float, float]) -> None:
        """Restart a chain (kickoff, goal kick, second half): ball + carrier set."""
        nonlocal poss_key, carrier, flip_blocked_until, flip_blocked_team
        ball[0], ball[1] = at
        poss_key = team_key
        flip_blocked_until = -1e9
        flip_blocked_team = None
        carrier = _nearest(
            rng,
            squads[team_key],
            anchors,
            at,
            line_bonus={Position.MF: 6.0, Position.DF: 3.0},
        )

    def _flip_to(team_key: str, player: Player, clock: float) -> None:
        """Turnover: possession (and carrier) flips to the winner on the spot.

        The previous holder cannot win it straight back for a cooldown spell,
        which stops chain ping-pong without biasing either side.
        """
        nonlocal poss_key, carrier, flip_blocked_until, flip_blocked_team
        flip_blocked_team = poss_key
        flip_blocked_until = clock + FLIP_COOLDOWN_S
        poss_key = team_key
        carrier = player

    def _flip_allowed(clock: float, team_key: str) -> bool:
        """No instant re-flip to the previous holder; opening 90s always retain."""
        if clock < 90.0:
            return False
        return team_key != flip_blocked_team or clock >= flip_blocked_until

    def chain_pass(clock: float, minute: int, arc: str, aggressive: bool = False) -> dict:
        """One connected pass: carrier -> nearby teammate near a progressive target."""
        nonlocal carrier
        gx = goal_x_of(poss_key, minute)
        squad = squads[poss_key]
        ax = _to_attacking(ball[0], gx)
        direct = aggressive or counter_team(minute) == poss_key
        if ax < BUILDUP_AX:
            step, order = (7.0, 13.0), {Position.DF: 6.0, Position.MF: 4.0, Position.GK: 2.0}
        elif ax < CREATION_AX:
            step, order = (9.0, 17.0), {Position.MF: 6.0, Position.FW: 4.0, Position.DF: 2.0}
        else:
            step, order = (5.0, 11.0), {Position.FW: 8.0, Position.MF: 4.0}
        if direct:
            step = (step[0] + 4.0, step[1] + 6.0)
        pressed = pressing_team(minute) not in (None, poss_key)
        # Occasional circulation backwards in build-up instead of forcing forward.
        backpass = ax < 25.0 and rng.random() < 0.14
        if backpass:
            target_ax = max(6.0, ax - rng.uniform(4.0, 10.0))
            order = {Position.DF: 6.0, Position.GK: 4.0, Position.MF: 2.0}
        else:
            target_ax = min(93.0, ax + rng.uniform(*step))
        target_y = min(96.0, max(4.0, ball[1] + rng.uniform(-22.0, 22.0)))
        desired = _to_absolute(target_ax, target_y, gx)
        mates = [p for p in squad if p.id != carrier.id]
        if not backpass and ax > 40.0:
            mates = [p for p in mates if p.position != Position.GK] or mates
        target = (
            _nearest(
                rng,
                mates,
                anchors,
                desired,
                order,
                exclude={carrier.id},
                allow_gk=backpass,
            )
            if mates
            else carrier
        )
        landing = _jitter(rng, desired, 2.5)
        dx, dy = landing[0] - ball[0], landing[1] - ball[1]
        dist = math.hypot(dx, dy)
        if dist > 30.0:  # hard continuity cap: the receiver meets the ball shorter
            landing = (ball[0] + dx / dist * 30.0, ball[1] + dy / dist * 30.0)
            dist = 30.0
        spell_team = possession_spell_team(minute)
        press_side = pressing_team(minute)
        if spell_team == poss_key:
            complete_p = 0.90
        elif pressed:
            # Pressed but composed: circulate through the press, keep the ball.
            complete_p = 0.86
        elif press_side == poss_key:
            # Gegenpressing is rushed: won fast, played vertical, often lost,
            # so the presser duels plenty without hogging possession.
            complete_p = 0.50
        else:
            complete_p = 0.80
        roll = rng.random()
        outcome = (
            EventOutcome.COMPLETE
            if roll < complete_p
            else (EventOutcome.INCOMPLETE if roll < complete_p + 0.10 else EventOutcome.BLOCKED)
        )
        passer = carrier
        anchors[passer.id] = [ball[0], ball[1]]  # the passer was on the ball
        payload = {
            "type": EventType.PASS,
            "outcome": outcome,
            "player": passer,
            "target": target if outcome == EventOutcome.COMPLETE else None,
            "at": landing,
            "pass_distance": round(dist * PITCH_LENGTH_M / 100, 1),
            "pass_difficulty": round(min(0.95, dist / 60 + rng.uniform(0, 0.3)), 2),
            "ball_speed": round(rng.uniform(20, 60), 1),
            "arc": arc,
        }
        if outcome == EventOutcome.COMPLETE:
            ball[0], ball[1] = landing
            anchors[target.id] = [landing[0], landing[1]]  # receiver runs to meet it
            carrier = target
        elif outcome == EventOutcome.INCOMPLETE:
            # Overhit: a hunter collects on the move; dominant sides hunt in packs.
            share = _spell_share(minute)
            share = 0.5 if share is None else share
            other = "home" if rng.random() < share else "away"
            mid = ((ball[0] + landing[0]) / 2, (ball[1] + landing[1]) / 2)
            winner = _nearest(
                rng, squads[other], anchors, mid, {Position.DF: 5.0, Position.MF: 4.0}
            )
            ball[0], ball[1] = mid
            anchors[winner.id] = [mid[0], mid[1]]
            if other != poss_key and _flip_allowed(clock, other):
                _flip_to(other, winner, clock)
            else:  # same-team recovery
                mate = _nearest(rng, squads[poss_key], anchors, mid, {Position.MF: 5.0})
                anchors[mate.id] = [mid[0], mid[1]]
                carrier = mate
        else:  # BLOCKED: ball stays near the passer, usually turned over.
            ball[0], ball[1] = _jitter(rng, (ball[0], ball[1]), 2.0)
            anchors[passer.id] = [ball[0], ball[1]]
            share = _spell_share(minute)
            share = 0.5 if share is None else share
            other = "home" if rng.random() < share else "away"
            if other != poss_key and rng.random() < 0.7 and _flip_allowed(clock, other):
                winner = _nearest(
                    rng,
                    squads[other],
                    anchors,
                    (ball[0], ball[1]),
                    {Position.DF: 5.0, Position.MF: 3.0},
                )
                anchors[winner.id] = [ball[0], ball[1]]
                _flip_to(other, winner, clock)
        if outcome != EventOutcome.COMPLETE:
            # Marker follows the ball: incomplete/blocked balls die where they are,
            # not at the intended landing spot.
            payload["at"] = (ball[0], ball[1])
        return payload

    def duel_event(clock: float, minute: int, team_key: str, kind: EventType, arc: str) -> dict:
        """A duel involving the sampled team; won duels flip possession on the spot.

        The pressing side duels constantly but hurries into mistakes, so its
        win rate is lower than the pressed side's composure rate: volume without
        hoarding the ball.
        """
        nonlocal carrier
        spell_team = possession_spell_team(minute)
        press_side = pressing_team(minute)
        if press_side == team_key:
            win_p = 0.45
        elif press_side is not None:
            win_p = 0.65
        else:
            win_p = 0.72 if spell_team == team_key else 0.55
        won = rng.random() < win_p
        if kind == EventType.TACKLE:
            outcome = EventOutcome.WON if won else EventOutcome.LOST
        elif kind == EventType.INTERCEPTION:
            outcome = EventOutcome.SUCCESS if won else EventOutcome.NEUTRAL
        else:  # POSSESSION_CHANGE always resolves the duel
            outcome = EventOutcome.SUCCESS
            won = True
        if won and team_key != poss_key and _flip_allowed(clock, team_key):
            winner = _nearest(
                rng,
                squads[team_key],
                anchors,
                (ball[0], ball[1]),
                {Position.DF: 6.0, Position.MF: 4.0, Position.FW: 1.0},
            )
            at = _jitter(rng, (ball[0], ball[1]), 2.0 if kind == EventType.TACKLE else 1.0)
            ball[0], ball[1] = at
            anchors[winner.id] = [at[0], at[1]]  # winner was exactly there
            _flip_to(team_key, winner, clock)
            player = winner
        elif won or kind == EventType.POSSESSION_CHANGE:
            # Possessor rides the challenge (or recycles it): keep the ball with
            # one of their own. POSSESSION_CHANGE always resolves, no cooldown.
            if kind == EventType.POSSESSION_CHANGE and team_key != poss_key:
                winner = _nearest(
                    rng,
                    squads[team_key],
                    anchors,
                    (ball[0], ball[1]),
                    {Position.DF: 6.0, Position.MF: 4.0},
                )
                at = _jitter(rng, (ball[0], ball[1]), 1.0)
                ball[0], ball[1] = at
                anchors[winner.id] = [at[0], at[1]]
                _flip_to(team_key, winner, clock)
                player = winner
            else:
                player = (
                    carrier
                    if carrier in squads[team_key]
                    else _nearest(
                        rng,
                        squads[team_key],
                        anchors,
                        (ball[0], ball[1]),
                        {Position.DF: 5.0, Position.MF: 3.0},
                    )
                )
                at = _jitter(rng, (ball[0], ball[1]), 1.5)
                ball[0], ball[1] = at
                anchors[player.id] = [at[0], at[1]]
        else:
            # Beaten off the ball but it breaks loose nearby; possession holds.
            player = _nearest(
                rng,
                squads[team_key],
                anchors,
                (ball[0], ball[1]),
                {Position.DF: 5.0, Position.MF: 3.0},
            )
            at = _jitter(rng, (ball[0], ball[1]), 2.5)
            ball[0], ball[1] = at
            anchors[carrier.id] = [at[0], at[1]]
        return {"type": kind, "outcome": outcome, "player": player, "at": at, "arc": arc}

    def _pin_keeper(team_key: str, minute: int) -> None:
        """Keepers never roam: clamp their anchor inside their own box."""
        keeper = next(p for p in squads[team_key] if p.position == Position.GK)
        box_x = 100.0 - goal_x_of(team_key, minute)
        anchor = anchors[keeper.id]
        anchor[0] = min(99.0, max(1.0, min(max(anchor[0], box_x - 12.0), box_x + 12.0)))
        anchor[1] = min(75.0, max(25.0, anchor[1]))

    def shot_event(
        clock: float, minute: int, arc: str, header: bool = False
    ) -> tuple[dict, list[tuple[float, str, dict]]]:
        """A shot from the carrier (or nearest attacker); aftermath resolved inline.

        Returns (shot payload, extra dead-ball events). Extra offsets are scaled
        to the event pacing so sorted order matches generation order.
        """
        nonlocal carrier
        gx = goal_x_of(poss_key, minute)
        squad = squads[poss_key]
        if carrier.position not in (Position.FW, Position.MF):
            carrier = _nearest(
                rng,
                squad,
                anchors,
                (ball[0], ball[1]),
                {Position.FW: 8.0, Position.MF: 5.0},
                role_first=[Position.FW, Position.MF],
            )
        shooter = carrier
        anchors[shooter.id] = [ball[0], ball[1]]  # shot from where they stood
        shot_from: tuple[float, float] = (ball[0], ball[1])
        ex = gx - rng.uniform(1.0, 7.0) if gx == 100.0 else gx + rng.uniform(1.0, 7.0)
        ey = 50.0 + rng.uniform(-16.0, 16.0)
        flight = math.hypot(ex - ball[0], ey - ball[1])
        if flight > 60.0:  # even long shots stay on the same grid neighbourhood
            ex = ball[0] + (ex - ball[0]) / flight * 60.0
            ey = ball[1] + (ey - ball[1]) / flight * 60.0
            flight = 60.0
        dist = abs(gx - ball[0])
        xg = max(0.02, min(0.4, 0.35 - dist / 120 + rng.uniform(-0.03, 0.05)))
        if header:
            xg = round(max(0.03, xg * 0.6), 3)
        else:
            xg = round(xg, 3)
        outcome = rng.choices(
            [EventOutcome.SAVED, EventOutcome.BLOCKED, EventOutcome.OFF_TARGET],
            weights=[0.35, 0.3, 0.35],
        )[0]
        payload = {
            "type": EventType.SHOT,
            "outcome": outcome,
            "player": shooter,
            "at": (ex, ey),
            "at_from": shot_from,
            "shot_speed": round(rng.uniform(70, 130), 1),
            "xg": xg,
            "arc": arc,
        }
        other = "away" if poss_key == "home" else "home"
        extras: list[tuple[float, str, dict]] = []
        # Where the ball ends up if the keeper never claims it.
        mouth = _jitter(rng, (ex, ey), 4.0)
        if outcome == EventOutcome.SAVED and rng.random() < 0.65:
            # Rebound falls back into play; attackers react first.
            ball[0], ball[1] = _jitter(rng, (ex, ey), 6.0)
            carrier = _nearest(
                rng,
                squad,
                anchors,
                (ball[0], ball[1]),
                {Position.FW: 6.0, Position.MF: 4.0},
            )
            anchors[carrier.id] = [ball[0], ball[1]]
        elif outcome == EventOutcome.BLOCKED and rng.random() < 0.7 and _flip_allowed(clock, other):
            # Blocked en route: the ball dies where the defender stands.
            block_spot = (
                ball[0] + (mouth[0] - ball[0]) * rng.uniform(0.5, 0.8),
                ball[1] + (mouth[1] - ball[1]) * rng.uniform(0.5, 0.8),
            )
            blocker = _nearest(
                rng,
                squads[other],
                anchors,
                block_spot,
                {Position.DF: 6.0, Position.MF: 3.0},
            )
            ball[0], ball[1] = _jitter(rng, block_spot, 3.0)
            anchors[blocker.id] = [ball[0], ball[1]]
            _flip_to(other, blocker, clock)
        elif outcome == EventOutcome.SAVED and _flip_allowed(clock, other):
            # Defender collects the rebound at the mouth and clears the danger.
            defender = _nearest(
                rng,
                squads[other],
                anchors,
                (ex, ey),
                {Position.DF: 6.0, Position.GK: 4.0},
                allow_gk=True,
            )
            ball[0], ball[1] = _jitter(rng, (ex, ey), 5.0)
            anchors[defender.id] = [ball[0], ball[1]]
            _pin_keeper(other, minute)
            _flip_to(other, defender, clock)
        elif outcome == EventOutcome.SAVED:
            # Claimed under pressure: same keeper ball, no flip.
            ball[0], ball[1] = _jitter(rng, (ex, ey), 3.0)
            anchors[carrier.id] = [ball[0], ball[1]]
        else:  # OFF_TARGET or blocked-away: explicit goal kick, a dead-ball reset.
            keeper = next(p for p in squads[other] if p.position == Position.GK)
            kick = _jitter(rng, tuple(anchors[keeper.id]), 4.0)
            ball[0], ball[1] = kick
            anchors[keeper.id] = [kick[0], kick[1]]
            _pin_keeper(other, minute)
            _flip_to(other, keeper, clock)
            extras.append(
                (
                    step * rng.uniform(0.8, 1.3),
                    other,
                    {
                        "type": EventType.GOAL_KICK,
                        "outcome": EventOutcome.SUCCESS,
                        "player": keeper,
                        "at": kick,
                        "arc": arc,
                    },
                )
            )
        return payload, extras

    def corner_sequence(
        clock: float, minute: int, arc: str
    ) -> tuple[list[tuple[float, str, dict]], float]:
        """Corner swung in, then an immediate header or clearance.

        Returns (events, end_clock): the caller must advance past end_clock so
        aftermath never sorts before events generated after the corner.
        """
        nonlocal carrier
        attacking = poss_key
        gx = goal_x_of(attacking, minute)
        cx = gx - 3.0 if gx == 100.0 else gx + 3.0
        cy = 2.0 if rng.random() < 0.5 else 98.0
        taker = _nearest(
            rng,
            squads[attacking],
            anchors,
            (ball[0], ball[1]),
            {Position.MF: 6.0, Position.DF: 3.0},
        )
        corner = {
            "type": EventType.CORNER,
            "outcome": rng.choice([EventOutcome.COMPLETE, EventOutcome.INCOMPLETE]),
            "player": taker,
            "at": (cx, cy),
            "arc": arc,
        }
        ball[0], ball[1] = cx, cy
        carrier = taker
        anchors[taker.id] = [cx, cy]
        out = [(clock, attacking, corner)]
        header_t = clock + step * rng.uniform(0.8, 1.3)
        if rng.random() < 0.55:
            header, header_extras = shot_event(header_t, minute, arc, header=True)
            out.append((header_t, attacking, header))
            end = header_t
            for dt, owner, extra in header_extras:
                out.append((header_t + dt, owner, extra))
                end = header_t + dt
        else:
            # Cleared to midfield; second ball sampled by possession share.
            other = "away" if attacking == "home" else "home"
            winner_key = (
                attacking
                if rng.random() < (spell_share if (spell_share := _spell_share(minute)) else 0.5)
                else other
            )
            mid = _to_absolute(rng.uniform(38.0, 58.0), rng.uniform(25.0, 75.0), gx)
            winner = _nearest(
                rng, squads[winner_key], anchors, mid, {Position.MF: 6.0, Position.DF: 3.0}
            )
            ball[0], ball[1] = _jitter(rng, tuple(anchors[winner.id]), 3.0)
            anchors[winner.id] = [ball[0], ball[1]]
            _flip_to(winner_key, winner, clock)
            end = clock + step * rng.uniform(0.8, 1.3)
            out.append(
                (
                    end,
                    winner_key,
                    {
                        "type": EventType.POSSESSION_CHANGE,
                        "outcome": EventOutcome.SUCCESS,
                        "player": winner,
                        "at": (ball[0], ball[1]),
                        "arc": arc,
                    },
                )
            )
        return out, end

    def _spell_share(minute: int) -> float | None:
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        if not spell:
            return None
        return float(spell["share"]) if spell["team"] == "home" else 1.0 - float(spell["share"])

    def goal_sequence(
        goal_minute: int, goal_team: str, goal_t: float, clock: float
    ) -> tuple[float, int]:
        """Coherent 4-6 pass buildup from the live ball, ending in a box finish.

        Emits an interception to win the ball (if needed), 4-6 progressive
        passes toward the box, the GOAL at the scripted timestamp and a centre
        restart pass. Returns (new clock, events emitted). Every event starts
        where the previous one ended — no teleports, not even here.
        """
        nonlocal poss_key, carrier
        gx = goal_x_of(goal_team, goal_minute)
        arc = arc_label(goal_minute)
        n = rng.randint(4, 6)
        count = n + 2  # n passes + goal + restart
        start = max(clock, goal_t - (n + 1) * 5.0)
        if poss_key != goal_team:
            count += 1  # opening interception to win the ball
        if poss_key != goal_team:
            # Wins it back to launch the attack from the live ball position.
            winner = _nearest(
                rng,
                squads[goal_team],
                anchors,
                (ball[0], ball[1]),
                {Position.DF: 6.0, Position.MF: 4.0},
            )
            at = _jitter(rng, (ball[0], ball[1]), 2.0)
            ball[0], ball[1] = at
            anchors[winner.id] = [at[0], at[1]]
            _flip_to(goal_team, winner, clock)
            emit(
                start,
                goal_team,
                {
                    "type": EventType.INTERCEPTION,
                    "outcome": EventOutcome.SUCCESS,
                    "player": winner,
                    "at": at,
                    "arc": arc,
                },
            )
        # Walk the ball toward the box, one connected pass at a time.
        for i in range(n):
            t = start + (goal_t - start) * (i + 1) / (n + 1)
            ax = _to_attacking(ball[0], gx)
            frac = (i + 1) / (n + 1)
            target_ax = min(90.0, ax + (88.0 - ax) * frac + rng.uniform(-2.0, 2.0))
            target_y = min(
                96.0, max(4.0, 50.0 + (ball[1] - 50.0) * (1 - frac) + rng.uniform(-8, 8))
            )
            desired = _to_absolute(target_ax, target_y, gx)
            order: dict[Position, float] = (
                {Position.FW: 8.0, Position.MF: 5.0}
                if i >= n - 2
                else {Position.MF: 6.0, Position.FW: 4.0, Position.DF: 2.0}
            )
            target = _nearest(rng, squads[goal_team], anchors, desired, order, exclude={carrier.id})
            landing = _jitter(rng, desired, 2.0)
            dx, dy = landing[0] - ball[0], landing[1] - ball[1]
            dist = math.hypot(dx, dy)
            if dist > 30.0:
                landing = (ball[0] + dx / dist * 30.0, ball[1] + dy / dist * 30.0)
                dist = 30.0
            passer = carrier
            anchors[passer.id] = [ball[0], ball[1]]
            emit(
                t,
                goal_team,
                {
                    "type": EventType.PASS,
                    "outcome": EventOutcome.COMPLETE,
                    "player": passer,
                    "target": target,
                    "at": landing,
                    "pass_distance": round(dist * PITCH_LENGTH_M / 100, 1),
                    "pass_difficulty": round(min(0.95, dist / 60 + rng.uniform(0, 0.3)), 2),
                    "ball_speed": round(rng.uniform(20, 60), 1),
                    "arc": arc,
                },
            )
            ball[0], ball[1] = landing
            anchors[target.id] = [landing[0], landing[1]]
            carrier = target
        scorer = (
            carrier
            if carrier.position == Position.FW
            else _nearest(
                rng,
                squads[goal_team],
                anchors,
                (ball[0], ball[1]),
                {Position.FW: 9.0},
                role_first=[Position.FW, Position.MF],
            )
        )
        carrier = scorer
        spot = (
            min(99.0, max(93.0, gx - rng.uniform(1.0, 6.0)))
            if gx == 100.0
            else min(7.0, max(1.0, gx + rng.uniform(1.0, 6.0))),
            min(96.0, max(4.0, ball[1] + rng.uniform(-8.0, 8.0))),
        )
        origin = (ball[0], ball[1])
        ball[0], ball[1] = spot
        anchors[scorer.id] = [spot[0], spot[1]]
        emit(
            goal_t,
            goal_team,
            {
                "type": EventType.GOAL,
                "outcome": EventOutcome.GOAL,
                "player": scorer,
                "at": spot,
                "at_from": origin,
                "xg": round(rng.uniform(0.25, 0.65), 3),
                "shot_speed": round(rng.uniform(75, 125), 1),
                "arc": "goal",
            },
        )
        # Centre restart by the conceding side: visible anchor, no teleport.
        conceding = "away" if goal_team == "home" else "home"
        restarter = _nearest(
            rng, squads[conceding], anchors, (50.0, 50.0), {Position.MF: 6.0, Position.DF: 3.0}
        )
        mate = _nearest(
            rng,
            squads[conceding],
            anchors,
            (54.0, 48.0),
            {Position.MF: 6.0, Position.FW: 3.0},
            exclude={restarter.id},
        )
        at_restart = _jitter(rng, (52.0, 49.0), 2.5)
        anchors[restarter.id] = [50.0, 50.0]
        anchors[mate.id] = [at_restart[0], at_restart[1]]
        emit(
            goal_t + 3.0,
            conceding,
            {
                "type": EventType.PASS,
                "outcome": EventOutcome.COMPLETE,
                "player": restarter,
                "target": mate,
                "at": at_restart,
                "pass_distance": round(
                    math.hypot(at_restart[0] - 50.0, at_restart[1] - 50.0) * PITCH_LENGTH_M / 100, 1
                ),
                "pass_difficulty": 0.1,
                "ball_speed": 25.0,
                "arc": "restart",
            },
        )
        ball[0], ball[1] = at_restart
        _flip_to(conceding, mate, clock)
        return goal_t + 3.0 + rng.uniform(1.0, 4.0), count

    # Opening kickoff.
    emit(0.0, "home", {"type": EventType.KICKOFF, "outcome": EventOutcome.NEUTRAL})

    step = 5390.0 / max(1, n_ball)  # per-event pacing covers the full 90
    clock = 5.0
    sub_idx = 0
    goal_idx = 0
    pending_goals = sorted(goals)
    # Deterministic scripted timestamps, fixed before the loop consumes rng.
    goal_times = {i: m * 60 + rng.randint(0, 59) for i, (m, _) in enumerate(pending_goals)}
    last_goal: tuple[int, str] | None = None
    built: set[int] = set()
    crossed_half = False

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
            anchors[on.id] = anchors.pop(off.id)
            if carrier.id == off.id:
                carrier = on
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

        # Second-half reset: sides switch, away restarts from the centre.
        if not crossed_half and clock >= 46 * 60:
            crossed_half = True
            anchors.update(_anchor_grid(home.roster[:11], mirror=True))
            anchors.update(_anchor_grid(away.roster[:11], mirror=False))
            for _team_key, starters in (("home", home.roster[:11]), ("away", away.roster[:11])):
                for player in starters:
                    if player.id not in anchors:
                        anchors[player.id] = [50.0, 50.0]
            reset_chain("away", (50.0, 50.0))
            restart_at = _jitter(rng, (53.0, 49.0), 2.0)
            restart_mate = _nearest(
                rng, squads["away"], anchors, restart_at, {Position.MF: 6.0, Position.FW: 3.0}
            )
            anchors[carrier.id] = [50.0, 50.0]
            anchors[restart_mate.id] = [restart_at[0], restart_at[1]]
            emit(
                clock,
                "away",  # current clock: fixed stamps would sort out of order
                {
                    "type": EventType.PASS,
                    "outcome": EventOutcome.COMPLETE,
                    "player": carrier,
                    "target": restart_mate,
                    "at": restart_at,
                    "pass_distance": 4.0,
                    "pass_difficulty": 0.1,
                    "ball_speed": 25.0,
                    "arc": "restart",
                },
            )
            ball[0], ball[1] = restart_at
            carrier = restart_mate
            emitted += 1

        # Scripted goal: grow a coherent buildup from the live ball position.
        if goal_idx < len(pending_goals) and goal_idx not in built:
            g_minute, g_team = pending_goals[goal_idx]
            if clock >= goal_times[goal_idx] - 30:
                built.add(goal_idx)
                clock, n_done = goal_sequence(g_minute, g_team, goal_times[goal_idx], clock)
                emitted += n_done
                last_goal = (g_minute, g_team)
                goal_idx += 1
                continue
        # Safety net: never lose a scripted beat if the clock ever jumps it.
        while goal_idx < len(pending_goals) and pending_goals[goal_idx][0] < minute:
            if goal_idx not in built:
                g_minute, g_team = pending_goals[goal_idx]
                built.add(goal_idx)
                clock, n_done = goal_sequence(g_minute, g_team, max(clock, g_minute * 60), clock)
                emitted += n_done
                last_goal = (g_minute, g_team)
            goal_idx += 1

        weights = dict(BASE_WEIGHTS)
        press = _active_spell(scenario_dict.get("press_spells", []), minute)
        counter = _active_spell(scenario_dict.get("counter_bursts", []), minute)
        spell = _active_spell(scenario_dict.get("possession_spells", []), minute)
        home_share = 0.5
        if spell:
            home_share = spell["share"] if spell["team"] == "home" else 1 - spell["share"]
        if press:
            # Off-ball hunting surges the moment the press triggers (no flips,
            # so the ball doesn't move — only the duel count explodes).
            onset = 1.8 if minute - int(press["start_minute"]) <= 3 else 1.0
            weights[EventType.PRESSURE] *= 2.2 * onset
            weights[EventType.TACKLE] *= 1.8
            weights[EventType.INTERCEPTION] *= 1.7
            weights[EventType.FOUL] *= 1.6
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
        # Acting team for duels and off-ball events; the chain owns passes/shots.
        # The pressing side hunts in packs: duels tilt toward it during its spell.
        press_side = str(press["team"]) if press else None
        if press_side is not None:
            duel_key = (
                press_side if rng.random() < 0.55 else ("away" if press_side == "home" else "home")
            )
        else:
            tilt = min(0.85, max(0.15, 0.5 + (home_share - 0.5) * 1.6))
            duel_key = "home" if rng.random() < tilt else "away"
        team_key = duel_key
        kind = rng.choices(list(weights), weights=list(weights.values()))[0]
        arc = arc_label(minute)
        emitted_before = emitted
        if kind == EventType.PASS:
            owner = poss_key  # capture before the builder may flip possession
            emit(clock, owner, chain_pass(clock, minute, arc))
            emitted += 1
            clock += rng.uniform(0.4, 1.6) * step
        elif kind == EventType.SHOT:
            if _to_attacking(ball[0], goal_x_of(poss_key, minute)) >= SHOT_MIN_AX:
                owner = poss_key  # the shooter’s side; aftermath flips come after
                payload, extras = shot_event(clock, minute, arc)
                emit(clock, owner, payload)
                emitted += 1
                for dt, extra_owner, extra in extras:
                    emit(clock + dt, extra_owner, extra)
                    emitted += 1
            else:  # out of range: keep circulating instead of forcing it
                emit(clock, poss_key, chain_pass(clock, minute, arc))
                emitted += 1
            # One clock step per emitted event so multi-emit iterations
            # don't starve the clock (which would cut the match short).
            clock += rng.uniform(0.4, 1.6) * step * max(1, emitted - emitted_before)
        elif kind == EventType.CORNER:
            seq, end = corner_sequence(clock, minute, arc)
            for t, owner, payload in seq:
                emit(t, owner, payload)
                emitted += 1
            clock = end + rng.uniform(0.4, 1.6) * step * max(1, emitted - emitted_before)
        elif kind in (EventType.TACKLE, EventType.INTERCEPTION, EventType.POSSESSION_CHANGE):
            emit(clock, team_key, duel_event(clock, minute, team_key, kind, arc))
            emitted += 1
            clock += rng.uniform(0.4, 1.6) * step
        elif kind == EventType.PRESSURE:
            presser = _nearest(
                rng,
                squads[team_key],
                anchors,
                (ball[0], ball[1]),
                {Position.DF: 4.0, Position.MF: 3.0, Position.FW: 2.0},
            )
            ball[0], ball[1] = _jitter(rng, (ball[0], ball[1]), 2.0)
            emit(
                clock,
                team_key,
                {
                    "type": kind,
                    "outcome": rng.choice([EventOutcome.SUCCESS, EventOutcome.NEUTRAL]),
                    "player": presser,
                    "at": (ball[0], ball[1]),
                    "arc": arc,
                },
            )
            emitted += 1
            clock += rng.uniform(0.4, 1.6) * step
        else:  # FOUL: stoppage, ball stays, possession retained.
            committer = _nearest(
                rng,
                squads[team_key],
                anchors,
                (ball[0], ball[1]),
                {Position.DF: 5.0, Position.MF: 3.0},
            )
            emit(
                clock,
                team_key,
                {
                    "type": kind,
                    "outcome": EventOutcome.NEUTRAL,
                    "player": committer,
                    "at": (ball[0], ball[1]),
                    "arc": arc,
                },
            )
            emitted += 1
            clock += rng.uniform(0.4, 1.6) * step

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

    # All goals were built inline with coherent lead-ups; only the fixed
    # clock markers remain.
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
                    **({"from": list(payload["at_from"])} if "at_from" in payload else {}),
                },
            )
        )
    return MatchData(meta=meta, events=events)


def save_match(match: MatchData, path: str | Path) -> Path:
    """Write a match to JSON and return the path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(match.model_dump_json(indent=1), encoding="utf-8")
    return target


def load_match(path: str | Path) -> MatchData:
    """Read a match JSON file back into a validated MatchData."""
    return MatchData.model_validate_json(Path(path).read_text(encoding="utf-8"))
