"""Tests for the production-grade Azure AI Foundry client (stdlib only)."""

import json
import urllib.error

import pytest

from app.llm.azure import DEFAULT_DEPLOYMENT, AzureFoundryLLM

LEGACY_VARS = ("MATCHIQ_AZURE_ENDPOINT", "MATCHIQ_AZURE_API_KEY", "MATCHIQ_AZURE_DEPLOYMENT")
FOUNDRY_VARS = (
    "MATCHIQ_AZURE_FOUNDRY_ENDPOINT",
    "MATCHIQ_AZURE_FOUNDRY_API_KEY",
    "MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT",
)


def _clear_env(monkeypatch):
    for var in LEGACY_VARS + FOUNDRY_VARS:
        monkeypatch.delenv(var, raising=False)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _ok_payload(text: str = "Goal! Northgate lead 1-0.") -> dict:
    return {"choices": [{"message": {"content": text}}]}


def test_foundry_available_with_foundry_env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_API_KEY", "secret")
    client = AzureFoundryLLM()
    assert client.available()
    assert client.deployment == DEFAULT_DEPLOYMENT == "gpt-4o"


def test_foundry_unavailable_without_any_env(monkeypatch):
    _clear_env(monkeypatch)
    client = AzureFoundryLLM()
    assert not client.available()
    with pytest.raises(RuntimeError):
        client.generate(agent="explain", task="goal", evidence={}, names={})


def test_foundry_prefers_foundry_over_legacy(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MATCHIQ_AZURE_ENDPOINT", "https://legacy.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_API_KEY", "legacy-key")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_ENDPOINT", "https://foundry.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_API_KEY", "foundry-key")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT", "gpt-4o-mini")
    client = AzureFoundryLLM()
    assert client.endpoint == "https://foundry.openai.azure.com"
    assert client.deployment == "gpt-4o-mini"


def test_foundry_payload_and_grounding_prompt(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_API_KEY", "secret")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT", "gpt-4o")
    seen: dict = {}

    def _fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["api_key"] = request.get_header("Api-key")
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(_ok_payload())

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    text = AzureFoundryLLM().generate(
        agent="explain",
        task="goal",
        evidence={"xg": 0.5, "minute": 23},
        names={"NGU": "Northgate United"},
    )
    assert text == "Goal! Northgate lead 1-0."
    assert seen["url"].startswith("https://example.openai.azure.com/openai/deployments/")
    assert "/gpt-4o/chat/completions" in seen["url"]
    assert seen["api_key"] == "secret"
    system = seen["body"]["messages"][0]["content"]
    assert "ONLY numbers" in system
    assert "Forbidden" in system
    assert "0.5" in seen["body"]["messages"][1]["content"]
    assert seen["body"]["temperature"] == 0.2


def test_foundry_falls_back_to_mock_on_network_failure(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("MATCHIQ_AZURE_FOUNDRY_API_KEY", "secret")

    def _boom(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    text = AzureFoundryLLM().generate(
        agent="explain",
        task="goal",
        evidence={"team_id": "NGU", "minute": 23, "scorer": "NGU_11", "xg": 0.55, "score": "1-0"},
        names={"NGU": "Northgate United", "NGU_11": "Ellis Thornton"},
    )
    # MockLLM template output: grounded, no invented numbers, no exception.
    assert "1-0" in text
    assert "23" in text


def test_foundry_never_touches_network_when_unconfigured(monkeypatch):
    _clear_env(monkeypatch)

    def _boom(*args, **kwargs):
        raise AssertionError("must not touch the network without credentials")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    with pytest.raises(RuntimeError):
        AzureFoundryLLM().generate(agent="explain", task="goal", evidence={}, names={})
