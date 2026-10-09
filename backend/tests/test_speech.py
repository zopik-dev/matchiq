"""Tests for the hybrid speech commentary service (Azure TTS + fallback)."""

import io

from fastapi.testclient import TestClient

from app.config import reload_settings
from app.main import app
from app.speech.service import AzureSpeechService, build_ssml, cache_key


def _service(key: str = "dummy-key", region: str = "westeurope") -> AzureSpeechService:
    return AzureSpeechService(api_key=key, region=region)


def test_ssml_english_voice():
    ssml, voice = build_ssml("Goal for Northgate!", "en", "goal")
    assert voice == "en-GB-RyanNeural"
    assert "en-GB-RyanNeural" in ssml
    assert "Goal for Northgate!" in ssml


def test_ssml_ukrainian_voice():
    ssml, voice = build_ssml("Гол забиває Іствейл!", "uk", None)
    assert voice == "uk-UA-OstapNeural"
    assert "uk-UA-OstapNeural" in ssml


def test_ssml_prosody_goal_vs_tactical():
    excited, _ = build_ssml("What a strike!", "en", "goal")
    assert 'rate="+12%"' in excited
    assert 'pitch="+3%"' in excited
    big_chance, _ = build_ssml("Huge chance!", "en", "big_chance")
    assert 'rate="+12%"' in big_chance
    tactical, _ = build_ssml("The press breaks down in midfield.", "en", "tactical")
    assert 'rate="+0%"' in tactical
    assert "+12%" not in tactical


def test_ssml_escapes_markup():
    ssml, _ = build_ssml("Fish & <chips> breakdown", "en", None)
    assert "&amp;" in ssml
    assert "<chips>" not in ssml


def test_cache_key_differs_by_lang_and_moment():
    assert cache_key("Goal!", "en", "goal") != cache_key("Goal!", "uk", "goal")
    assert cache_key("Goal!", "en", "goal") != cache_key("Goal!", "en", None)
    assert cache_key("Goal!", "en", "goal") == cache_key("Goal!", "en", "goal")


def test_is_available_requires_key():
    assert _service(key="").is_available() is False
    assert _service(key="abc").is_available() is True


def test_synthesize_uses_cache(monkeypatch):
    service = _service()
    calls = {"n": 0}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"ID3fake-mp3-bytes"

    def _fake_urlopen(request, timeout=None):
        calls["n"] += 1
        assert request.full_url.startswith("https://westeurope.tts.speech.microsoft.com/")
        assert request.get_header("Ocp-apim-subscription-key") == "dummy-key"
        assert request.get_header("Content-type") == "application/ssml+xml"
        assert request.get_header("X-microsoft-outputformat") == "audio-16khz-32kbitrate-mono-mp3"
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    first = service.synthesize("Goal!", lang="en", moment_type="goal")
    second = service.synthesize("Goal!", lang="en", moment_type="goal")
    assert first == b"ID3fake-mp3-bytes"
    assert second == first
    assert calls["n"] == 1  # second call served from the in-memory cache
    assert service.cache_size() == 1


def test_synthesize_rejects_empty_and_bad_lang():
    service = _service()
    try:
        service.synthesize("   ", lang="en")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty text")
    try:
        service.synthesize("Hello", lang="de")  # type: ignore[arg-type]
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for bad lang")


def test_endpoint_fallback_when_key_unset(monkeypatch):
    monkeypatch.setenv("MATCHIQ_AZURE_SPEECH_KEY", "")
    monkeypatch.setenv("MATCHIQ_AZURE_SPEECH_REGION", "westeurope")
    reload_settings()
    try:
        client = TestClient(app)
        res = client.post(
            "/api/speech/synthesize",
            json={"text": "Goal!", "lang": "en", "moment_type": "goal"},
        )
        assert res.status_code == 200
        payload = res.json()
        assert payload["status"] == "fallback_client"
        assert payload["reason"] == "azure_speech_not_configured"
    finally:
        monkeypatch.undo()
        reload_settings()


def test_endpoint_returns_audio_when_configured(monkeypatch):
    monkeypatch.setenv("MATCHIQ_AZURE_SPEECH_KEY", "dummy-key")
    monkeypatch.setenv("MATCHIQ_AZURE_SPEECH_REGION", "westeurope")
    reload_settings()

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"ID3fake-mp3-bytes"

    def _fake_urlopen(request, timeout=None):
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    try:
        client = TestClient(app)
        res = client.post(
            "/api/speech/synthesize",
            json={"text": "What a goal!", "lang": "uk"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/mpeg"
        assert res.content == b"ID3fake-mp3-bytes"
    finally:
        monkeypatch.undo()
        reload_settings()


def test_endpoint_rejects_bad_lang(monkeypatch):
    monkeypatch.setenv("MATCHIQ_AZURE_SPEECH_KEY", "dummy-key")
    reload_settings()
    try:
        client = TestClient(app)
        res = client.post("/api/speech/synthesize", json={"text": "Hi", "lang": "de"})
        assert res.status_code == 422
    finally:
        monkeypatch.undo()
        reload_settings()


def test_no_real_network_without_key(monkeypatch):
    """The service raises before any urlopen when unconfigured."""

    def _boom(*args, **kwargs):
        raise AssertionError("must not touch the network without a key")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    service = AzureSpeechService(api_key="")
    try:
        service.synthesize("Goal!", lang="en")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    _ = io.BytesIO(b"ok")
