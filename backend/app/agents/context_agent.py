"""ContextAgent: attach engine metrics and storyline context (Phase 3).

Pure code, no LLM. Joins the live 5-minute window snapshot, momentum, score
and the storyline segment covering the moment's minute.
"""

from app.agents.messages import AgentMessage
from app.engine.schemas import Moment, Segment, WindowStats


class ContextAgent:
    """Enrich a fired moment with engine numbers for downstream agents."""

    name = "context"

    def handle(
        self,
        moment: Moment,
        stats: WindowStats,
        score: dict[str, int],
        segment: Segment | None,
        message_id: str,
    ) -> AgentMessage:
        team_stats = {team_id: team.model_dump() for team_id, team in stats.teams.items()}
        return AgentMessage(
            id=message_id,
            kind="context.attached",
            sender="context",
            moment_id=moment.id,
            payload={
                "moment_type": moment.type,
                "minute": moment.minute,
                "team_id": moment.team_id,
                "window_minutes": stats.window_minutes,
                "tempo_per_min": stats.tempo_per_min,
                "teams": team_stats,
                "momentum": stats.momentum,
                "score": dict(score),
                "segment": segment.model_dump() if segment else None,
            },
            evidence=dict(moment.evidence),
        )
