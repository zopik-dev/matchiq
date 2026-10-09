"""HTTP routes for matches and replay control (Phase 4)."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents import PersonalizeProfile
from app.agents.copilot import answer_question
from app.api.live import LiveSession
from app.engine import AnalyticsEngine, build_storyline
from app.llm import AzureFoundryLLM, MockLLM
from app.models.events import EventType
from app.simulator.generator import load_match

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_FILE = REPO_ROOT / "data" / "samples" / "sample_demo_seed42.json"

router = APIRouter(prefix="/api")

_session: LiveSession | None = None


def get_session() -> LiveSession:
    """Singleton demo-match session (single-viewer by design)."""
    global _session
    if _session is None:
        _session = LiveSession(load_match(DEMO_FILE))
    return _session


def reset_session() -> None:
    global _session
    _session = None


class SpeedBody(BaseModel):
    speed: float = Field(ge=0)


class SeekBody(BaseModel):
    minute: float = Field(ge=0)


class AskBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    minute: int | None = Field(default=None, ge=0, le=120)
    mode: str = "fan"
    lang: str = "en"


def _profile(mode: str, lang: str, club: str | None, focus: str | None) -> PersonalizeProfile:
    if mode not in ("analyst", "fan", "beginner"):
        raise HTTPException(status_code=422, detail="mode must be analyst|fan|beginner")
    if lang not in ("en", "uk"):
        raise HTTPException(status_code=422, detail="lang must be en|uk")
    return PersonalizeProfile(mode=mode, language=lang, favorite_club=club, player_focus=focus)  # type: ignore[arg-type]


@router.get("/match")
def get_match() -> dict:
    """Match metadata, rosters, precomputed moments, storyline and momentum."""
    session = get_session()
    match = session.match
    home_id = match.meta.teams[0].id
    away_id = match.meta.teams[1].id
    names = match.meta.display_names()
    engine = AnalyticsEngine(home_id, away_id, names)
    for event in session.events:
        engine.update(event)
    shots = [e for e in session.events if e.type in (EventType.SHOT, EventType.GOAL)]
    passes = [e for e in session.events if e.type == EventType.PASS]
    home_passes = sum(1 for e in passes if e.team_id == home_id)
    totals = {
        "xg_home": round(sum(e.xg or 0.0 for e in shots if e.team_id == home_id), 2),
        "xg_away": round(sum(e.xg or 0.0 for e in shots if e.team_id == away_id), 2),
        "poss_home": round(home_passes / len(passes) * 100, 1) if passes else 50.0,
        "poss_away": round((len(passes) - home_passes) / len(passes) * 100, 1) if passes else 50.0,
    }
    # Cumulative per-minute series so the UI shows values "so far", not finals.
    xg_series: list[dict] = []
    poss_series: list[dict] = []
    run_xg = {home_id: 0.0, away_id: 0.0}
    run_pass = {home_id: 0, away_id: 0}
    by_minute: dict[int, list] = {}
    for event in session.events:
        by_minute.setdefault(event.minute, []).append(event)
    for minute in range(0, 91):
        for event in by_minute.get(minute, []):
            if event.type in (EventType.SHOT, EventType.GOAL) and event.team_id:
                run_xg[event.team_id] = run_xg.get(event.team_id, 0.0) + (event.xg or 0.0)
            if event.type == EventType.PASS and event.team_id:
                run_pass[event.team_id] = run_pass.get(event.team_id, 0) + 1
        total_pass = run_pass[home_id] + run_pass[away_id]
        xg_series.append(
            {
                "minute": minute,
                "home": round(run_xg[home_id], 2),
                "away": round(run_xg[away_id], 2),
            }
        )
        poss_series.append(
            {
                "minute": minute,
                "home": round(run_pass[home_id] / total_pass * 100, 1) if total_pass else 50.0,
                "away": round(run_pass[away_id] / total_pass * 100, 1) if total_pass else 50.0,
            }
        )
    return {
        "meta": match.meta.model_dump(mode="json"),
        "total_events": len(session.events),
        "totals": totals,
        "xg_series": xg_series,
        "poss_series": poss_series,
        "moments": [
            {
                "id": m.id,
                "type": m.type,
                "minute": m.minute,
                "timestamp_s": m.timestamp_s,
                "team_id": m.team_id,
                "title": m.title,
                "evidence": m.evidence,
            }
            for m in engine.moments
        ],
        "segments": [
            s.model_dump()
            for s in build_storyline(engine.samples, engine.moments, home_id, away_id, names)
        ],
        "momentum_series": [
            {"minute": minute, "home": stats.momentum[home_id]}
            for minute, stats in sorted(engine.samples.items())
        ],
        "state": session.state(),
    }


@router.get("/replay/state")
def replay_state() -> dict:
    return get_session().state()


@router.post("/replay/play")
def replay_play() -> dict:
    return get_session().play()


@router.post("/replay/pause")
def replay_pause() -> dict:
    return get_session().pause()


@router.post("/replay/speed")
def replay_speed(body: SpeedBody) -> dict:
    try:
        return get_session().set_speed(body.speed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/replay/seek")
def replay_seek(body: SeekBody) -> dict:
    try:
        return get_session().seek(body.minute)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/replay/stream")
async def replay_stream(
    mode: str = Query(default="fan"),
    lang: str = Query(default="en"),
    club: str | None = Query(default=None),
    player_focus: str | None = Query(default=None),
    speed: float | None = Query(default=None, ge=0),
) -> StreamingResponse:
    """SSE live stream: events, momentum, moments, explanations, traces."""
    session = get_session()
    if speed is not None:
        session.set_speed(speed)
    profile = _profile(mode, lang, club, player_focus)
    session.play()  # connecting a viewer (re)starts playback

    async def generate():
        async for kind, payload in session.stream(profile):
            yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/copilot/ask")
def copilot_ask(body: AskBody) -> dict:
    """Answer a tactical question, grounded strictly in engine evidence."""
    if body.mode not in ("analyst", "fan", "beginner"):
        raise HTTPException(status_code=422, detail="mode must be analyst|fan|beginner")
    if body.lang not in ("en", "uk"):
        raise HTTPException(status_code=422, detail="lang must be en|uk")
    azure = AzureFoundryLLM()
    llm = azure if azure.available() else MockLLM()
    query = body.query if body.minute is None else f"{body.query} ({body.minute}')"
    return answer_question(query, mode=body.mode, language=body.lang, llm=llm)


def _check_mode_lang(mode: str, lang: str) -> None:
    if mode not in ("analyst", "fan", "beginner"):
        raise HTTPException(status_code=422, detail="mode must be analyst|fan|beginner")
    if lang not in ("en", "uk"):
        raise HTTPException(status_code=422, detail="lang must be en|uk")


@router.get("/players/{player_id}/telemetry")
def player_telemetry(
    player_id: str,
    mode: str = Query(default="fan"),
    lang: str = Query(default="en"),
) -> dict:
    """Scouting dossier for one player, computed from the event stream."""
    from app.engine.telemetry import player_telemetry as build_dossier

    _check_mode_lang(mode, lang)
    try:
        return build_dossier(get_session().match, player_id, lang=lang, mode=mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/moments/{moment_id}/xray")
def moment_xray(moment_id: str) -> dict:
    """Step-by-step breakdown of a goal: lead-up passes plus the finish."""
    from app.engine.telemetry import goal_xray

    session = get_session()
    match = session.match
    names = match.meta.display_names()
    engine = AnalyticsEngine(match.meta.teams[0].id, match.meta.teams[1].id, names)
    for event in session.events:
        engine.update(event)
    try:
        return goal_xray(match, engine.moments, moment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
