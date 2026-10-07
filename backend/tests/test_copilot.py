"""Tests for the Ask MatchIQ copilot: parsing, grounding, fallback, endpoint."""

from fastapi.testclient import TestClient

from app.agents.copilot import answer_question, find_moment, get_demo_context, parse_question
from app.llm import check_grounding
from app.main import app

client = TestClient(app)


class ExplodingLLM:
    name = "exploding"

    def available(self) -> bool:
        return True

    def generate(self, **kwargs):
        raise ConnectionError("boom")


def test_parse_minute_forms():
    assert parse_question("Why did Eastvale score at 57'?") == {"minute": 57, "topic": "goal"}
    assert parse_question("Explain the 89th minute")["minute"] == 89
    assert parse_question("minute 23 goal")["minute"] == 23
    assert parse_question("score at 57")["minute"] == 57
    assert parse_question("How is the momentum?") == {"minute": None, "topic": "momentum_swing"}


def test_parse_clamps_and_topics():
    assert parse_question("minute 150")["minute"] == 90
    assert parse_question("tell me about pressing")["topic"] == "pressure_spike"
    assert parse_question("the substitution")["topic"] == "tactical_shift"
    assert parse_question("hello there")["topic"] == "general"


def test_find_moment_prefers_nearby_topic_match():
    _, engine = get_demo_context()
    moment = find_moment(engine.moments, "goal", 57)
    assert moment is not None and (moment.minute, moment.team_id) == (57, "EVR")
    moment = find_moment(engine.moments, "general", None)
    assert moment is not None


def test_answers_are_grounded_in_evidence():
    for query in [
        "Why did Eastvale score at 57'?",
        "Explain the 89' winning counter-attack",
        "How did Northgate's press break down?",
        "Who is on top right now?",
    ]:
        result = answer_question(query, mode="fan", language="en")
        assert result["answer"]
        assert result["evidence"]
        assert len(result["relevant_events"]) > 0
        assert len(result["suggested_followups"]) == 3
        assert check_grounding(result["answer"], result["evidence"]), query


def test_goal_answer_names_scorer_and_score():
    result = answer_question("Why did Eastvale score at 57'?", mode="analyst")
    assert "Felix Okafor" in result["answer"] and "1-1" in result["answer"]


def test_ukrainian_beginner_answer():
    result = answer_question("Explain the 89' counter", mode="beginner", language="uk")
    assert "Простими словами:" in result["answer"]
    assert check_grounding(result["answer"], result["evidence"])


def test_exploding_llm_still_returns_grounded_answer():
    result = answer_question("Why did Eastvale score at 57'?", llm=ExplodingLLM())
    assert "Felix Okafor" in result["answer"]
    assert check_grounding(result["answer"], result["evidence"])


def test_endpoint_schema_and_validation():
    payload = client.post(
        "/api/copilot/ask",
        json={"query": "Why did Eastvale score at 57'?", "mode": "fan", "lang": "en"},
    ).json()
    assert set(payload) == {"answer", "evidence", "relevant_events", "suggested_followups"}
    assert "1-1" in payload["answer"]
    assert client.post("/api/copilot/ask", json={"query": ""}).status_code == 422
    assert client.post("/api/copilot/ask", json={"query": "hi", "mode": "coach"}).status_code == 422
    uk = client.post(
        "/api/copilot/ask",
        json={"query": "Why did Eastvale score at 57'?", "mode": "fan", "lang": "uk"},
    ).json()
    assert "забиває" in uk["answer"] or "Тому що" in uk["answer"]
