# MatchIQ - project rules (read this first, every session)

MatchIQ is a real-time, explainable football match intelligence system built for the
"Inside the Game: Developer Hackathon" (Microsoft + Premier League). It turns SYNTHETIC
football events into explainable insights, live narratives and automated recaps for
studio / broadcast / streaming use.

## Required pipeline (every component maps to one stage)
1. Ingest synthetic match events as they happen
2. Interpret them into football statistics, patterns and context
3. Explain WHY a moment matters (not only that it happened)
4. Render it as something that can sit on screen next to a match
5. Personalize it (analyst / fan / beginner, language, favorite club/player, player focus)

## Hard rules
- All data is synthetic. Use INVENTED clubs, players and stadiums. Never use real club or
  player names, badges, logos or any Premier League branding.
- No secrets in code. .env is git-ignored. Never read, print or log .env or any key.
- User-facing text is English.
- Runs on a weak laptop: Python 3.11+, no GPU, small dependencies
  (FastAPI, pydantic v2, pytest, ruff).
- No external network calls until Phase 3. LLM calls go through an abstraction with an
  offline MockLLM.
- All numbers shown to users are computed by code. An LLM may only explain numbers the
  engine provides, never invent them.
- Typed, documented, tested code. Small commits with clear messages.

## Repository layout
matchiq/
  README.md  AGENTS.md  .gitignore  .env.example
  prompts/                 (phase briefs)
  docs/ARCHITECTURE.md  docs/DECISIONS.md  docs/DEMO_SCRIPT.md
  backend/pyproject.toml
  backend/app/{main.py,config.py,models/,simulator/,engine/,agents/,llm/,store/,api/}
  backend/tests/
  frontend/                (React + Vite + TypeScript, Phase 4)
  infra/                   (Docker + Azure, Phase 5)
  data/samples/            (generated synthetic matches)

## Working agreement
- Work on ONE phase at a time, only the phase I name. Stop when it is done.
- Start in Plan mode: propose the plan, wait for my approval, then build.
- Make reasonable decisions yourself and log non-obvious ones in docs/DECISIONS.md.
- Before finishing a phase: run pytest and ruff, then summarize what exists, how to run
  it, and any open questions.
