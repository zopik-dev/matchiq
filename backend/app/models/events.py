"""Pydantic v2 schema for MatchIQ synthetic match events.

All clubs, players and stadiums are invented. The pitch is a 0-100 grid in both
axes; the team attacking the own goal at ``x=0`` defends that end.

Conventions used by the generator and replay engine:

- ``minute`` is the global match minute (0-90). ``period`` is 1 for 0-45,
  2 for 46-90.
- ``timestamp_s`` is seconds since kickoff and must stay close to
  ``minute * 60 + second`` (a small slack allows stoppage time).
- ``xg`` is a synthetic expected-goals value carried only by ``shot`` and
  ``goal`` events; every other event type must leave it as ``None``.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EventType(StrEnum):
    """Allowed synthetic event types."""

    PASS = "pass"
    SHOT = "shot"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    POSSESSION_CHANGE = "possession_change"
    PRESSURE = "pressure"
    FOUL = "foul"
    CORNER = "corner"
    GOAL = "goal"
    SUBSTITUTION = "substitution"
    KICKOFF = "kickoff"
    HALF_TIME = "half_time"
    FULL_TIME = "full_time"


class EventOutcome(StrEnum):
    """Allowed outcome labels for events."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"
    SAVED = "saved"
    GOAL = "goal"
    OFF_TARGET = "off_target"
    WON = "won"
    LOST = "lost"
    SUCCESS = "success"
    NEUTRAL = "neutral"


class Position(StrEnum):
    """Simplified player positions."""

    GK = "GK"
    DF = "DF"
    MF = "MF"
    FW = "FW"


#: Events that describe the match clock rather than on-ball action.
SYSTEM_EVENTS = frozenset({EventType.KICKOFF, EventType.HALF_TIME, EventType.FULL_TIME})

#: Slack (seconds) between timestamp_s and minute*60+second for stoppage time.
TIMESTAMP_SLACK_S = 600.0

#: Full-time in seconds for a 90-minute match without stoppage.
FULL_TIME_S = 90 * 60


class Event(BaseModel):
    """A single synthetic match event on the 0-100 pitch grid."""

    event_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    period: Literal[1, 2]
    minute: int = Field(ge=0, le=90)
    second: int = Field(ge=0, le=59)
    timestamp_s: float = Field(ge=0, le=FULL_TIME_S + TIMESTAMP_SLACK_S)
    type: EventType
    team_id: str | None = None
    player_id: str | None = None
    target_player_id: str | None = None
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    outcome: EventOutcome
    pass_distance_m: float | None = Field(default=None, ge=0, le=120)
    pass_difficulty: float | None = Field(default=None, ge=0, le=1)
    ball_speed_kmh: float | None = Field(default=None, ge=0, le=160)
    shot_speed_kmh: float | None = Field(default=None, ge=0, le=160)
    xg: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("team_id", "player_id", "target_player_id")
    @classmethod
    def _non_empty_ids(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("id fields must be non-empty when provided")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> "Event":
        expected_period: Literal[1, 2] = 1 if self.minute <= 45 else 2
        if self.period != expected_period:
            raise ValueError(f"period {self.period} inconsistent with minute {self.minute}")
        clock = self.minute * 60 + self.second
        if abs(self.timestamp_s - clock) > TIMESTAMP_SLACK_S:
            raise ValueError(
                f"timestamp_s {self.timestamp_s} too far from minute/second clock {clock}"
            )
        if self.type in SYSTEM_EVENTS:
            return self
        if not self.team_id:
            raise ValueError(f"event type '{self.type.value}' requires team_id")
        if not self.player_id and self.type != EventType.SUBSTITUTION:
            raise ValueError(f"event type '{self.type.value}' requires player_id")
        if self.type in (EventType.SHOT, EventType.GOAL):
            return self
        if self.xg is not None:
            raise ValueError(f"xg is only allowed on shot/goal, got {self.type.value}")
        return self


class Player(BaseModel):
    """A single invented player in a team roster."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    number: int = Field(ge=1, le=99)
    position: Position


class Team(BaseModel):
    """An invented team with formation and roster."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    formation: str = Field(min_length=1)
    roster: list[Player] = Field(min_length=11)

    @field_validator("roster")
    @classmethod
    def _unique_numbers(cls, roster: list[Player]) -> list[Player]:
        numbers = [p.number for p in roster]
        if len(set(numbers)) != len(numbers):
            raise ValueError("shirt numbers must be unique within a team")
        ids = [p.id for p in roster]
        if len(set(ids)) != len(ids):
            raise ValueError("player ids must be unique within a team")
        return roster


class MatchMeta(BaseModel):
    """Match-level metadata: invented teams, stadium and kickoff time."""

    match_id: str = Field(min_length=1)
    teams: list[Team] = Field(min_length=2, max_length=2)
    stadium: str = Field(min_length=1)
    kickoff_time: datetime

    @field_validator("teams")
    @classmethod
    def _distinct_teams(cls, teams: list[Team]) -> list[Team]:
        if teams[0].id == teams[1].id:
            raise ValueError("the two teams must have distinct ids")
        return teams

    def display_names(self) -> dict[str, str]:
        """Map every team AND player id to its display name for user-facing text.

        Evidence payloads keep raw ids (stable keys for grounding); only
        rendered strings resolve through this map, with raw-id fallback.
        """
        names = {team.id: team.name for team in self.teams}
        for team in self.teams:
            for player in team.roster:
                names[player.id] = player.name
        return names


class MatchData(BaseModel):
    """A full synthetic match: metadata plus ordered events."""

    meta: MatchMeta
    events: list[Event] = Field(min_length=1)
