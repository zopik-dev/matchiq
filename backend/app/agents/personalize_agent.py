"""PersonalizeAgent: analyst / fan / beginner, EN/UK, club, focus (Phase 3).

Pure rule-based formatting — no LLM, so personalization can never invent
numbers. Mode changes the framing, language switches fixed strings, the
favorite club gets top billing, and player-focus mode filters to lines
involving that player.
"""

from app.agents.messages import AgentMessage, PersonalizeProfile

_MODE_PREFIX: dict[str, dict[str, str]] = {
    "analyst": {"en": "ANALYST", "uk": "АНАЛІТИКА"},
    "fan": {"en": "What a moment!", "uk": "Який момент!"},
    "beginner": {"en": "In simple terms:", "uk": "Простими словами:"},
}

_XG_GLOSSARY = {
    "en": " (xG means chance quality: 1.0 is a certain goal)",
    "uk": " (xG — якість моменту: 1.0 означає неминучий гол)",
}

_FAV_LINE = {"en": "Your club. ", "uk": "Ваш клуб. "}

_RECAP_HEAD = {"en": "Full-time recap:", "uk": "Підсумок матчу:"}


def _xg_glossary(text: str, language: str) -> str:
    if "xG" in text and "chance quality" not in text and "якість моменту" not in text:
        return text + _XG_GLOSSARY[language]
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
        lang = self.profile.language
        if self.profile.mode == "analyst":
            text = f"[{_MODE_PREFIX['analyst'][lang]}] {text}"
        elif self.profile.mode == "fan":
            text = f"{_MODE_PREFIX['fan'][lang]} {text}"
        else:
            text = _xg_glossary(f"{_MODE_PREFIX['beginner'][lang]} {text}", lang)
        fav = self.profile.favorite_club
        if fav and line.evidence.get("team_id") == fav:
            text = f"{_FAV_LINE[lang]}{text}"
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
        lang = self.profile.language
        text = f"{_RECAP_HEAD[lang]} {recap.payload.get('text', '')}"
        fav = self.profile.favorite_club
        if fav and fav in names:
            text = f"{_FAV_LINE[lang]}{text}"
        return AgentMessage(
            id=message_id,
            kind="personalized",
            sender="personalize",
            payload={"text": text, "mode": self.profile.mode, "language": lang},
            evidence=dict(recap.evidence),
        )
