"""Output schemas for the Phase 2 deterministic analytics engine.

Every insight carries an ``evidence`` payload with the exact numbers that
justify it, so Phase 3 agents can only explain what the engine measured.
Zero LLM involved: pure data containers.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

MomentType = Literal["goal", "big_chance", "pressure_spike", "momentum_swing", "tactical_shift"]

SegmentLabel = Literal["control", "high_press", "tactical_shift", "momentum_swing", "balanced"]


class TeamWindow(BaseModel):
    """One team's stats inside a rolling window."""

    team_id: str
    possession_pct: float = Field(ge=0, le=100)
    pass_accuracy_pct: float = Field(ge=0, le=100)
    pressure_events: int = Field(ge=0)
    high_turnovers: int = Field(ge=0)
    xg_sum: float = Field(ge=0)


class WindowStats(BaseModel):
    """Rolling-window snapshot for all teams at one point in time."""

    window_minutes: int
    end_timestamp_s: float
    end_minute: int
    tempo_per_min: float = Field(ge=0)
    teams: dict[str, TeamWindow]
    momentum: dict[str, float] = Field(description="Momentum index per team, -100..100 (zero-sum).")


class Moment(BaseModel):
    """A detected key moment with its numeric evidence payload."""

    id: str
    type: MomentType
    minute: int
    timestamp_s: float
    team_id: str | None = None
    title: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class Segment(BaseModel):
    """One labelled match phase with start/end minutes and evidence."""

    label: SegmentLabel
    team_id: str | None = None
    start_minute: int
    end_minute: int
    title: str
    evidence: dict[str, Any] = Field(default_factory=dict)
