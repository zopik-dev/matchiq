"""In-memory match store: match meta, agent outputs, handoff trace (Phase 3)."""

from typing import Any


class InMemoryStore:
    """Ephemeral store for offline runs, CI and tests."""

    def __init__(self) -> None:
        self._meta: dict[str, dict[str, Any]] = {}
        self._outputs: dict[str, list[dict[str, Any]]] = {}
        self._trace: dict[str, list[dict[str, Any]]] = {}

    def save_match(self, match_id: str, meta: dict[str, Any]) -> None:
        self._meta[match_id] = meta
        self._outputs.setdefault(match_id, [])
        self._trace.setdefault(match_id, [])

    def record_output(self, match_id: str, moment_id: str, output: dict[str, Any]) -> None:
        self._outputs.setdefault(match_id, []).append({"moment_id": moment_id, **output})

    def append_handoff(self, match_id: str, handoff: dict[str, Any]) -> None:
        self._trace.setdefault(match_id, []).append(handoff)

    def get_trace(self, match_id: str) -> list[dict[str, Any]]:
        return list(self._trace.get(match_id, []))

    def get_outputs(self, match_id: str) -> list[dict[str, Any]]:
        return list(self._outputs.get(match_id, []))

    def clear(self, match_id: str) -> None:
        self._meta.pop(match_id, None)
        self._outputs.pop(match_id, None)
        self._trace.pop(match_id, None)
