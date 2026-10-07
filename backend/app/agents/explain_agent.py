"""ExplainAgent: explain WHY a moment matters, grounded in evidence (Phase 3).

Calls the LLM with the moment evidence only, then runs the grounding check.
On violation or LLM failure it retries once and finally degrades to a pure
template built straight from the evidence (always grounded).
"""

from typing import Any

from app.agents.messages import AgentMessage
from app.engine.schemas import Moment
from app.llm.base import BaseLLM
from app.llm.grounding import check_grounding


class ExplainAgent:
    """Grounded explainer with retry + template fallback."""

    name = "explain"

    def __init__(self, llm: BaseLLM, language: str = "en") -> None:
        self.llm = llm
        self.language = language

    def llm_evidence(self, moment: Moment, context: AgentMessage) -> dict[str, Any]:
        """Evidence subset the LLM may verbalise (engine numbers + ids only)."""
        payload = context.payload
        evidence: dict[str, Any] = {
            **moment.evidence,
            "team_id": moment.team_id,
            "minute": moment.minute,
            "moment_type": moment.type,
            "score": moment.evidence.get("score"),
        }
        teams = payload.get("teams", {})
        if moment.team_id and moment.team_id in teams:
            evidence["possession_pct"] = teams[moment.team_id]["possession_pct"]
            evidence["pass_accuracy_pct"] = teams[moment.team_id]["pass_accuracy_pct"]
        momentum = payload.get("momentum", {})
        if moment.team_id in momentum:
            evidence["momentum"] = momentum[moment.team_id]
        other = [t for t in payload.get("score", {}) if t != moment.team_id]
        if other:
            evidence["opponent_id"] = other[0]
        return {k: v for k, v in evidence.items() if v is not None}

    def fallback(self, moment: Moment, names: dict[str, str]) -> str:
        """Pure template from evidence: grounded by construction."""
        team = names.get(moment.team_id or "", moment.team_id or "-")
        minute = moment.minute
        ev = moment.evidence

        def who(key: str) -> str:
            raw = ev.get(key)
            return names.get(str(raw), str(raw)) if raw else "-"

        if moment.type == "goal":
            return f"{who('scorer')} scores for {team} ({minute}'). Now {ev.get('score')}."
        if moment.type == "big_chance":
            return f"{who('player')} threatens for {team} ({minute}'): xG {ev.get('xg')}."
        if moment.type == "pressure_spike":
            return f"{team} press: {ev.get('pressure_events')} duels in 5 minutes ({minute}')."
        if moment.type == "momentum_swing":
            return f"Momentum to {team} ({minute}')."
        return f"{team} substitution ({minute}'): {who('player_off')} off."

    def handle(
        self,
        moment: Moment,
        context: AgentMessage,
        names: dict[str, str],
        message_id: str,
        evidence: dict[str, Any] | None = None,
    ) -> tuple[AgentMessage, bool]:
        """Return (message, degraded). Retries once, then template fallback."""
        evidence = dict(evidence) if evidence is not None else self.llm_evidence(moment, context)
        text: str | None = None
        last_error: str | None = None
        for _ in range(2):
            try:
                candidate = self.llm.generate(
                    agent="explain",
                    task=moment.type,
                    evidence=evidence,
                    names=names,
                    language=self.language,
                )
            except Exception as exc:  # noqa: BLE001 - degrade on any LLM failure
                last_error = str(exc)
                continue
            if check_grounding(candidate, evidence):
                text = candidate
                break
            last_error = "grounding violation"
        degraded = text is None
        if degraded:
            text = self.fallback(moment, names)
        return (
            AgentMessage(
                id=message_id,
                kind="explanation",
                sender="explain",
                moment_id=moment.id,
                payload={
                    "text": text,
                    "degraded": degraded,
                    "error": last_error,
                    "moment_type": moment.type,
                },
                evidence=dict(moment.evidence),
            ),
            degraded,
        )
