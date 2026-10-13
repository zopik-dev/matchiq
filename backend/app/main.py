"""MatchIQ FastAPI application (Phase 4).

Run from ``backend/``::

    uvicorn app.main:app --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.speech import router as speech_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="MatchIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(speech_router)


@app.get("/")
def index() -> dict:
    """Landing pointer so a bare host:port explains itself instead of 404."""
    return {
        "service": "MatchIQ API",
        "version": "0.1.0",
        "dashboard": "http://localhost:5173",
        "health": "/health",
        "docs": "/docs",
        "endpoints": [
            "GET /api/match",
            "GET /api/replay/stream",
            "POST /api/speech/synthesize",
            "POST /api/copilot/ask",
        ],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
