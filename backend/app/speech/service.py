"""Azure AI Speech TTS client with in-memory caching (stdlib only).

Configured purely through environment variables — no keys in code::

    MATCHIQ_AZURE_SPEECH_KEY     (secret, never logged)
    MATCHIQ_AZURE_SPEECH_REGION  e.g. westeurope (default)

Uses only :mod:`urllib.request` (zero heavy binary dependencies). When the
key is missing, :meth:`AzureSpeechService.is_available` returns False and the
API layer answers with a ``fallback_client`` hint so the browser uses its
built-in Web Speech API instead. No network calls happen unless configured.
"""

import hashlib
import os
import urllib.request
import xml.sax.saxutils as saxutils

VOICES: dict[str, str] = {
    "en": "en-GB-RyanNeural",
}

OUTPUT_FORMAT = "audio-16khz-32kbitrate-mono-mp3"

#: Moment types that get heightened matchday excitement in the SSML prosody.
EXCITED_MOMENTS = frozenset({"goal", "big_chance"})


def _voice_for(lang: str) -> str:
    return VOICES.get(lang, VOICES["en"])


def build_ssml(text: str, lang: str, moment_type: str | None = None) -> tuple[str, str]:
    """Build the SSML payload and voice name for a commentary line.

    Goals and big chances are wrapped in an excited prosody
    (``rate="+12%" pitch="+3%"``); tactical analysis keeps a neutral rate.
    Returns ``(ssml, voice_name)``.
    """
    voice = _voice_for(lang)
    locale = "en-GB"
    safe = saxutils.escape(text)
    if moment_type in EXCITED_MOMENTS:
        body = f'<prosody rate="+12%" pitch="+3%">{safe}</prosody>'
    else:
        body = f'<prosody rate="+0%">{safe}</prosody>'
    ssml = (
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice xml:lang='{locale}' xml:gender='Male' name='{voice}'>"
        f"{body}</voice></speak>"
    )
    return ssml, voice


def cache_key(text: str, lang: str, moment_type: str | None) -> str:
    """MD5 key for the in-memory MP3 cache."""
    raw = f"{text}\x00{lang}\x00{moment_type or ''}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class AzureSpeechService:
    """Thin Azure Speech TTS client with a dict-based MP3 cache."""

    def __init__(
        self,
        api_key: str | None = None,
        region: str | None = None,
        timeout_s: float = 15.0,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.environ.get("MATCHIQ_AZURE_SPEECH_KEY", "")
        )
        self.region = region or os.environ.get("MATCHIQ_AZURE_SPEECH_REGION", "westeurope")
        self.timeout_s = timeout_s
        self._cache: dict[str, bytes] = {}

    def is_available(self) -> bool:
        """True only when a Speech API key is configured."""
        return bool(self.api_key)

    @property
    def endpoint(self) -> str:
        return f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def synthesize(self, text: str, lang: str = "en", moment_type: str | None = None) -> bytes:
        """Synthesize ``text`` to MP3 bytes, using the cache when possible."""
        if not self.is_available():
            raise RuntimeError("Azure Speech is not configured (missing API key)")
        if lang != "en":
            raise ValueError("lang must be en")
        cleaned = " ".join(text.split())
        if not cleaned:
            raise ValueError("text must be non-empty")
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000]
        key = cache_key(cleaned, lang, moment_type)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        ssml, _ = build_ssml(cleaned, lang, moment_type)
        request = urllib.request.Request(
            self.endpoint,
            data=ssml.encode("utf-8"),
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            audio = response.read()
        self._cache[key] = audio
        return audio

    def cache_size(self) -> int:
        return len(self._cache)

    def clear_cache(self) -> None:
        self._cache.clear()
