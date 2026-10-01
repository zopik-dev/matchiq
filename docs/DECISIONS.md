# Decisions

Log of non-obvious decisions (newest first).

- (Phase 1 start) `promts/` renamed to `prompts/` to match AGENTS.md. AGENTS.md itself unchanged.
- (Phase 1 start) Scenario and sample files are JSON (no extra deps). Scenarios live in
  `backend/app/simulator/scenarios/*.json`; generated matches in `data/samples/*.json`.
- (Phase 1 start) CLI runs from `backend/` as `python -m app.simulator ...`.
