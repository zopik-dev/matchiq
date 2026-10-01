"""Grounding check: reject LLM output with numbers outside the evidence (Phase 3).

Every number token in the text must either appear verbatim in an evidence
string (covers scores like "2-1" and ids like "NGU_11") or match an evidence
number within rounding tolerance.
"""

import re
from typing import Any

#: Leading minus counts as a sign, except after a letter ("minute-23" reads 23).
NUMBER_RE = re.compile(r"(?<![A-Za-z])-?\d+(?:\.\d+)?")

#: Tolerance for rounded evidence numbers ("0.55" for evidence 0.547).
ROUNDING_TOLERANCE = 0.011


class GroundingReport:
    """Result of checking one generated text against its evidence."""

    def __init__(self, ok: bool, violations: list[str]) -> None:
        self.ok = ok
        self.violations = violations

    def __bool__(self) -> bool:
        return self.ok


def _flatten(evidence: dict[str, Any]) -> tuple[list[float], list[str]]:
    numbers: list[float] = []
    strings: list[str] = []
    stack: list[Any] = [evidence]
    while stack:
        item = stack.pop()
        if isinstance(item, bool):
            continue
        if isinstance(item, (int, float)):
            numbers.append(float(item))
        elif isinstance(item, str):
            strings.append(item)
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
    return numbers, strings


def check_grounding(text: str, evidence: dict[str, Any]) -> GroundingReport:
    """Check that every number in ``text`` is grounded in ``evidence``."""
    numbers, strings = _flatten(evidence)
    blob = " | ".join(strings)
    violations: list[str] = []
    for token in NUMBER_RE.findall(text):
        if token and token in blob:
            continue
        try:
            value = float(token)
        except ValueError:
            continue
        if any(abs(value - known) <= ROUNDING_TOLERANCE for known in numbers):
            continue
        violations.append(token)
    return GroundingReport(ok=not violations, violations=violations)
