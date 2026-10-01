"""HTTP routes for matches and replay control (Phase 4)."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents import PersonalizeProfile
from app.api.live import LiveSession
from app.engine import AnalyticsEngine, build_storyline
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
    names = {t.id: t.name for t in match.meta.teams}
    engine = AnalyticsEngine(home_id, away_id, names)
    for event in session.events:
        engine.update(event)
    return {
        "meta": match.meta.model_dump(mode="json"),
        "total_events": len(session.events),
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
