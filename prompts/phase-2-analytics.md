# Phase 2 - analytics engine (interpret + explain evidence)

Goal: turn the event stream into football state, statistics and detected moments, each with
evidence numbers. No LLM yet.

- Rolling windows (1, 5, 10 min): possession %, pass accuracy, tempo (events/min), pressure
  events, high turnovers (ball won in opponent half), shot quality (sum xG), momentum index.
- Key-moment detector: goals, big chances, pressure spikes, momentum swings, tactical shifts.
- Storyline segmenter: label match phases (for example control, pressure broken, high press,
  tactical shift) with start/end minutes.
- Every insight carries an evidence payload: the exact numbers that justify it, so later
  agents can only explain what is in the payload.
- Incremental processing: the engine updates state event by event (live), not only in batch.
- Tests with the demo scenario: the known arcs (high press, tactical shift, goal swing) must
  be detected at the expected minutes.

Definition of done: pytest and ruff pass, a CLI command prints the live insight feed and the
storyline for the demo match, DECISIONS.md updated.
