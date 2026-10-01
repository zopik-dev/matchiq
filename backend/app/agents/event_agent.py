"""EventAgent: validate and parse incoming streaming events (Phase 3)."""

from typing import Any

from pydantic import ValidationError

from app.agents.messages import AgentMessage
from app.models.events import Event


class EventAgent:
    """Gatekeeper: raw dicts in, validated Event messages out."""

    name = "event"

    def handle(self, raw: dict[str, Any], message_id: str) -> AgentMessage:
        try:
            event = Event(**raw) if not isinstance(raw, Event) else raw
        except ValidationError as exc:
            raise ValueError(f"invalid event: {exc}") from exc
        return AgentMessage(
            id=message_id,
            kind="event.validated",
            sender="event",
            payload={"event": event.model_dump(mode="json")},
            evidence={},
        )
