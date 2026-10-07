"""MatchPipeline: lightweight in-repo orchestrator for the five agents (Phase 3).

Chosen over Microsoft Agent Framework: the framework would add heavy
dependencies to a weak-laptop, offline-first project for concepts (typed
handoffs, retries, trace) that fit in one explicit module. Logged in
docs/DECISIONS.md.

Flow per match: EventAgent validates the stream while the engine builds state
live; then per fired moment Context -> Explain -> Story; finally the recap is
personalized. Every agent call is retried and recorded in the handoff trace;
failures degrade to evidence-only fallbacks instead of aborting the run.
"""

from collections.abc import Callable
from functools import partial
from typing import Any

from app.agents.context_agent import ContextAgent
from app.agents.event_agent import EventAgent
from app.agents.explain_agent import ExplainAgent
from app.agents.messages import (
    AgentMessage,
    Handoff,
    PersonalizeProfile,
)
from app.agents.personalize_agent import PersonalizeAgent
from app.agents.story_agent import StoryAgent
from app.engine import AnalyticsEngine, build_storyline
from app.engine.schemas import Moment, Segment, WindowStats
from app.llm.base import BaseLLM
from app.models.events import Event, MatchData
from app.store.base import MatchStore


class PipelineResult:
    """End-to-end run outcome with viewable trace."""

    def __init__(
        self,
        match_id: str,
        lines: list[str],
        recap: str,
        trace: list[Handoff],
        degraded: int,
        filtered: int,
        moment_count: int,
        details: list[dict] | None = None,
    ) -> None:
        self.match_id = match_id
        self.lines = lines
        self.recap = recap
        self.trace = trace
        self.degraded = degraded
        self.filtered = filtered
        self.moment_count = moment_count
        #: Per-moment texts for live streaming (explanation/story/line or None).
        self.details: list[dict] = details or []


