# Hackathon submission checklist

## Originality & branding
- [x] Every club, player, stadium and badge is invented (Northgate United,
      Eastvale Rovers, Meridian Park). No real Premier League club/player names.
- [x] No Premier League logos, trademarks or branding in code, data, UI or video.
- [x] Grep the repo for real club names before submitting:
      `rg -i "arsenal|chelsea|liverpool|city|united|tottenham|newcastle|villa|west ham|everton|leeds" --glob '!package-lock.json'`
      (only our invented "Northgate United" / "Eastvale Rovers" may match "united"/"rovers").

## Secrets & repo hygiene
- [x] No API keys, connection strings or credentials in code, configs or history.
- [x] `.env` is git-ignored; only `.env.example` (placeholders) is committed.
- [x] `MIT LICENSE` present; `README.md` links it.

## Working submission
- [x] `pytest -q` passes in `backend/` (116 tests).
- [x] `npm test` passes in `frontend/` (41 vitest tests).
- [x] `ruff check .` and `ruff format --check .` clean in `backend/`.
- [x] `npm run build` succeeds in `frontend/` (tsc + vite).
- [ ] `docker compose up --build` serves frontend :5173 + backend :8000
      (verify on a machine with Docker; CI laptop here has none — see DECISIONS).
- [ ] Public repo URL works for judges until the end of judging; Azure
      deployment (deploy.sh) stays up with scale-to-zero.

## Demo video (< 2:00)
- [ ] Follows `docs/DEMO_SCRIPT.md`: hook, engine, agents, 89' winner,
      personalization, Azure close — all 5 criteria covered.
- [ ] States that all data is synthetic; shows repo URL.
