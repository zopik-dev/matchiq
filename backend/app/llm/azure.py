"""AzureFoundryLLM: production-grade Azure AI Foundry client (Phase 3+).

Configured purely through environment variables — no keys in code::

    MATCHIQ_AZURE_FOUNDRY_ENDPOINT    https://<resource>.openai.azure.com (preferred)
    MATCHIQ_AZURE_FOUNDRY_API_KEY      (secret, never logged)
    MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT   chat deployment name (default: gpt-4o)

Legacy ``MATCHIQ_AZURE_ENDPOINT / _API_KEY / _DEPLOYMENT`` variables are still
honoured as a fallback so existing deployments keep working. Uses only the
standard library (no heavy SDK dependencies). When credentials are missing,
:meth:`available` returns False; when the network fails mid-request the call
falls back to MockLLM (with a warning in the trace log) instead of breaking
the broadcast. No network calls happen unless this client is explicitly used.
"""

import json
import logging
import os
import urllib.request
from typing import Any

from app.llm.base import build_prompt
from app.llm.mock import MockLLM

log = logging.getLogger(__name__)

DEFAULT_DEPLOYMENT = "gpt-4o"
DEFAULT_API_VERSION = "2024-10-01-preview"

#: Appended to every system prompt so production models obey the grounding rule.
GROUNDING_SUFFIX = (
    " Strict grounding: every number in your reply MUST come from the evidence "
    "payload above. Forbidden: inventing scores, minutes, xG, percentages or any "
    "statistic not present in the evidence. If a number is missing, omit it "
    "instead of guessing."
)


def _first(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


class AzureFoundryLLM:
    """Thin Azure AI Foundry chat-completions client behind the BaseLLM interface."""

    name = "azure-foundry"

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout_s: float = 20.0,
    ) -> None:
        self.endpoint = _first(
            (endpoint or "").rstrip("/"),
            os.environ.get("MATCHIQ_AZURE_FOUNDRY_ENDPOINT", "").rstrip("/"),
            os.environ.get("MATCHIQ_AZURE_ENDPOINT", "").rstrip("/"),
        )
        self.api_key = _first(
            api_key or "",
            os.environ.get("MATCHIQ_AZURE_FOUNDRY_API_KEY", ""),
            os.environ.get("MATCHIQ_AZURE_API_KEY", ""),
        )
        self.deployment = _first(
            deployment or "",
            os.environ.get("MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT", ""),
            os.environ.get("MATCHIQ_AZURE_DEPLOYMENT", ""),
            DEFAULT_DEPLOYMENT,
        )
        self.api_version = os.environ.get("MATCHIQ_AZURE_API_VERSION", api_version)
        self.timeout_s = timeout_s

    def available(self) -> bool:
        """True only when endpoint, key and deployment are all configured."""
        return bool(self.endpoint and self.api_key and self.deployment)

    def _payload(
        self,
        *,
        agent: str,
        task: str,
        evidence: dict[str, Any],
        names: dict[str, str],
        language: str,
    ) -> tuple[str, dict[str, Any]]:
        system, user = build_prompt(
            agent=agent, task=task, evidence=evidence, names=names, language=language
        )
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )
        body = {
            "messages": [
                {"role": "system", "content": system + GROUNDING_SUFFIX},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 120,
        }
        return url, body

    def generate(
        self,
        *,
        agent: str,
        task: str,
        evidence: dict[str, Any],
        names: dict[str, str],
        language: str = "en",
    ) -> str:
        if not self.available():
            raise RuntimeError("Azure client is not configured (missing env vars)")
        url, body = self._payload(
            agent=agent, task=task, evidence=evidence, names=names, language=language
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            log.warning("Azure Foundry request failed (%s); falling back to MockLLM", exc)
            return MockLLM().generate(
                agent=agent, task=task, evidence=evidence, names=names, language=language
            )
        return str(payload["choices"][0]["message"]["content"]).strip()
