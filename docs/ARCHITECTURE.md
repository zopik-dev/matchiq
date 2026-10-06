# Architecture

Five pipeline stages; each stage is one backend module plus its frontend surface.

1. **Ingest** — `backend/app/simulator/`: seeded RNG, invented teams/rosters,
   scenario arcs (`default`, `demo`), replay engine. Output: validated
   `Event` stream (`backend/app/models/events.py`) and `data/samples/*.json`.
2. **Interpret** — `backend/app/engine/`: single live path `AnalyticsEngine.update()`
   producing rolling 1/5/10-min `WindowStats`, a zero-sum momentum index and
   typed `Moment`s, merged into `Segment` storylines. Pure math, zero LLM.
3. **Explain** — `backend/app/agents/` + `backend/app/llm/`: Event, Context,
   Explain, Story and Personalize agents with typed `AgentMessage` handoffs, a
   `Handoff` trace, retries and evidence-only fallbacks. `MockLLM` offline;
   `AzureFoundryLLM` via env; `check_grounding()` rejects invented numbers.
4. **Render** — `backend/app/api/` (FastAPI + SSE `LiveSession`) and `frontend/`
   (React/Vite/TS/Tailwind broadcast dashboard: pitch, pressure timeline,
   storyline feed, agent trace panel).
5. **Personalize** — `PersonalizeProfile` (analyst/fan/beginner, en/uk,
   favorite club, player focus) applied rule-based at the end of the pipeline
   and selectable live in the UI.

Cross-cutting: `backend/app/config.py` (env settings), `backend/app/store/`
(`MatchStore` interface; in-memory default, Cosmos DB when configured),
`infra/` (Docker + Azure Container Apps scale-to-zero deployment).
