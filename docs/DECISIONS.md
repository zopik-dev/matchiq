# Decisions

Log of non-obvious decisions (newest first).

- (Phase 3) In-repo orchestrator instead of Microsoft Agent Framework: the
  framework's dependency weight is wrong for an offline-first weak-laptop
  project; typed handoffs, retries and the trace fit in one explicit module.
- (Phase 3) Grounding rule: a number token must appear in an evidence string
  (scores "2-1", ids "NGU_11") or match an evidence number within 0.011
  (rounding); a leading minus counts as a sign except after a letter.
- (Phase 3) Personalization is rule-based (no LLM): mode framing, EN/UK fixed
  strings, club top-billing, player-focus filtering. The recap is pure code
  from counted facts.
- (Phase 3) Azure client uses only the standard library and env vars
  (`MATCHIQ_AZURE_ENDPOINT/API_KEY/DEPLOYMENT/API_VERSION`); missing config
  means `available() == False` and the pipeline falls back to MockLLM.
- (Phase 3) Duplicate moment ids fixed with a monotonic counter (two moments
  from one event previously shared an id).
- (Phase 2) Engine has one live path: `AnalyticsEngine.update()` event by event.
  No batch mode; file analysis feeds the same method, so streaming and CLI agree.
- (Phase 2) Momentum is zero-sum (-100..100, home perspective): possession edge x1.2,
  xG edge x50 (clamped +-25), pressure edge x1.5 (clamped +-15), plus a +25 goal
  boost decaying over 10 minutes.
- (Phase 2) A swing fires on a lead flip (hysteresis +-10) or a goal by a side
  that was not already firmly on top (|momentum| < 25 pre-boost). Goals scored
  while dominant (demo 23') deliberately fire no swing.
- (Phase 2) Big-chance threshold is xG >= 0.25 so scripted demo goals (0.27-0.55)
  always qualify as chances.
- (Phase 2) Pressure spike = 14+ team duels (pressure/tackle/interception) in the
  trailing 5 minutes, leading edge, 5-minute cooldown per team.
- (Phase 2) Generator change (Phase 1 file, Phase 2 enabler): the scenario's
  shifting team now takes its first sub exactly at the tactical-shift minute, so
  the shift is visible in the stream. Event counts and scripted goals unchanged;
  both committed samples were regenerated.
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
