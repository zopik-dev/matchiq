"""Speech synthesis routes: Azure TTS with browser fallback hint (Phase 4+)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.speech import AzureSpeechService

router = APIRouter(prefix="/api/speech")


class SynthesizeBody(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    lang: str = Field(default="en", pattern="^(en|uk)$")
    moment_type: str | None = Field(default=None, max_length=40)


def _service() -> AzureSpeechService:
    settings = get_settings()
    return AzureSpeechService(
        api_key=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )


@router.post("/synthesize", response_model=None)
def synthesize(body: SynthesizeBody) -> Response:
    """Synthesize commentary audio, or hint the browser fallback.

    Returns ``audio/mpeg`` bytes when Azure Speech is configured, otherwise
    HTTP 200 JSON ``{"status": "fallback_client", ...}`` so the frontend
    speaks the same text via the Web Speech API.
    """
    service = _service()
    if not service.is_available():
        return JSONResponse(
            status_code=200,
            content={"status": "fallback_client", "reason": "azure_speech_not_configured"},
        )
    try:
        audio = service.synthesize(body.text, lang=body.lang, moment_type=body.moment_type)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except RuntimeError as exc:
        return JSONResponse(
            status_code=200,
            content={"status": "fallback_client", "reason": str(exc)},
        )
    return Response(content=audio, media_type="audio/mpeg")
