"""LLM abstraction: client interface shared by Mock and Azure clients (Phase 3).

The interface is evidence-first: every call carries the engine ``evidence``
payload, and implementations must only verbalise those numbers. A separate
grounding check (`app.llm.grounding`) enforces this after generation.
"""

from typing import Any, Protocol


class BaseLLM(Protocol):
    """Minimal LLM client interface for MatchIQ agents."""

    name: str

    def available(self) -> bool:
        """Return True when this client can serve requests right now."""
        ...

    def generate(
        self,
        *,
        agent: str,
        task: str,
        evidence: dict[str, Any],
        names: dict[str, str],
        language: str = "en",
    ) -> str:
        """Generate text for ``agent``/``task`` using only ``evidence`` numbers."""
        ...


def build_prompt(
    *,
    agent: str,
    task: str,
    evidence: dict[str, Any],
    names: dict[str, str],
    language: str = "en",
) -> tuple[str, str]:
    """Build (system, user) prompts that forbid inventing numbers.

    Shared by all real LLM clients so grounding rules live in one place.
    """
    system = (
        "You are a football broadcast assistant. You receive a JSON evidence "
        "payload with the ONLY numbers you may use. Rules: use numbers exactly "
        "as given (rounding to 2 decimals allowed); never invent scores, minutes, "
        "percentages or statistics; if a number is missing, omit it. "
        "Reply in English."
    )
    user = (
        f"Agent: {agent}\nTask: {task}\nTeams: {names}\nEvidence: {evidence}\n"
        "Write one concise broadcast line."
    )
    return system, user
