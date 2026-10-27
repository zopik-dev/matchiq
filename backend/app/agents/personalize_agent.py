"""PersonalizeAgent: analyst / fan / beginner, EN/UK, club, focus (Phase 3).

Pure rule-based formatting — no LLM, so personalization can never invent
numbers. Mode changes the framing, language switches fixed strings, the
favorite club gets top billing, and player-focus mode filters to lines
involving that player.
"""

from app.agents.messages import AgentMessage, PersonalizeProfile

_MODE_PREFIX: dict[str, str] = {
    "analyst": "ANALYST",
    "fan": "What a moment!",
    "beginner": "In simple terms:",
}

_XG_GLOSSARY = " (xG means chance quality: 1.0 is a certain goal)"

_FAV_LINE = "Your club. "

_RECAP_HEAD = "Full-time recap:"


def _xg_glossary(text: str, language: str = "en") -> str:
    if "xG" in text and "chance quality" not in text:
        return text + _XG_GLOSSARY
    return text


class PersonalizeAgent:
    """Deterministic formatter over story lines and the recap."""

    name = "personalize"

    def __init__(self, profile: PersonalizeProfile) -> None:
        self.profile = profile

    def handle_line(
        self, line: AgentMessage, names: dict[str, str], message_id: str
    ) -> AgentMessage | None:
        """Format one story line; None means filtered out by player focus."""
        focus = self.profile.player_focus
        if focus:
            blob = " ".join(
                str(v)
                for v in (
                    line.evidence.get("scorer"),
                    line.evidence.get("player"),
                    line.evidence.get("player_off"),
                    line.evidence.get("player_on"),
                )
                if v
            )
            if focus not in blob:
                return None
        text = str(line.payload.get("text", ""))
        lang = "en"
        if self.profile.mode == "analyst":
            text = f"[{_MODE_PREFIX['analyst']}] {text}"
        elif self.profile.mode == "fan":
            text = f"{_MODE_PREFIX['fan']} {text}"
        else:
            text = _xg_glossary(f"{_MODE_PREFIX['beginner']} {text}", lang)
        fav = self.profile.favorite_club
        if fav and line.evidence.get("team_id") == fav:
            text = f"{_FAV_LINE}{text}"
        _ = names
        return AgentMessage(
            id=message_id,
            kind="personalized",
            sender="personalize",
            moment_id=line.moment_id,
            payload={"text": text, "mode": self.profile.mode, "language": lang},
            evidence=dict(line.evidence),
        )

    def handle_recap(
        self, recap: AgentMessage, names: dict[str, str], message_id: str
    ) -> AgentMessage:
        """Format the recap; always kept even under player focus."""
        lang = "en"
        text = f"{_RECAP_HEAD} {recap.payload.get('text', '')}"
        fav = self.profile.favorite_club
        if fav and fav in names:
            text = f"{_FAV_LINE}{text}"
        return AgentMessage(
            id=message_id,
            kind="personalized",
            sender="personalize",
            payload={"text": text, "mode": self.profile.mode, "language": lang},
            evidence=dict(recap.evidence),
        )
