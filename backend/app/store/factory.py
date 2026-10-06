"""Store factory: Cosmos DB when configured, memory otherwise (Phase 5)."""

from app.store.base import MatchStore
from app.store.cosmos import CosmosStore
from app.store.memory import InMemoryStore


def build_store() -> MatchStore:
    """Return a CosmosStore if credentials exist, else an InMemoryStore."""
    from app.config import get_settings

    if get_settings().cosmos_configured:
        return CosmosStore.from_env()
    return InMemoryStore()
