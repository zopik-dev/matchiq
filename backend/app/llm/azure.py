"""AzureFoundryLLM: Azure OpenAI / Foundry client with graceful fallback (Phase 3).

Configured purely through environment variables — no keys in code::

    MATCHIQ_AZURE_ENDPOINT    https://<resource>.openai.azure.com
    MATCHIQ_AZURE_API_KEY      (secret, never logged)
    MATCHIQ_AZURE_DEPLOYMENT   chat deployment name
    MATCHIQ_AZURE_API_VERSION  e.g. 2024-10-01-preview

Uses only the standard library (no new dependencies). When credentials are
missing, :meth:`available` returns False and the pipeline falls back to
MockLLM. No network calls happen unless this client is explicitly used.
"""

import json
import os
import urllib.request
from typing import Any

from app.llm.base import build_prompt

DEFAULT_API_VERSION = "2024-10-01-preview"


class AzureFoundryLLM:
    """Thin Azure OpenAI chat-completions client behind the BaseLLM interface."""

    name = "azure-foundry"

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout_s: float = 20.0,
    ) -> None:
        self.endpoint = (endpoint or os.environ.get("MATCHIQ_AZURE_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("MATCHIQ_AZURE_API_KEY", "")
        self.deployment = deployment or os.environ.get("MATCHIQ_AZURE_DEPLOYMENT", "")
        self.api_version = os.environ.get("MATCHIQ_AZURE_API_VERSION", api_version)
        self.timeout_s = timeout_s

    def available(self) -> bool:
        """True only when endpoint, key and deployment are all configured."""
        return bool(self.endpoint and self.api_key and self.deployment)

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
        system, user = build_prompt(
            agent=agent, task=task, evidence=evidence, names=names, language=language
        )
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )
        body = json.dumps(
            {
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 120,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "api-key": self.api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload["choices"][0]["message"]["content"]).strip()
