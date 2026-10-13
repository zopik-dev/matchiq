# Decisions

Log of non-obvious decisions (newest first).

- (Resilience) SSE auto-reconnects 3 s after a backend drop (cleared on the
  next healthy state); natural full-time sets a flag so finished matches stay
  finished instead of reconnect-looping. Shared speech service per credentials
  so the MP3 cache survives across requests.
- (Perf) Backdrop is static paint: the animated full-viewport drift layer,
  blend modes and will-change are gone (weak GPUs fell back to black
  compositor tiles and the drift never visibly moved there); blur radii cut
  roughly in half. Dead CSS (dash-anim, noir-drift) and the dead `_wake`
  event in LiveSession removed; experience choice persists in localStorage.
- (Elite suite) Pitch Control is a lightweight influence field (21x14 cells,
  1/(1+d2) falloff, ball-carrier boost) — not a true Voronoi — because token
  positions are illustrative, not tracked data; overloads fire on 3v2+ counts
  near the ball. Heatmap accumulates the streamed window (800-pt ring buffer),
  so seeks rebuild it honestly. Pundit distances read display units as metres
  (105x68 grid, spec formula). Crowd is 100% procedural Web Audio (no assets);
  speech ducks it to 30%. Foundry client prefers FOUNDRY_* env, falls back to
  legacy AZURE_* vars, then MockLLM on any network failure.
- (Dual experience) One engine, two presentations: TV Broadcast View (fullscreen
  pitch, scorebug, auto lower-thirds for goal/big_chance/tactical_shift with
  speech, 8 s auto-dismiss, ESC to exit) vs Interactive Console (full dashboard).
  Entering TV auto-enables commentary; lower-third pills use only moment evidence
  (xG, score, duels, sub names) — never invented transition/speed numbers.
- (Frontend Apple TV Minimal) Dropped the neon/sci-fi system (cyan #00F2FE, amber
  #F59E0B, glow filters, floodlit gradients, pulsing halos) for a restrained
  editorial look: graphite canvas #090D16, matte cards #0F1626, moss turf #0C2317
  with 35%-opacity markings, matte team accents (blue #2563EB, crimson #DC2626),
  system font stack. All interactions (22-player focus, X-Ray stepper, live
  audio, SSE wiring) untouched — visuals only.
- (Speech) Hybrid commentary audio: Azure Speech TTS via stdlib `urllib` REST
  (no SDK, honoring the small-deps rule) with an MD5 in-memory MP3 cache;
  missing `MATCHIQ_AZURE_SPEECH_KEY` returns `{"status": "fallback_client"}` and
  the browser speaks the same text via Web Speech API (`en-GB`/`uk-UA`,
  rate 1.1). Excited SSML prosody only for `goal`/`big_chance`; autoplay skips
  the SSE catch-up burst (2 s guard) so reconnects don't replay past goals.
- (Phase 5) Cosmos DB over PostgreSQL: the SQL API is reachable with stdlib
  REST + HMAC (zero new dependencies, honoring the small-deps rule); Postgres
  stays a documented alternative behind the same interface.
- (Phase 5) No Docker daemon on the dev laptop, so images/compose/Azure scripts
  are authored but not executed here — they must be verified with
  `docker compose up --build` on a Docker machine before submission.
- (Phase 5) Nginx (not `vite preview`) serves the frontend image and proxies
  `/api` to the backend container, keeping one origin for the app.
- (Frontend Variant 2) Adopted the Figma prototype's visual system (glass
  cards, floodlit pitch, pressure area chart, 2x2 metrics, breakdown steps)
  on the existing Tailwind v3 setup (theme ported, no v4 migration). All
  prototype mock data was discarded: sine-wave pressure replaced by the real
  momentum series, invented names/xG replaced by roster lookup and evidence
  payloads, fabricated breakdown steps replaced by the real events preceding
  each moment. Metrics show only engine-computed numbers (shot/match xG,
  momentum, chances, possession).
- (Phase 4) SSE reuses the batch pipeline: one full MockLLM run per profile is
  cached, then events stream paced by speed while moments/texts/traces release
  at their timestamps. Connecting a viewer (re)starts playback; reconnects get
  catch-up moments so seek and profile switches rebuild the feed.
- (Phase 4) Single-viewer session: a new stream takes over the old one. Enough
  for a laptop demo; multi-room sync is out of scope.
- (Phase 4) Frontend is Vite + React + TS + Tailwind v3 + lucide-react, SVG-only
  visuals (no chart/3D libs). Dark broadcast grid on #0B0F19.
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
