"""Typed message contracts and handoff trace for the agent pipeline (Phase 3)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["event", "context", "explain", "story", "personalize", "pipeline"]

MessageKind = Literal[
    "event.validated",
    "context.attached",
    "explanation",
    "story.line",
    "story.recap",
    "personalized",
]


class AgentMessage(BaseModel):
    """One typed handoff between agents; evidence always rides along."""

    id: str
    kind: MessageKind
    sender: AgentName
    moment_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class Handoff(BaseModel):
    """One trace-log entry for an agent call (inspectable pipeline flow)."""

    seq: int
    sender: AgentName
    receiver: AgentName
    message_id: str
    attempts: int = 1
    ok: bool = True
    degraded: bool = False
    error: str | None = None


class PersonalizeProfile(BaseModel):
    """Output preferences for the PersonalizeAgent."""

    mode: Literal["analyst", "fan", "beginner"] = "fan"
    language: Literal["en", "uk"] = "en"
    favorite_club: str | None = None
    player_focus: str | None = None
