# Demo video script — under 2 minutes (0:00–1:59)

Setup before recording: backend on :8000, frontend on :5173 (or `docker compose up`).
Open the dashboard, press Restart so the match plays from 0:00 at 60x.
What you see is 100% synthetic: invented clubs Northgate United (NGU) and
Eastvale Rovers (EVR). Target: all 5 judging criteria in 119 seconds.

## 0:00–0:15 — Hook + Real-world value
> "This is MatchIQ: a broadcast dashboard that turns a live football data feed
> into explainable on-screen storytelling — built for studio and streaming teams."

Show: full dashboard playing, scoreboard ticking, pitch dots moving.
Criterion: **Real-world value** (second-screen/broadcast companion).

## 0:15–0:35 — Technical depth (engine, zero LLM)
> "Underneath, a deterministic analytics engine computes rolling windows,
> a zero-sum momentum index and key moments — pure math, no LLM involved."

Show: pressure timeline building, hover readout ("57' · Eastvale 36 momentum"),
momentum chart flipping at the equaliser.
Criterion: **Technical depth**.

## 0:35–0:60 — Agentic design (trace panel)
> "Five specialized agents handle each moment: Event validates, Context adds
> stats, Explain justifies, Story narrates, Personalize formats. Every handoff
> is typed, retried and logged."

Show: open the Agent Trace panel, expand two moments
(`event→context→explain→story→personalize [ok]`).
Mention: "If any step fails, the pipeline degrades to evidence templates
instead of breaking the broadcast."
Criterion: **Agentic design**.

## 1:00–1:25 — Explainability + UX (the 89' winner)
> "Watch the late winner: the 89th-minute goal fires a momentum swing, and the
> AI explains WHY it matters using only engine numbers — xG 0.29, score 2–1 —
> with a grounding check rejecting anything invented."

Show: 89' goal card with evidence badges, narrative panel updating, breakdown steps.
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
> "MatchIQ: ingest, interpret, explain, render, personalize — live, grounded,
> and broadcast-ready."

Show: final 2–1 scoreboard, recap line, repo URL on screen.

## Shot list (recording checklist)
- [ ] 60x speed so 0'→90' fits the runtime; pause on the 57' and 89' cards.
- [ ] One take per section; total under 1:59 after editing.
- [ ] No real club/player names appear anywhere (verify feed text before upload).
- [ ] Captions mention: synthetic data, MIT-licensed, repo link.
