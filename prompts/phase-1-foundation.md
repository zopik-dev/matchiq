# Phase 1 - foundation and synthetic data

Goal: repo skeleton, event schema, deterministic synthetic match generator, replay engine.

1. Create the repo structure from AGENTS.md, pyproject.toml, ruff config, .gitignore
   (include .env), .env.example, README skeleton, docs stubs. First commit.
2. Event schema in backend/app/models/events.py (pydantic v2). Fields: event_id, match_id,
   period (1/2), minute, second, timestamp_s, type (pass, shot, tackle, interception,
   possession_change, pressure, foul, corner, goal, substitution, kickoff, half_time,
   full_time), team_id, player_id, target_player_id (optional), x and y on a 0-100 pitch
   grid (own goal at x=0), outcome (complete/incomplete/blocked/saved/goal...),
   pass_distance_m, pass_difficulty (0-1), ball_speed_kmh, shot_speed_kmh, xg (synthetic,
   0-1, shots only), metadata dict. Match metadata model: teams, rosters with positions and
   numbers, formation, stadium, kickoff time. Validate ranges and types.
3. Synthetic match generator in backend/app/simulator/:
   - Seeded RNG: same seed gives the same match.
   - Two invented teams, 11 starters plus subs, named players with positions.
   - Full 90 minutes, roughly 1200-1800 events, realistic type ratios, usually 0-4 total goals.
   - Scenario arcs so the match has a story: possession control spells, a high-press spell,
     a counter-attack burst, a tactical shift at a given minute, a momentum swing after a goal.
   - Arcs configurable via a scenario file, including a dramatic "demo" scenario suited to a
     2-minute video.
   - Write sample matches to data/samples/ (one random, one demo).
4. Replay engine: async iterator streaming events in order with a speed multiplier
   (1x, 10x, 60x, instant), pause/resume and seek to minute.
5. Tests: schema validation, determinism by seed, ordering and timestamps, plausible totals,
   replay speed and pause. pytest and ruff must pass.
6. CLI: python -m app.simulator generate --seed 42 --scenario demo
        python -m app.simulator replay --speed 60
7. README: exact commands to install, test and run the CLI.

Definition of done: small clear commits, pytest and ruff pass, CLI generates and replays a
deterministic match, docs/DECISIONS.md lists decisions, final summary with open questions.
