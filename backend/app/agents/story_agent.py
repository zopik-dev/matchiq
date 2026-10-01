"""StoryAgent: narrative lines and the match recap (Phase 3).

Turns grounded explanations into broadcast lines (via LLM + grounding check)
and synthesises the final recap from counted, engine-derived facts only.
"""

from typing import Any

from app.agents.messages import AgentMessage
from app.engine.schemas import Moment
from app.llm.base import BaseLLM
from app.llm.grounding import check_grounding


class StoryAgent:
    """Narrative synthesis with the same retry/fallback discipline as Explain."""

    name = "story"

    def __init__(self, llm: BaseLLM, language: str = "en") -> None:
        self.llm = llm
        self.language = language

    def handle_line(
        self,
        explanation: AgentMessage,
        moment: Moment,
        evidence: dict[str, Any],
        segment_title: str | None,
        names: dict[str, str],
        message_id: str,
    ) -> tuple[AgentMessage, bool]:
        """Turn one explanation into a broadcast line (grounded in its evidence)."""
        text: str | None = None
        for _ in range(2):
            try:
                candidate = self.llm.generate(
                    agent="story",
                    task=moment.type,
                    evidence=evidence,
                    names=names,
                    language=self.language,
                )
            except Exception:  # noqa: BLE001 - any LLM failure degrades
                break
            if check_grounding(candidate, evidence):
                text = candidate
                break
        degraded = text is None
        if degraded:
            text = str(explanation.payload.get("text", ""))
        if segment_title:
            text = f"{text} [{segment_title}]"
        return (
            AgentMessage(
                id=message_id,
                kind="story.line",
                sender="story",
                moment_id=explanation.moment_id,
                payload={"text": text, "degraded": degraded},
                evidence=evidence,
            ),
            degraded,
        )

    def handle_recap(
        self,
        summary: dict[str, Any],
        names: dict[str, str],
        message_id: str,
    ) -> AgentMessage:
        """Recap is pure code from counted facts — no LLM, nothing to hallucinate."""
        home = summary["home_name"]
        away = summary["away_name"]
        text = (
            f"{home} {summary['score_home']}-{summary['score_away']} {away}. "
            f"Goals: {summary['goals']}. Big chances: {summary['chances']}. "
            f"Press spikes: {summary['spikes']}. Swings: {summary['swings']}. "
            f"Changes: {summary['shifts']}."
        )
        return AgentMessage(
            id=message_id,
            kind="story.recap",
            sender="story",
            payload={"text": text, "summary": summary},
            evidence={"summary": summary},
        )
