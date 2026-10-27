"""MockLLM: fast, deterministic, offline template generator (Phase 3).

Used for CI, tests and laptop development. Every template slot is filled from
the evidence payload only, so output is grounded by construction. English
templates are provided.
"""

from typing import Any

_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "explain": {
        "en": {
            "goal": "{scorer} scores for {team} in minute {minute}. xG {xg}, score now {score}.",
            "big_chance": "{player} with a big chance for {team} in minute {minute}: xG {xg}.",
            "pressure_spike": (
                "{team} pressing hard: {pressure_events} duels in 5 minutes, "
                "{opponent} managed {opponent_pressure_events}."
            ),
            "momentum_swing": "Momentum swings to {team}: home index now {after} (was {before}).",
            "tactical_shift": "{team} change in minute {minute}: {off} off, {on} on.",
        },
    },
    "story": {
        "en": {
            "goal": "Goal! {team} make it {score} through {scorer} (minute {minute}).",
            "big_chance": "{team} knock on the door as {player} tests the keeper.",
            "pressure_spike": "{team} turn up the heat without the ball.",
            "momentum_swing": "The tide turns towards {team}.",
            "tactical_shift": "{team} reshuffle with fresh legs ({off} for {on}).",
        },
    },
    "copilot": {
        "en": {
            "goal": (
                "Because {scorer} finished a {xg} xG chance for {team} "
                "in minute {minute}, making it {score}."
            ),
            "big_chance": (
                "Because {player} tested the keeper for {team} in minute {minute} with xG {xg}."
            ),
            "pressure_spike": (
                "Because {team} logged {pressure_events} duels in 5 minutes "
                "against {opponent_pressure_events} from the opponent."
            ),
            "momentum_swing": (
                "Because the home index moved to {after} (from {before}), favoring {team}."
            ),
            "tactical_shift": (
                "Because {team} changed shape in minute {minute}: {off} off, {on} on."
            ),
            "general": (
                "At minute {minute}, {team} holds {possession}% possession "
                "with momentum {momentum}."
            ),
        },
    },
}


class MockLLM:
    """Deterministic offline LLM replacement."""

    name = "mock"

    def available(self) -> bool:
        return True

    def generate(
        self,
        *,
        agent: str,
        task: str,
        evidence: dict[str, Any],
        names: dict[str, str],
        language: str = "en",
    ) -> str:
        group = _TEMPLATES.get(agent, _TEMPLATES["explain"])["en"]
        template = group.get(task, "{team} update in minute {minute}.")
        slots = _slots(evidence, names)
        try:
            return template.format(**slots)
        except KeyError:
            return f"Update in minute {slots.get('minute', '?')}."


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return "-"
    return str(value)


def _slots(evidence: dict[str, Any], names: dict[str, str]) -> dict[str, str]:
    def team(key: str) -> str:
        team_id = evidence.get(key)
        return names.get(team_id, str(team_id)) if team_id else "-"

    def person(key: str) -> str:
        player_id = evidence.get(key)
        if not player_id:
            return "-"
        return names.get(str(player_id), str(player_id))

    return {
        "team": team("team_id") if "team_id" in evidence else team("scorer_team"),
        "scorer": person("scorer"),
        "player": person("player"),
        "minute": _fmt(evidence.get("minute")),
        "xg": _fmt(evidence.get("xg")),
        "score": _fmt(evidence.get("score")),
        "pressure_events": _fmt(evidence.get("pressure_events")),
        "opponent": team("opponent_id") if "opponent_id" in evidence else "-",
        "opponent_pressure_events": _fmt(evidence.get("opponent_pressure_events")),
        "after": _fmt(evidence.get("momentum_home_after")),
        "before": _fmt(evidence.get("momentum_home_before")),
        "off": person("player_off"),
        "on": person("player_on"),
        "possession": _fmt(evidence.get("possession_pct")),
        "momentum": _fmt(evidence.get("momentum")),
    }
