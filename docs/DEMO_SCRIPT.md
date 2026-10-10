# Demo video script — under 2 minutes (0:00–1:59)

Setup before recording: backend on :8000, frontend on :5173 (or `docker compose up`).
Open the dashboard, press Restart so the match plays from 0:00 at 60x.
What you see is 100% synthetic: invented clubs Northgate United (NGU) and
Eastvale Rovers (EVR). Target: all 5 judging criteria in 119 seconds.

## 0:00–0:20 — Hook: dual experience (TV + console)
> "This is MatchIQ, in two experiences. First, the living room: a TV broadcast
> view with a scorebug and automated lower-thirds. Second, the interactive
> console for analysts, fans and beginners."

Show: header pill switch Console → **TV Broadcast View** (pitch goes
fullscreen, scorebug `[NGU] 0–0 [EVR]` top-left). Let the 23' goal fire the
lower-third (`⚽ GOAL ANALYSIS · 23'`, headline, xG/score pills) with voice
commentary, auto-fading after 8 seconds. Press ESC back to console.
Criterion: **Real-world value** (passive TV overlay + second-screen companion).

## 0:20–0:40 — Technical depth (engine, zero LLM)
> "Underneath, a deterministic analytics engine computes rolling windows,
> a zero-sum momentum index and key moments — pure math, no LLM involved."

Show: pressure timeline building, hover readout ("57' · Eastvale 36 momentum"),
momentum chart flipping at the equaliser.
Criterion: **Technical depth**.

## 0:40–1:00 — Agentic design (trace panel)
> "Five specialized agents handle each moment: Event validates, Context adds
> stats, Explain justifies, Story narrates, Personalize formats. Every handoff
> is typed, retried and logged."

Show: open the Agent Trace panel, expand two moments
(`event→context→explain→story→personalize [ok]`).
Mention: "If any step fails, the pipeline degrades to evidence templates
instead of breaking the broadcast."
Criterion: **Agentic design**.

## 1:00–1:25 — Explainability + TV payoff (the 89' winner)
> "Watch the late winner twice: first as a TV viewer — the 89th-minute goal
> raises the lower-third with xG and score pills and speaks the story. Then as
> an analyst — the same moment explained with grounded engine numbers."

Show: switch to TV mode, seek near 88', 89' goal lower-third + commentary;
back to console: 89' goal card with evidence badges, narrative panel updating.
Switch mode Fan → Analyst → Beginner, then EN → UA.
Criterion: **UX/Presentation** + explainability.

## 1:25–1:45 — Personalization + Azure alignment
> "Analysts get numbers, beginners get plain language with xG explained, in
> English or Ukrainian — filtered by favorite club or player. It deploys to
> Azure Container Apps with scale-to-zero, Cosmos DB state and Microsoft
> Foundry models behind the same interfaces."

Show: player-focus dropdown on NGU_10, recap line. Cut to `infra/` tree +
`docker compose up` terminal (b-roll, 3 s).
Criterion: **Alignment** (Microsoft + Premier League track: Azure, Foundry).

## 1:45–1:59 — Close
> "MatchIQ: ingest, interpret, explain, render, personalize — on TV and in
> your hands, live, grounded, and broadcast-ready."

Show: TV mode final 2–1 scorebug, repo URL on screen.

## Shot list (recording checklist)
- [ ] 60x speed so 0'→90' fits the runtime; pause on the 57' and 89' cards.
- [ ] TV lower-third captured on at least one goal (23', 57' or 89').
- [ ] ESC / header pill return to console shown once.
- [ ] One take per section; total under 1:59 after editing.
- [ ] No real club/player names appear anywhere (verify feed text before upload).
- [ ] Captions mention: synthetic data, MIT-licensed, repo link.
