# MatchIQ

Real-time, explainable football match intelligence for studio / broadcast / streaming use.
Built for the "Inside the Game: Developer Hackathon". **All clubs, players and events are
synthetic and invented** — no real teams, players, badges or league branding.

Phase 1: repo skeleton, synthetic event schema, deterministic match generator,
replay engine, CLI.
Phase 2: deterministic analytics engine — rolling windows, momentum
index, key-moment detectors, storyline segmenter. Zero LLM, pure math.
Phase 3: five-agent pipeline (event, context, explain, story,
personalize) with MockLLM offline and Azure Foundry client via env vars.
Phase 4 (current): FastAPI backend (match info, replay controls, SSE live
stream) + React/Vite/TS/Tailwind broadcast dashboard.

## Requirements

- Python 3.11+
- pip
- Node.js 20+ and npm (frontend only)

## Install

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Test and lint

```powershell
cd backend
pytest -q
ruff check .
```

## Run the CLI

```powershell
cd backend
python -m app.simulator generate --seed 42 --scenario demo
python -m app.simulator replay --speed 60
python -m app.engine feed --file ../data/samples/sample_demo_seed42.json
python -m app.agents run --mode fan --lang en
```

Generated matches are written to `../data/samples/` as JSON.

## Agent pipeline options

```powershell
cd backend
python -m app.agents run --mode beginner --lang uk --club NGU --player-focus NGU_10
python -m app.agents run --llm azure  # needs MATCHIQ_AZURE_* env vars, else MockLLM
```

## Run the live dashboard

Two terminals. Terminal 1 — backend API on :8000:

```powershell
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --port 8000
```

Terminal 2 — frontend on :5173:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the demo match starts playing automatically:
scoreboard with timer and Play/Pause/1x/10x/60x/Restart, 2D pitch, momentum
chart, clickable timeline, AI storyline feed (Analyst/Fan/Beginner, EN/UA,
club + player focus) and the collapsible agent trace panel.