class MatchPipeline:
    """Run a match through all five agents with retries and fallbacks."""

    def __init__(
        self,
        llm: BaseLLM,
        store: MatchStore,
        profile: PersonalizeProfile | None = None,
        max_retries: int = 2,
    ) -> None:
        self.llm = llm
        self.store = store
        self.profile = profile or PersonalizeProfile()
        self.max_retries = max_retries
        self._seq = 0
        self._trace: list[Handoff] = []
        self._match_id = ""

    def _handover(
        self,
        sender: Any,
        receiver: Any,
        message_id: str,
        fn: Callable[[], AgentMessage | tuple[AgentMessage, bool] | None],
        fallback: Callable[[], AgentMessage | None],
    ) -> AgentMessage | None:
        sender_name = getattr(sender, "name", str(sender))
        receiver_name = getattr(receiver, "name", str(receiver))
        attempts = 0
        last_error: str | None = None
        while attempts <= self.max_retries:
            attempts += 1
            try:
                outcome = fn()
                message = outcome[0] if isinstance(outcome, tuple) else outcome
                degraded = outcome[1] if isinstance(outcome, tuple) else False
                self._record(sender_name, receiver_name, message_id, attempts, True, degraded, None)
                return message
            except Exception as exc:  # noqa: BLE001 - retry any agent crash
                last_error = f"{type(exc).__name__}: {exc}"
        try:
            message = fallback()
            self._record(sender_name, receiver_name, message_id, attempts, True, True, last_error)
            return message
        except Exception as exc:  # noqa: BLE001 - fallback itself failed
            self._record(
                sender_name,
                receiver_name,
                message_id,
                attempts,
                False,
                True,
                f"{last_error} | fallback failed: {exc}",
            )
            return None

    def _record(
        self,
        sender: Any,
        receiver: Any,
        message_id: str,
        attempts: int,
        ok: bool,
        degraded: bool,
        error: str | None,
    ) -> None:
        self._seq += 1
        handoff = Handoff(
            seq=self._seq,
            sender=sender,
            receiver=receiver,
            message_id=message_id,
            attempts=attempts,
            ok=ok,
            degraded=degraded,
            error=error,
        )
        self._trace.append(handoff)
        self.store.append_handoff(self._match_id, handoff.model_dump())

    def run(self, match: MatchData) -> PipelineResult:
        """Run a full match end to end; never raises on agent failure."""
        self._seq = 0
        self._trace = []
        match_id = match.meta.match_id
        self._match_id = match_id
        home_id, away_id = match.meta.teams[0].id, match.meta.teams[1].id
        names = match.meta.display_names()
        self.store.save_match(match_id, match.meta.model_dump(mode="json"))

        event_agent = EventAgent()
        engine = AnalyticsEngine(home_id, away_id, names)
        staged: list[tuple[Moment, WindowStats]] = []
        for index, raw in enumerate(match.events):
            message_id = f"{match_id}-e{index:04d}-event"
            message = self._handover(
                "pipeline",
                event_agent,
                message_id,
                partial(event_agent.handle, raw.model_dump(mode="json"), message_id),
                lambda: None,
            )
            if message is None:
                continue
            event = Event(**message.payload["event"])
            for moment in engine.update(event):
                stats = engine.state.window_stats(5)
                staged.append((moment, stats))

        segments = build_storyline(engine.samples, engine.moments, home_id, away_id, names)

        context_agent = ContextAgent()
        explain_agent = ExplainAgent(self.llm, self.profile.language)
        story_agent = StoryAgent(self.llm, self.profile.language)
        personalize_agent = PersonalizeAgent(self.profile)

        lines: list[str] = []
        details: list[dict] = []
        degraded = 0
        filtered = 0
        for moment, stats in staged:
            segment = _segment_for(segments, moment.minute)
            moment_id = moment.id
            context = self._handover(
                event_agent,
                context_agent,
                f"{moment_id}-context",
                partial(
                    context_agent.handle,
                    moment,
                    stats,
                    engine.state.score,
                    segment,
                    f"{moment_id}-context",
                ),
                partial(_minimal_context, moment, f"{moment_id}-context"),
            )
            if context is None:
                continue
            explanation, was_degraded = self._handover_explain(
                explain_agent, moment, context, names
            )
            if explanation is None:
                continue
            degraded += was_degraded
            story_line, line_degraded = self._handover_story(
                story_agent, explain_agent, explanation, moment, context, segment, names
            )
            if story_line is None:
                continue
            degraded += line_degraded
            personalized = self._handover(
                story_agent,
                personalize_agent,
                f"{moment_id}-personalized",
                partial(
                    personalize_agent.handle_line,
                    story_line,
                    names,
                    f"{moment_id}-personalized",
                ),
                partial(_passthrough_line, story_line, f"{moment_id}-personalized"),
            )
            if personalized is None:
                filtered += 1
                details.append(
                    {
                        "moment_id": moment.id,
                        "moment_type": moment.type,
                        "minute": moment.minute,
                        "timestamp_s": moment.timestamp_s,
                        "team_id": moment.team_id,
                        "evidence": moment.evidence,
                        "explanation": str(explanation.payload.get("text", "")),
                        "story": str(story_line.payload.get("text", "")),
                        "line": None,
                    }
                )
                continue
            lines.append(str(personalized.payload["text"]))
            details.append(
                {
                    "moment_id": moment.id,
                    "moment_type": moment.type,
                    "minute": moment.minute,
                    "timestamp_s": moment.timestamp_s,
                    "team_id": moment.team_id,
                    "evidence": moment.evidence,
                    "explanation": str(explanation.payload.get("text", "")),
                    "story": str(story_line.payload.get("text", "")),
                    "line": str(personalized.payload["text"]),
                }
            )
            self.store.record_output(
                match_id,
                moment_id,
                {"text": personalized.payload["text"], "kind": "line"},
            )

        recap = self._handover(
            story_agent,
            story_agent,
            f"{match_id}-recap",
            lambda: story_agent.handle_recap(
                _summarize(engine.moments, engine.state.score, names, home_id, away_id),
                names,
                f"{match_id}-recap",
            ),
            lambda: None,
        )
        recap_text = ""
        if recap is not None:
            personal = self._handover(
                story_agent,
                personalize_agent,
                f"{match_id}-recap-personalized",
                lambda: personalize_agent.handle_recap(
                    recap, names, f"{match_id}-recap-personalized"
                ),
                lambda: _passthrough_line(recap, f"{match_id}-recap-personalized"),
            )
            if personal is not None:
                recap_text = str(personal.payload["text"])
        return PipelineResult(
            match_id=match_id,
            lines=lines,
            recap=recap_text,
            trace=list(self._trace),
            degraded=degraded,
            filtered=filtered,
            moment_count=len(staged),
            details=details,
        )

    def _handover_explain(
        self, agent: ExplainAgent, moment: Moment, context: AgentMessage, names: dict[str, str]
    ) -> tuple[AgentMessage | None, bool]:
        message_id = f"{moment.id}-explanation"
        outcome = self._handover(
            "context",
            agent,
            message_id,
            lambda: agent.handle(moment, context, names, message_id),
            lambda: _fallback_message(agent, moment, names, message_id),
        )
        if outcome is None:
            return None, True
        return outcome, bool(outcome.payload.get("degraded", False))

    def _handover_story(
        self,
        agent: StoryAgent,
        explain_agent: ExplainAgent,
        explanation: AgentMessage,
        moment: Moment,
        context: AgentMessage,
        segment: Segment | None,
        names: dict[str, str],
    ) -> tuple[AgentMessage | None, bool]:
        message_id = f"{explanation.moment_id}-story"
        title = segment.title if segment else None
        evidence = explain_agent.llm_evidence(moment, context)
        outcome = self._handover(
            "explain",
            agent,
            message_id,
            lambda: agent.handle_line(explanation, moment, evidence, title, names, message_id),
            lambda: _passthrough_line(explanation, message_id),
        )
        if outcome is None:
            return None, True
        return outcome, bool(outcome.payload.get("degraded", False))


