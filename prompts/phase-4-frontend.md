# Phase 4 - API and frontend

Backend: FastAPI endpoints for matches, replay control (play/pause/speed/seek), SSE live
stream of insights, storyline, key moments, explanations, agent trace.

Frontend (React + Vite + TypeScript), broadcast-overlay look:
- Live insight feed with timestamps.
- Pitch view showing recent events.
- Match Storyline timeline; clicking a segment asks "why did the match change here?"
- Mode switcher (analyst / fan / beginner), language switcher (English / Ukrainian),
  favorite club, player focus.
- Agent trace panel showing handoffs.
- Clean, fast, readable on a laptop; no heavy libraries.

Definition of done: one command starts backend and frontend, the demo match plays live in
the browser, README explains how to run it.
