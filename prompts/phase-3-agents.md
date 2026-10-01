# Phase 3 - multi-agent system

Five agents with distinct roles and typed messages:
- Event Agent: validate and parse incoming events.
- Context Agent: stats and patterns from the engine.
- Explain Agent: why a moment matters, grounded only in engine evidence.
- Story Agent: narrative lines and match recap.
- Personalize Agent: analyst / fan / beginner modes, English and Ukrainian, favorite club,
  player focus mode.

Requirements:
- Shared MatchState, explicit handoffs between agents, retries and fallbacks (if an agent
  fails, degrade gracefully), full trace log of every handoff.
- LLM abstraction in backend/app/llm/: a client interface with MockLLM (templates, offline)
  and AzureFoundryLLM configured through env vars (no keys in code).
- Grounding check: reject or repair any LLM output containing numbers that are not in the
  evidence payload.
- Match state storage behind an interface in backend/app/store/ (in-memory first).
- Tests for handoffs, failure recovery and the grounding check.

Orchestration: use Microsoft Agent Framework if it can be installed cleanly; otherwise build
a thin orchestrator with the same concepts and note it in DECISIONS.md.

Definition of done: the demo match runs end to end through all five agents offline with
MockLLM, trace log is viewable, tests pass.