def _segment_for(segments: list[Segment], minute: int) -> Segment | None:
    for segment in segments:
        if segment.start_minute <= minute <= segment.end_minute:
            return segment
    return None


def _minimal_context(moment: Moment, message_id: str) -> AgentMessage:
    return AgentMessage(
        id=message_id,
        kind="context.attached",
        sender="context",
        moment_id=moment.id,
        payload={"teams": {}, "momentum": {}, "score": {}},
        evidence=dict(moment.evidence),
    )


def _fallback_message(
    agent: ExplainAgent, moment: Moment, names: dict[str, str], message_id: str
) -> AgentMessage:
    return AgentMessage(
        id=message_id,
        kind="explanation",
        sender="explain",
        moment_id=moment.id,
        payload={"text": agent.fallback(moment, names), "degraded": True, "error": "agent crash"},
        evidence=dict(moment.evidence),
    )


def _passthrough_line(source: AgentMessage, message_id: str) -> AgentMessage:
    return AgentMessage(
        id=message_id,
        kind="story.line",
        sender="story",
        moment_id=source.moment_id,
        payload={"text": str(source.payload.get("text", "")), "degraded": True},
        evidence=dict(source.evidence),
    )


def _summarize(
    moments: list[Moment],
    score: dict[str, int],
    names: dict[str, str],
    home_id: str,
    away_id: str,
) -> dict[str, Any]:
    kinds = [m.type for m in moments]
    return {
        "home_name": names.get(home_id, home_id),
        "away_name": names.get(away_id, away_id),
        "score_home": score.get(home_id, 0),
        "score_away": score.get(away_id, 0),
        "goals": kinds.count("goal"),
        "chances": kinds.count("big_chance"),
        "spikes": kinds.count("pressure_spike"),
        "swings": kinds.count("momentum_swing"),
        "shifts": kinds.count("tactical_shift"),
    }
