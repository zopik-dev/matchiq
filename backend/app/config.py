"""Central environment-based configuration (Phase 5, stdlib only).

All secrets come from environment variables — never from code or the repo.
Missing optional credentials simply disable the corresponding integration,
with seamless fallback to offline implementations.
"""

import os
from dataclasses import dataclass, field


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    """All MatchIQ settings, read once from the environment."""

    env: str = field(default_factory=lambda: _get("MATCHIQ_ENV", "local"))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip()
            for o in _get("MATCHIQ_CORS_ORIGINS", "http://localhost:5173").split(",")
            if o.strip()
        )
    )
    # Microsoft Foundry / Azure OpenAI (see backend/app/llm/azure.py).
    azure_endpoint: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_ENDPOINT"))
    azure_api_key: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_API_KEY"))
    azure_deployment: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_DEPLOYMENT"))
    azure_api_version: str = field(
        default_factory=lambda: _get("MATCHIQ_AZURE_API_VERSION", "2024-10-01-preview")
    )
    # Azure AI Foundry inference (preferred over the legacy MATCHIQ_AZURE_* trio).
    foundry_endpoint: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_FOUNDRY_ENDPOINT"))
    foundry_api_key: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_FOUNDRY_API_KEY"))
    foundry_deployment: str = field(
        default_factory=lambda: _get("MATCHIQ_AZURE_FOUNDRY_DEPLOYMENT", "gpt-4o")
    )
    # Azure Cosmos DB for match state (see backend/app/store/cosmos.py).
    cosmos_endpoint: str = field(default_factory=lambda: _get("MATCHIQ_COSMOS_ENDPOINT"))
    cosmos_key: str = field(default_factory=lambda: _get("MATCHIQ_COSMOS_KEY"))
    cosmos_database: str = field(default_factory=lambda: _get("MATCHIQ_COSMOS_DATABASE", "matchiq"))
    cosmos_container: str = field(
        default_factory=lambda: _get("MATCHIQ_COSMOS_CONTAINER", "matches")
    )
    # Optional PostgreSQL URL (alternative behind the same interface).
    database_url: str = field(default_factory=lambda: _get("MATCHIQ_DATABASE_URL"))
    # Azure AI Speech TTS for live broadcast commentary (see backend/app/speech/).
    # Empty key disables Azure and the frontend falls back to Web Speech API.
    azure_speech_key: str = field(default_factory=lambda: _get("MATCHIQ_AZURE_SPEECH_KEY"))
    azure_speech_region: str = field(
        default_factory=lambda: _get("MATCHIQ_AZURE_SPEECH_REGION", "westeurope")
    )

    @property
    def azure_configured(self) -> bool:
        return bool(self.azure_endpoint and self.azure_api_key and self.azure_deployment)

    @property
    def cosmos_configured(self) -> bool:
        use_identity = _get("MATCHIQ_USE_MANAGED_IDENTITY") == "1"
        return bool(self.cosmos_endpoint and (self.cosmos_key or use_identity))


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings (re-read with `reload_settings` in tests)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Drop the cache and re-read the environment."""
    global _settings
    _settings = Settings()
    return _settings
