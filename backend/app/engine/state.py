"""Deterministic analytics engine: rolling windows and momentum (Phase 2).

Zero LLM. Pure incremental math over the synthetic event stream.
"""

from collections import deque

from app.engine.schemas import TeamWindow, WindowStats
from app.models.events import Event, EventType

#: Rolling windows (minutes) maintained by the engine.
WINDOWS = (1, 5, 10)

#: Event types counted as defending-pressure actions.
PRESSURE_TYPES = frozenset({EventType.PRESSURE, EventType.TACKLE, EventType.INTERCEPTION})

#: Event types that can win the ball back.
TURNOVER_TYPES = frozenset({EventType.TACKLE, EventType.INTERCEPTION, EventType.POSSESSION_CHANGE})

#: Outcomes meaning the duel was won.
WON_OUTCOMES = frozenset({"won", "success"})

#: Shot-like types carrying xG.
SHOT_TYPES = frozenset({EventType.SHOT, EventType.GOAL})

#: Goal-boost strength and decay horizon (seconds) for the momentum index.
GOAL_BOOST = 25.0
GOAL_DECAY_S = 600.0


def attack_x(team_id: str, period: int, home_id: str, away_id: str) -> float:
    """Return the x coordinate a team attacks (sides switch at half-time)."""
    if team_id == home_id:
        return 100.0 if period == 1 else 0.0
    if team_id == away_id:
        return 0.0 if period == 1 else 100.0
    return 100.0


def in_opponent_half(event: Event, home_id: str, away_id: str) -> bool:
    """Check whether an event happened in the team's attacking (opponent) half."""
    goal_x = attack_x(event.team_id or "", event.period, home_id, away_id)
    return event.x > 50 if goal_x == 100.0 else event.x < 50


class MatchState:
    """Incremental match state, updated event by event.

    Keeps the trailing 10 minutes of events plus score and last-goal
    bookkeeping. All window stats derive from this single state object,
    so live and batch processing agree exactly.
    """

    def __init__(self, home_id: str, away_id: str) -> None:
        self.home_id = home_id
        self.away_id = away_id
        self._events: deque[Event] = deque()
        self.score: dict[str, int] = {home_id: 0, away_id: 0}
        self.last_goal: tuple[float, str] | None = None
        self.processed = 0
        self.now_s = 0.0

    def update(self, event: Event) -> None:
        """Fold one event into the state (must arrive in timestamp order)."""
        self._events.append(event)
        self.now_s = event.timestamp_s
        self.processed += 1
        horizon = self.now_s - (max(WINDOWS) * 60 + 1)
        while self._events and self._events[0].timestamp_s <= horizon:
            self._events.popleft()
        if event.type == EventType.GOAL and event.team_id:
            self.score[event.team_id] = self.score.get(event.team_id, 0) + 1
            self.last_goal = (event.timestamp_s, event.team_id)

    def _in_window(self, minutes: int, now: float) -> list[Event]:
        cutoff = now - minutes * 60
        return [e for e in self._events if e.timestamp_s > cutoff]

    def window_stats(self, minutes: int, now: float | None = None) -> WindowStats:
        """Compute rolling-window stats ending at ``now`` (default: last event)."""
        at = self.now_s if now is None else now
        events = self._in_window(minutes, at)
        teams: dict[str, TeamWindow] = {}
        total_passes = 0
        team_passes: dict[str, int] = {}
        for team_id in (self.home_id, self.away_id):
            own = [e for e in events if e.team_id == team_id]
            passes = [e for e in own if e.type == EventType.PASS]
            complete = [e for e in passes if e.outcome.value == "complete"]
            pressure = [e for e in own if e.type in PRESSURE_TYPES]
            turnovers = [
                e
                for e in own
                if e.type in TURNOVER_TYPES
                and e.outcome.value in WON_OUTCOMES
                and in_opponent_half(e, self.home_id, self.away_id)
            ]
            xg = sum(e.xg or 0.0 for e in own if e.type in SHOT_TYPES)
            total_passes += len(passes)
            team_passes[team_id] = len(passes)
            teams[team_id] = TeamWindow(
                team_id=team_id,
                possession_pct=0.0,  # filled below once the total is known
                pass_accuracy_pct=(len(complete) / len(passes) * 100) if passes else 0.0,
                pressure_events=len(pressure),
                high_turnovers=len(turnovers),
                xg_sum=round(xg, 3),
            )
        for team_id, stats in teams.items():
            stats.possession_pct = (
                round(team_passes[team_id] / total_passes * 100, 1) if total_passes else 50.0
            )
        home = teams[self.home_id]
        away = teams[self.away_id]
        momentum_home = self._momentum(home, away, at)
        minute = min(90, int(at // 60))
        return WindowStats(
            window_minutes=minutes,
            end_timestamp_s=at,
            end_minute=minute,
            tempo_per_min=round(len(events) / minutes, 2),
            teams=teams,
            momentum={
                self.home_id: momentum_home,
                self.away_id: round(-momentum_home, 2),
            },
        )

    def _momentum(self, home: TeamWindow, away: TeamWindow, at: float) -> float:
        """Zero-sum momentum index (home perspective), -100..100.

        Combines possession share, shot-quality edge and pressure edge over the
        window, plus a decaying boost for the last goalscorer.
        """
        value = (home.possession_pct - 50.0) * 1.2
        value += max(-25.0, min(25.0, (home.xg_sum - away.xg_sum) * 50.0))
        value += max(-15.0, min(15.0, (home.pressure_events - away.pressure_events) * 1.5))
        if self.last_goal is not None:
            goal_ts, scorer = self.last_goal
            age = at - goal_ts
            if 0 <= age <= GOAL_DECAY_S:
                boost = GOAL_BOOST * (1 - age / GOAL_DECAY_S)
                value += boost if scorer == self.home_id else -boost
        return round(max(-100.0, min(100.0, value)), 2)

    def momentum_now(self) -> dict[str, float]:
        """Current 5-minute momentum per team."""
        return self.window_stats(5).momentum
