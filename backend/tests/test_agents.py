"""Tests for the five agents' contracts and personalization (Phase 3)."""

from pathlib import Path

import pytest

from app.agents.context_agent import ContextAgent
from app.agents.event_agent import EventAgent
from app.agents.explain_agent import ExplainAgent
from app.agents.messages import PersonalizeProfile
from app.agents.personalize_agent import PersonalizeAgent
from app.agents.story_agent import StoryAgent
from app.engine import AnalyticsEngine
from app.llm import MockLLM, check_grounding
from app.simulator.generator import load_match

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


class ExplodingLLM:
    name = "exploding"

    def available(self) -> bool:
        return True

    def generate(self, **kwargs):
        raise ConnectionError("boom")


class HallucinatingLLM:
    name = "hallucinating"

    def available(self) -> bool:
        return True

    def generate(self, **kwargs):
        return "Unbelievable 9.99 xG bicycle kick seals a 5-0 win!"


def _goal_moment():
    match = load_match(SAMPLE)
    names = match.meta.display_names()
    engine = AnalyticsEngine(match.meta.teams[0].id, match.meta.teams[1].id, names)
    for event in match.events:
        engine.update(event)
    goal = next(m for m in engine.moments if m.type == "goal")
    stats = engine.state.window_stats(5, now=goal.timestamp_s)
    return match, names, engine, goal, stats


def test_event_agent_validates_and_rejects():
    agent = EventAgent()
    match = load_match(SAMPLE)
    message = agent.handle(match.events[0].model_dump(mode="json"), "m1")
    assert message.kind == "event.validated"
    with pytest.raises(ValueError):
        agent.handle({"type": "bicycle_kick"}, "m2")


def test_context_agent_attaches_engine_numbers():
    _, _, engine, goal, stats = _goal_moment()
    message = ContextAgent().handle(goal, stats, engine.state.score, None, "m1")
    assert message.kind == "context.attached"
    assert message.payload["teams"]["NGU"]["possession_pct"] >= 0
    assert message.payload["score"] == {"NGU": 2, "EVR": 1}
    assert message.evidence == goal.evidence


def test_explain_agent_grounded_with_mock():
    _, names, _, goal, stats = _goal_moment()
    from app.agents.context_agent import ContextAgent as Ctx

    context = Ctx().handle(goal, stats, {"NGU": 1, "EVR": 0}, None, "m1")
    message, degraded = ExplainAgent(MockLLM()).handle(goal, context, names, "m2")
    assert not degraded
    scorer = goal.evidence.get("scorer", "")
    assert names.get(scorer, scorer) in message.payload["text"]
    evidence = ExplainAgent(MockLLM()).llm_evidence(goal, context)
    assert check_grounding(message.payload["text"], evidence)


def test_explain_agent_falls_back_on_llm_failure():
    _, names, _, goal, stats = _goal_moment()
    context = ContextAgent().handle(goal, stats, {"NGU": 1, "EVR": 0}, None, "m1")
    message, degraded = ExplainAgent(ExplodingLLM()).handle(goal, context, names, "m2")
    assert degraded
    assert "1-0" in message.payload["text"]


def test_explain_agent_falls_back_on_hallucination():
    _, names, _, goal, stats = _goal_moment()
    context = ContextAgent().handle(goal, stats, {"NGU": 1, "EVR": 0}, None, "m1")
    message, degraded = ExplainAgent(HallucinatingLLM()).handle(goal, context, names, "m2")
    assert degraded
    assert "9.99" not in message.payload["text"]


def test_story_agent_line_and_recap():
    _, names, _, goal, stats = _goal_moment()
    context = ContextAgent().handle(goal, stats, {"NGU": 1, "EVR": 0}, None, "m1")
    explanation, _ = ExplainAgent(MockLLM()).handle(goal, context, names, "m2")
    evidence = ExplainAgent(MockLLM()).llm_evidence(goal, context)
    line, degraded = StoryAgent(MockLLM()).handle_line(
        explanation, goal, evidence, "Control phase", names, "m3"
    )
    assert not degraded
    assert "Control phase" in line.payload["text"]
    recap = StoryAgent(MockLLM()).handle_recap(
        {
            "home_name": "H",
            "away_name": "A",
            "score_home": 2,
            "score_away": 1,
            "goals": 3,
            "chances": 1,
            "spikes": 2,
            "swings": 1,
            "shifts": 1,
        },
        names,
        "r1",
    )
    assert "2-1" in recap.payload["text"]


def test_personalize_modes_differ():
    from app.agents.messages import AgentMessage

    story = AgentMessage(
        id="s",
        kind="story.line",
        sender="story",
        moment_id="m1",
        payload={"text": "NGU_11 scores, xG 0.55"},
        evidence={"scorer": "NGU_11", "xg": 0.55, "team_id": "NGU"},
    )
    texts = {}
    for mode in ("analyst", "fan", "beginner"):
        agent = PersonalizeAgent(PersonalizeProfile(mode=mode))
        texts[mode] = agent.handle_line(story, {}, "p").payload["text"]
    assert len(set(texts.values())) == 3
    assert "chance quality" in texts["beginner"]


def test_personalize_ukrainian_and_club_and_focus():
    from app.agents.messages import AgentMessage

    story = AgentMessage(
        id="s",
        kind="story.line",
        sender="story",
        moment_id="m1",
        payload={"text": "line"},
        evidence={"scorer": "EVR_10", "team_id": "EVR"},
    )
    agent = PersonalizeAgent(PersonalizeProfile(mode="fan", language="uk", favorite_club="EVR"))
    text = agent.handle_line(story, {}, "p").payload["text"]
    assert "Який момент!" in text and "Ваш клуб." in text
    focused = PersonalizeAgent(PersonalizeProfile(player_focus="NGU_10"))
    assert focused.handle_line(story, {}, "p") is None
    other = AgentMessage(
        id="s2",
        kind="story.line",
        sender="story",
        moment_id="m2",
        payload={"text": "line"},
        evidence={"scorer": "NGU_10", "team_id": "NGU"},
    )
    assert focused.handle_line(other, {}, "p") is not None
