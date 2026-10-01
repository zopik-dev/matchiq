# Decisions

Log of non-obvious decisions (newest first).

- (Phase 1) `minute` is the global match minute (0-90); `period` derives from it
  (1 for 0-45, 2 for 46-90). `timestamp_s` must stay within 600 s of the
  minute/second clock to allow stoppage time.
- (Phase 1) `xg` is allowed on `shot` AND `goal` (a goal is a finished shot);
  all other types must leave it `None`.
- (Phase 1) Rosters are fixed invented squads (`teams.py`); match variation comes
  only from the seed. Committed samples use `sample_*.json` names; ad-hoc CLI
  output defaults to git-ignored `match_<seed>_<scenario>.json`.
- (Phase 1) Goals are scripted at scenario minutes and inserted as `goal` events
  (demo: 23' home, 57' away, 89' home); random events never produce goals, so the
  0-4 range always holds. Momentum swing after each goal boosts shots/pressure.
- (Phase 1) Replay `speed` is match-seconds per real second, `0`/`instant` means
  no sleeping. Async tests use `asyncio.run()` inside sync tests, so no
  `pytest-asyncio` dependency.
- (Phase 1 start) `promts/` renamed to `prompts/` to match AGENTS.md. AGENTS.md itself unchanged.
- (Phase 1 start) Scenario and sample files are JSON (no extra deps). Scenarios live in
  `backend/app/simulator/scenarios/*.json`; generated matches in `data/samples/*.json`.
- (Phase 1 start) CLI runs from `backend/` as `python -m app.simulator ...`.
