"""Tests for the LLM abstraction and grounding validator (Phase 3)."""

from pathlib import Path

import pytest

from app.engine import AnalyticsEngine
from app.llm import AzureFoundryLLM, MockLLM, build_prompt, check_grounding
from app.simulator.generator import load_match

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


def test_grounding_accepts_exact_and_rounded_numbers():
    evidence = {"xg": 0.547, "minute": 23, "score": "2-1", "scorer": "NGU_11"}
    assert check_grounding("xG 0.547 in minute 23, score 2-1 by NGU_11", evidence)
    assert check_grounding("rounded xG 0.55", evidence)


def test_grounding_accepts_negative_momentum():
    evidence = {"momentum_home_after": -36.02, "momentum_home_before": -11.02}
    assert check_grounding("index now -36.02 (was -11.02)", evidence)


def test_grounding_rejects_hallucinated_numbers():
    evidence = {"xg": 0.27, "minute": 57, "score": "1-1"}
    report = check_grounding("hat-trick seals a 3-0 win with xG 0.99", evidence)
    assert not report
    assert set(report.violations) == {"3", "-0", "0.99"}


def test_mock_output_grounded_for_every_demo_moment():
    match = load_match(SAMPLE)
    names = {t.id: t.name for t in match.meta.teams}
    engine = AnalyticsEngine(match.meta.teams[0].id, match.meta.teams[1].id, names)
    llm = MockLLM()
    assert llm.available()
    for event in match.events:
        engine.update(event)
    assert engine.moments
    for moment in engine.moments:
        evidence = {"team_id": moment.team_id, "minute": moment.minute, **moment.evidence}
        for agent in ("explain", "story"):
            text = llm.generate(agent=agent, task=moment.type, evidence=evidence, names=names)
            assert check_grounding(text, evidence), (agent, moment.type, text)


def test_prompt_builder_forbids_invented_numbers():
    system, user = build_prompt(
        agent="explain",
        task="goal",
        evidence={"xg": 0.5},
        names={"NGU": "Northgate United"},
        language="en",
    )
    assert "ONLY numbers" in system and "English" in system
    assert "'xg': 0.5" in user or '"xg": 0.5' in user or "0.5" in user


def test_azure_client_unavailable_without_env(monkeypatch):
    for var in ("MATCHIQ_AZURE_ENDPOINT", "MATCHIQ_AZURE_API_KEY", "MATCHIQ_AZURE_DEPLOYMENT"):
        monkeypatch.delenv(var, raising=False)
    client = AzureFoundryLLM()
    assert not client.available()
    with pytest.raises(RuntimeError):
        client.generate(agent="explain", task="goal", evidence={}, names={})


def test_azure_client_available_with_env(monkeypatch):
    monkeypatch.setenv("MATCHIQ_AZURE_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_API_KEY", "secret")
    monkeypatch.setenv("MATCHIQ_AZURE_DEPLOYMENT", "chat")
    assert AzureFoundryLLM().available()
