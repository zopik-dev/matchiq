"""Azure Cosmos DB store behind the MatchStore interface (Phase 5).

Standard-library only: talks to the Cosmos DB REST API with SharedKey
(HMAC-SHA256) auth, or to Microsoft Entra ID via Managed Identity when no key
is configured (`MATCHIQ_USE_MANAGED_IDENTITY=1`, works inside Azure only).

One document per match: ``{"id", "meta", "outputs", "trace"}``. Writes are
read-modify-write upserts — plenty for demo scale. The constructor never
touches the network; failures surface as :class:`CosmosError` on use.
"""

import base64
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote


class CosmosError(RuntimeError):
    """Raised when a Cosmos DB request fails."""


def _rfc1123_now() -> str:
    return datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")


def build_auth_headers(
    *,
    verb: str,
    resource_type: str,
    resource_link: str,
    key: str,
    date: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build SharedKey authorization headers for one Cosmos DB REST call."""
    signature = base64.b64encode(
        hmac.new(
            base64.b64decode(key),
            f"{verb.lower()}\n{resource_type.lower()}\n{resource_link}\n{date}\n\n".encode(),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    headers = {
        "Authorization": f"type=master&ver=1.0&sig={quote(signature, safe='')}",
        "x-ms-date": date,
        "x-ms-version": "2018-12-31",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def fetch_managed_identity_token(resource: str = "https://cosmos.azure.com") -> str:
    """Fetch an AAD token from the Azure IMDS endpoint (in-Azure only)."""
    url = (
        "http://169.254.169.254/metadata/identity/oauth2/token"
        f"?api-version=2018-02-01&resource={quote(resource, safe='')}"
    )
    request = urllib.request.Request(url, headers={"Metadata": "true"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return str(json.loads(response.read().decode("utf-8"))["access_token"])


class CosmosStore:
    """MatchStore on Azure Cosmos DB (SQL API)."""

    def __init__(
        self,
        endpoint: str,
        key: str = "",
        database: str = "matchiq",
        container: str = "matches",
        use_managed_identity: bool = False,
        timeout_s: float = 10.0,
    ) -> None:
        if not endpoint:
            raise ValueError("Cosmos DB endpoint is required")
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.database = database
        self.container = container
        self.use_managed_identity = use_managed_identity or not key
        self.timeout_s = timeout_s
        self._bearer: str | None = None

    @classmethod
    def from_env(cls) -> "CosmosStore":
        """Build from MATCHIQ_COSMOS_* env vars; raises if not configured."""
        from app.config import get_settings

        settings = get_settings()
        if not settings.cosmos_configured:
            raise ValueError("Cosmos DB is not configured (see .env.example)")
        return cls(
            endpoint=settings.cosmos_endpoint,
            key=settings.cosmos_key,
            database=settings.cosmos_database,
            container=settings.cosmos_container,
            use_managed_identity=os.environ.get("MATCHIQ_USE_MANAGED_IDENTITY") == "1",
        )

    # -- HTTP plumbing -------------------------------------------------

    def _headers(self, verb: str, resource_type: str, resource_link: str) -> dict[str, str]:
        if self.use_managed_identity:
            if self._bearer is None:
                self._bearer = fetch_managed_identity_token()
            return {
                "Authorization": f"Bearer {self._bearer}",
                "x-ms-date": _rfc1123_now(),
                "x-ms-version": "2018-12-31",
                "Content-Type": "application/json",
            }
        return build_auth_headers(
            verb=verb,
            resource_type=resource_type,
            resource_link=resource_link,
            key=self.key,
            date=_rfc1123_now(),
        )

    def _request(
        self,
        verb: str,
        path: str,
        resource_type: str,
        resource_link: str,
        body: dict[str, Any] | None = None,
        upsert: bool = False,
    ) -> Any:
        headers = self._headers(verb, resource_type, resource_link)
        if upsert:
            headers["x-ms-documentdb-is-upsert"] = "true"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.endpoint}{path}", data=data, headers=headers, method=verb
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raise CosmosError(f"Cosmos DB {verb} {path} failed: HTTP {exc.code}") from exc

    def _coll_link(self) -> str:
        return f"dbs/{self.database}/colls/{self.container}"

    def _doc_path(self, match_id: str) -> str:
        return f"/{self._coll_link()}/docs/{quote(match_id, safe='')}"

    # -- MatchStore interface ------------------------------------------

    def _read_doc(self, match_id: str) -> dict[str, Any] | None:
        try:
            doc = self._request(
                "GET", self._doc_path(match_id), "docs", f"{self._coll_link()}/docs/{match_id}"
            )
            return dict(doc) if isinstance(doc, dict) else None
        except CosmosError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def _write_doc(self, doc: dict[str, Any]) -> None:
        self._request(
            "POST",
            f"/{self._coll_link()}/docs",
            "docs",
            self._coll_link(),
            body=doc,
            upsert=True,
        )

    def save_match(self, match_id: str, meta: dict[str, Any]) -> None:
        doc = self._read_doc(match_id) or {"id": match_id}
        doc.update({"meta": meta})
        doc.setdefault("outputs", [])
        doc.setdefault("trace", [])
        self._write_doc(doc)

    def record_output(self, match_id: str, moment_id: str, output: dict[str, Any]) -> None:
        doc = self._read_doc(match_id) or {"id": match_id}
        outputs = doc.setdefault("outputs", [])
        outputs.append({"moment_id": moment_id, **output})
        self._write_doc(doc)

    def append_handoff(self, match_id: str, handoff: dict[str, Any]) -> None:
        doc = self._read_doc(match_id) or {"id": match_id}
        trace = doc.setdefault("trace", [])
        trace.append(handoff)
        self._write_doc(doc)

    def get_trace(self, match_id: str) -> list[dict[str, Any]]:
        doc = self._read_doc(match_id)
        return list(doc.get("trace", [])) if doc else []

    def get_outputs(self, match_id: str) -> list[dict[str, Any]]:
        doc = self._read_doc(match_id)
        return list(doc.get("outputs", [])) if doc else []

    def clear(self, match_id: str) -> None:
        try:
            self._request(
                "DELETE",
                self._doc_path(match_id),
                "docs",
                f"{self._coll_link()}/docs/{match_id}",
            )
        except CosmosError as exc:
            if "HTTP 404" not in str(exc):
                raise
