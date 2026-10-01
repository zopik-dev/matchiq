"""End-to-end pipeline tests: handoffs, recovery, determinism (Phase 3)."""

from pathlib import Path

from app.agents import MatchPipeline, PersonalizeProfile
from app.llm import MockLLM
from app.simulator.generator import load_match
from app.store import InMemoryStore

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "sample_demo_seed42.json"


class ExplodingLLM:
    name = "exploding"

    def available(self) -> bool:
        return True

    def generate(self, **kwargs):
        raise ConnectionError("boom")


class FlakyExplainAgent:
    """ExplainAgent that fails once, then behaves like the Mock-backed agent."""

    def __init__(self):
        from app.agents.explain_agent import ExplainAgent

        self.calls = 0
        self._real = ExplainAgent(MockLLM())
        self.name = "explain"

    def __getattr__(self, item):
        return getattr(self._real, item)

    def handle(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return self._real.handle(*args, **kwargs)


def _run(profile=None, llm=None):
    match = load_match(SAMPLE)
    store = InMemoryStore()
    pipeline = MatchPipeline(
        llm=llm or MockLLM(), store=store, profile=profile or PersonalizeProfile()
    )
    return pipeline.run(match), store


def test_end_to_end_demo_run():
    result, store = _run()
    assert result.moment_count == len(result.lines) > 0
    assert result.degraded == 0 and result.filtered == 0
    assert "2-1" in result.recap
    receivers = [h.receiver for h in result.trace]
    for stage in ("event", "context", "explain", "story", "personalize"):
        assert stage in receivers
    assert len(store.get_trace(result.match_id)) == len(result.trace)
    assert len(store.get_outputs(result.match_id)) == len(result.lines)


def test_handoff_trace_is_ordered_and_complete():
    result, _ = _run()
    seqs = [h.seq for h in result.trace]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert all(h.attempts >= 1 and h.message_id for h in result.trace)


def test_exploding_llm_degrades_but_completes():
    result, _ = _run(llm=ExplodingLLM())
    assert result.moment_count == len(result.lines) > 0
    assert result.degraded > 0
    assert "2-1" in result.recap


def test_pipeline_retries_transient_agent_failure(monkeypatch):
    from app.agents import pipeline as pipeline_module

    flaky = FlakyExplainAgent()
    monkeypatch.setattr(pipeline_module, "ExplainAgent", lambda *args, **kwargs: flaky)
    result, _ = _run()
    assert flaky.calls > 1
    assert result.moment_count == len(result.lines)
    retried = [h for h in result.trace if h.attempts > 1]
    assert retried


def test_invalid_event_is_skipped_gracefully(monkeypatch):
    from app.agents import pipeline as pipeline_module

    real_handle = pipeline_module.EventAgent.handle
    calls = {"n": 0}

    def flaky_handle(self, raw, message_id):
        calls["n"] += 1
        if 10 <= calls["n"] <= 12:  # fail all 3 attempts of one event
            raise ValueError("corrupt payload")
        return real_handle(self, raw, message_id)

    monkeypatch.setattr(pipeline_module.EventAgent, "handle", flaky_handle)
    result, _ = _run()
    assert result.moment_count == len(result.lines) > 0
    skipped = [h for h in result.trace if h.error and "corrupt" in h.error]
    assert len(skipped) == 1 and skipped[0].degraded


def test_ukrainian_beginner_profile():
    profile = PersonalizeProfile(mode="beginner", language="uk", favorite_club="NGU")
    result, _ = _run(profile=profile)
    assert result.lines
    assert any("Простими словами:" in line for line in result.lines)
    assert "Підсумок матчу:" in result.recap


def test_player_focus_filters_lines_but_keeps_recap():
    profile = PersonalizeProfile(player_focus="NGU_11")
    result, _ = _run(profile=profile)
    assert 0 < len(result.lines) < result.moment_count
    assert result.filtered == result.moment_count - len(result.lines)
    assert result.recap


def test_pipeline_is_deterministic():
    first, _ = _run()
    second, _ = _run()
    assert first.lines == second.lines
    assert first.recap == second.recap
