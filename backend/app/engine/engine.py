"""Key-moment detectors over the incremental engine state (Phase 2).

Zero LLM. Each detector is a pure rule with a numeric threshold; every fired
moment carries the exact evidence numbers a Phase 3 agent may later explain.
"""

from app.engine.schemas import Moment, WindowStats
from app.engine.state import GOAL_BOOST, MatchState
from app.models.events import Event, EventType

#: A shot (or goal) with at least this synthetic xG is a big chance
#: (roughly a 1-in-4 chance; scripted demo goals fall in 0.15-0.65).
BIG_CHANCE_XG = 0.25

#: Team pressure actions in the trailing 5 minutes that open a spike.
PRESSURE_SPIKE_COUNT = 14
PRESSURE_COOLDOWN_MIN = 5

#: |momentum| at or beyond this means a side is firmly on top (goal rule).
MOMENTUM_STRONG = 25.0

#: |momentum| below this margin counts as "no leader" for lead flips.
MOMENTUM_LEAD_MARGIN = 10.0
SWING_COOLDOWN_MIN = 3

#: Minimum events in the trailing 5-minute window before swings may fire
#: (suppresses noise in the opening minutes).
SWING_MIN_EVENTS = 10


class AnalyticsEngine:
    """Incremental analytics: feed events in order, collect moments.

    The engine is the single live path — there is no separate batch mode, so
    streaming and file analysis always agree.
    """

    def __init__(
        self,
        home_id: str,
        away_id: str,
        team_names: dict[str, str] | None = None,
    ) -> None:
        self.state = MatchState(home_id, away_id)
        self.names = team_names or {}
        self.moments: list[Moment] = []
        self.samples: dict[int, WindowStats] = {}
        self._moment_seq = 0
        self._last_spike_minute: dict[str, float] = {}
        self._lead: str | None = None
        self._prev_momentum_home: float | None = None
        self._last_swing_minute: float | None = None

    def _name(self, team_id: str | None) -> str:
        if team_id is None:
            return "-"
        return self.names.get(team_id, team_id)

    def _next_id(self) -> str:
        self._moment_seq += 1
        return f"m{self._moment_seq:04d}"

    def update(self, event: Event) -> list[Moment]:
        """Fold one event into the state and return newly fired moments."""
        self.state.update(event)
        fired: list[Moment] = []
        stats5 = self.state.window_stats(5)
        momentum_home = stats5.momentum[self.state.home_id]

        goal = self._detect_goal(event)
        if goal is not None:
            fired.append(goal)
        chance = self._detect_big_chance(event)
        if chance is not None:
            fired.append(chance)
        fired.extend(self._detect_pressure_spikes(event, stats5))
        swing = self._detect_swing(event, stats5, momentum_home)
        if swing is not None:
            fired.append(swing)
        shift = self._detect_shift(event)
        if shift is not None:
            fired.append(shift)

        for moment in fired:
            self.moments.append(moment)
        # Last snapshot of each minute wins: end-of-minute state, deterministic.
        self.samples[event.minute] = stats5
        self._prev_momentum_home = momentum_home
        return fired

    def _detect_goal(self, event: Event) -> Moment | None:
        if event.type != EventType.GOAL or not event.team_id:
            return None
        score = self.state.score
        return Moment(
            id=self._next_id(),
            type="goal",
            minute=event.minute,
            timestamp_s=event.timestamp_s,
            team_id=event.team_id,
            title=f"GOAL {self._name(event.team_id)} ({self._name(event.player_id)})",
            evidence={
                "scorer": event.player_id,
                "xg": event.xg,
                "score_home": score[self.state.home_id],
                "score_away": score[self.state.away_id],
                "score": f"{score[self.state.home_id]}-{score[self.state.away_id]}",
            },
        )

    def _detect_big_chance(self, event: Event) -> Moment | None:
        if event.type not in (EventType.SHOT, EventType.GOAL):
            return None
        if event.xg is None or event.xg < BIG_CHANCE_XG:
            return None
        return Moment(
            id=self._next_id(),
            type="big_chance",
            minute=event.minute,
            timestamp_s=event.timestamp_s,
            team_id=event.team_id,
            title=f"Big chance {self._name(event.team_id)} xG {event.xg:.2f}",
            evidence={
                "player": event.player_id,
                "xg": event.xg,
                "event_type": event.type.value,
                "threshold": BIG_CHANCE_XG,
            },
        )

    def _detect_pressure_spikes(self, event: Event, stats5: WindowStats) -> list[Moment]:
        moments: list[Moment] = []
        for team_id in (self.state.home_id, self.state.away_id):
            count = stats5.teams[team_id].pressure_events
            if count < PRESSURE_SPIKE_COUNT:
                continue
            last = self._last_spike_minute.get(team_id)
            if last is not None and event.minute - last < PRESSURE_COOLDOWN_MIN:
                continue
            self._last_spike_minute[team_id] = event.minute
            other = self.state.away_id if team_id == self.state.home_id else self.state.home_id
            moments.append(
                Moment(
                    id=self._next_id(),
                    type="pressure_spike",
                    minute=event.minute,
                    timestamp_s=event.timestamp_s,
                    team_id=team_id,
                    title=f"High press {self._name(team_id)} ({count} duels/5min)",
                    evidence={
                        "pressure_events": count,
                        "opponent_pressure_events": stats5.teams[other].pressure_events,
                        "window_minutes": 5,
                        "threshold": PRESSURE_SPIKE_COUNT,
                    },
                )
            )
        return moments

    def _detect_swing(
        self, event: Event, stats5: WindowStats, momentum_home: float
    ) -> Moment | None:
        """Fire when the lead flips or a goal transforms the game state.

        A goal counts as a swing when the scorer was not already firmly on top
        (|momentum| below the strong threshold before the goal boost); goals
        scored while already dominant merely consolidate, not swing.
        """
        window_count = round(stats5.tempo_per_min * stats5.window_minutes)
        if window_count < SWING_MIN_EVENTS:
            return None
        gained: str | None = None
        before: float | None = None
        if event.type == EventType.GOAL and event.team_id:
            pre = (
                momentum_home - GOAL_BOOST
                if event.team_id == self.state.home_id
                else momentum_home + GOAL_BOOST
            )
            if event.team_id == self.state.home_id and pre < MOMENTUM_STRONG:
                gained, before = event.team_id, pre
            elif event.team_id != self.state.home_id and pre > -MOMENTUM_STRONG:
                gained, before = event.team_id, pre
        else:
            lead: str | None = None
            if momentum_home >= MOMENTUM_LEAD_MARGIN:
                lead = self.state.home_id
            elif momentum_home <= -MOMENTUM_LEAD_MARGIN:
                lead = self.state.away_id
            if lead is not None:
                if self._lead is not None and lead != self._lead:
                    gained = lead
                    before = self._prev_momentum_home
                self._lead = lead
            if gained is None:
                return None
        if gained is None:
            return None
        if (
            self._last_swing_minute is not None
            and event.minute - self._last_swing_minute < SWING_COOLDOWN_MIN
        ):
            return None
        self._last_swing_minute = event.minute
        self._lead = gained
        return Moment(
            id=self._next_id(),
            type="momentum_swing",
            minute=event.minute,
            timestamp_s=event.timestamp_s,
            team_id=gained,
            title=f"Momentum swing to {self._name(gained)} ({momentum_home:+.0f})",
            evidence={
                "momentum_home_before": round(before, 2) if before is not None else None,
                "momentum_home_after": momentum_home,
                "strong_threshold": MOMENTUM_STRONG,
            },
        )

    def _detect_shift(self, event: Event) -> Moment | None:
        if event.type != EventType.SUBSTITUTION or not event.team_id:
            return None
        return Moment(
            id=self._next_id(),
            type="tactical_shift",
            minute=event.minute,
            timestamp_s=event.timestamp_s,
            team_id=event.team_id,
            title=f"Tactical shift {self._name(event.team_id)} "
            f"({self._name(event.player_id)} -> {self._name(event.target_player_id)})",
            evidence={
                "player_off": event.player_id,
                "player_on": event.target_player_id,
            },
        )
