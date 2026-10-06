"""Tests for env config and the Cosmos DB store (mocked HTTP, Phase 5)."""

import io
import json
import urllib.error

import pytest

import app.store.cosmos as cosmos_module
from app.config import reload_settings
from app.store import InMemoryStore, build_store
from app.store.cosmos import CosmosStore, build_auth_headers


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeCosmosServer:
    """In-memory Cosmos DB document endpoint (no network)."""

    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.requests: list = []

    def __call__(self, request, timeout=None):
        method = request.get_method()
        url = request.full_url
        self.requests.append((method, url, dict(request.headers), request.data))
        doc_id = url.rstrip("/").rsplit("/", 1)[-1]
        is_collection = url.rstrip("/").endswith("/docs")
        if method == "GET":
            if doc_id in self.docs:
                return FakeResponse(self.docs[doc_id])
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())
        if method == "POST" and is_collection:
            doc = json.loads(request.data.decode("utf-8"))
            self.docs[doc["id"]] = doc
            return FakeResponse(doc)
        if method == "DELETE":
            if doc_id in self.docs:
                del self.docs[doc_id]
                return FakeResponse({})
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())
        raise AssertionError(f"unexpected {method} {url}")

    def auth_of(self, index=0):
        return self.requests[index][2].get("Authorization", "")


@pytest.fixture()
def server(monkeypatch):
    fake = FakeCosmosServer()
    monkeypatch.setattr(cosmos_module.urllib.request, "urlopen", fake)
    return fake


def _store():
    return CosmosStore(
        endpoint="https://demo.documents.azure.com:443",
        key="C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
        database="matchiq",
        container="matches",
    )


def test_shared_key_auth_header_shape():
    headers = build_auth_headers(
        verb="GET",
        resource_type="docs",
        resource_link="dbs/matchiq/colls/matches/docs/m1",
        key="C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
        date="Tue, 01 Oct 2024 00:00:00 GMT",
    )
    assert headers["Authorization"].startswith("type=master&ver=1.0&sig=")
    assert headers["x-ms-date"].endswith("GMT")


def test_cosmos_roundtrip(server):
    store = _store()
    store.save_match("m1", {"stadium": "Meridian Park"})
    store.record_output("m1", "m0001", {"text": "Goal!"})
    store.append_handoff("m1", {"seq": 1, "ok": True})
    assert store.get_outputs("m1") == [{"moment_id": "m0001", "text": "Goal!"}]
    assert store.get_trace("m1") == [{"seq": 1, "ok": True}]
    assert server.auth_of().startswith("type=master&ver=1.0&sig=")
    assert any(r[0] == "POST" and r[1].endswith("/docs") for r in server.requests), (
        "writes must use upsert POST"
    )


def test_cosmos_clear_is_idempotent(server):
    store = _store()
    store.save_match("m1", {})
    store.clear("m1")
    assert store.get_trace("m1") == []
    store.clear("m1")  # second delete (404) must not raise


def test_cosmos_requires_endpoint():
    with pytest.raises(ValueError):
        CosmosStore(endpoint="")


def test_factory_falls_back_without_credentials(monkeypatch):
    for var in (
        "MATCHIQ_COSMOS_ENDPOINT",
        "MATCHIQ_COSMOS_KEY",
        "MATCHIQ_USE_MANAGED_IDENTITY",
    ):
        monkeypatch.delenv(var, raising=False)
    reload_settings()
    try:
        assert isinstance(build_store(), InMemoryStore)
    finally:
        reload_settings()


def test_factory_builds_cosmos_when_configured(monkeypatch):
    monkeypatch.setenv("MATCHIQ_COSMOS_ENDPOINT", "https://demo.documents.azure.com:443")
    monkeypatch.setenv("MATCHIQ_COSMOS_KEY", "a2V5")
    reload_settings()
    try:
        assert isinstance(build_store(), CosmosStore)
    finally:
        reload_settings()


def test_settings_flags(monkeypatch):
    monkeypatch.setenv("MATCHIQ_CORS_ORIGINS", "http://a:1, http://b:2 ")
    monkeypatch.delenv("MATCHIQ_AZURE_API_KEY", raising=False)
    settings = reload_settings()
    try:
        assert settings.cors_origins == ("http://a:1", "http://b:2")
        assert not settings.azure_configured
        assert not settings.cosmos_configured
    finally:
        reload_settings()
