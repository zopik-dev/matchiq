# MatchIQ

Real-time, explainable football match intelligence for studio / broadcast / streaming use.
Built for the "Inside the Game: Developer Hackathon". **All clubs, players and events are
synthetic and invented** — no real teams, players, badges or league branding.

Phase 1 (current): repo skeleton, synthetic event schema, deterministic match generator,
replay engine, CLI.

## Requirements

- Python 3.11+
- pip

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
```

Generated matches are written to `../data/samples/` as JSON.
