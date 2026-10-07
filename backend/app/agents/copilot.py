"""Ask MatchIQ: interactive tactical copilot over engine evidence (Phase 5+).

Pipeline per question: parse minute/topic -> ContextAgent attaches engine
numbers -> ExplainAgent-style grounded synthesis (MockLLM copilot templates,
grounding-checked, template fallback) -> PersonalizeAgent formats for the
persona mode and language. Suggested follow-ups are rule-based and localized.
"""

import re
from typing import Any

from app.agents.context_agent import ContextAgent
from app.agents.explain_agent import ExplainAgent
from app.agents.messages import AgentMessage, PersonalizeProfile
from app.agents.personalize_agent import PersonalizeAgent
from app.engine import AnalyticsEngine, build_storyline
from app.engine.schemas import Moment
from app.llm.base import BaseLLM
from app.llm.grounding import check_grounding
from app.llm.mock import MockLLM
from app.models.events import MatchData
from app.simulator.generator import load_match

MINUTE_PATTERNS = [
    re.compile(r"(\d{1,3})\s*(?:'|’|′|th\b|st\b|nd\b|rd\b|-?[йя])", re.IGNORECASE),
    re.compile(r"minute\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"хвилин[аіу]\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"\bat\s*(\d{1,3})\b", re.IGNORECASE),
]

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "goal": ["goal", "score", "scored", "гол", "забив", "забити", "рахунок"],
    "big_chance": ["chance", "xg", "нагод", "шанс", "момент"],
    "pressure_spike": ["press", "пресинг", "тиск", "duel", "відбір"],
    "momentum_swing": ["momentum", "swing", "імпульс", "перелом", "tide", "повернув"],
    "tactical_shift": ["shift", "sub", "tactic", "замін", "тактик", "formation", "схем"],
    "counter": ["counter", "контратак", "transition", "перехід"],
}

FOLLOWUPS: dict[str, dict[str, list[str]]] = {
    "en": {
        "goal": [
            "What was the xG of that chance?",
            "How did the momentum shift after the goal?",
            "Show me the pressure before the goal",
        ],
        "big_chance": [
            "Who created the most chances?",
            "What is the match xG total?",
            "How did the momentum shift after that chance?",
        ],
        "pressure_spike": [
            "Who won the most duels?",
            "Did the press lead to a goal?",
            "How did possession change after the press?",
        ],
        "momentum_swing": [
            "What caused the swing?",
            "Did the score change after the swing?",
            "Who controlled the next 10 minutes?",
        ],
        "tactical_shift": [
            "Who came on and who went off?",
            "Did the formation change help?",
            "What happened in the next 10 minutes?",
        ],
        "counter": [
            "How fast was the transition?",
            "Who started the counter-attack?",
            "What was the xG of the finish?",
        ],
        "general": [
            "Who is on top right now?",
            "Show me the goals",
            "Where is the momentum going?",
        ],
    },
    "uk": {
        "goal": [
            "Який був xG того моменту?",
            "Як змінився імпульс після гола?",
            "Покажи тиск перед голом",
        ],
        "big_chance": [
            "Хто створив найбільше нагод?",
            "Який загальний xG матчу?",
            "Як змінився імпульс після нагоди?",
        ],
        "pressure_spike": [
            "Хто виграв найбільше єдиноборств?",
            "Чи призвів пресинг до гола?",
            "Як змінилося володіння після пресингу?",
        ],
        "momentum_swing": [
            "Що спричинило перелом?",
            "Чи змінився рахунок після перелому?",
            "Хто контролював наступні 10 хвилин?",
        ],
        "tactical_shift": [
            "Хто вийшов, а хто пішов з поля?",
            "Чи допомогла зміна схеми?",
            "Що сталося за наступні 10 хвилин?",
        ],
        "counter": [
            "Наскільки швидким був перехід?",
            "Хто розпочав контратаку?",
            "Який був xG завершення?",
        ],
        "general": [
            "Хто зараз попереду?",
            "Покажи голи",
            "Куди рухається імпульс?",
        ],
    },
}

_match_cache: MatchData | None = None
_engine_cache: AnalyticsEngine | None = None


def get_demo_context() -> tuple[MatchData, AnalyticsEngine]:
    """Load the demo match and run the engine once (cached)."""
    global _match_cache, _engine_cache
    if _match_cache is None or _engine_cache is None:
        from pathlib import Path

        path = Path(__file__).resolve().parents[3] / "data" / "samples" / "sample_demo_seed42.json"
        _match_cache = load_match(path)
        home_id = _match_cache.meta.teams[0].id
        away_id = _match_cache.meta.teams[1].id
        names = _match_cache.meta.display_names()
        _engine_cache = AnalyticsEngine(home_id, away_id, names)
        for event in _match_cache.events:
            _engine_cache.update(event)
    return _match_cache, _engine_cache


def parse_question(query: str) -> dict[str, Any]:
    """Extract an optional minute (0-90) and a topic key from free text."""
    minute: int | None = None
    for pattern in MINUTE_PATTERNS:
        found = pattern.search(query)
        if found:
            minute = max(0, min(90, int(found.group(1))))
            break
    lowered = query.lower()
    topic = "general"
    for key, words in TOPIC_KEYWORDS.items():
        if any(w in lowered for w in words):
            topic = key
            break
    return {"minute": minute, "topic": topic}


def _score_at(moments: list[Moment], minute: int, home_id: str) -> dict[str, int]:
    score = {home_id: 0, "away": 0}
    for moment in moments:
        if moment.type == "goal" and moment.minute <= minute and moment.team_id:
            key = home_id if moment.team_id == home_id else "away"
            score[key] += 1
    return score


def find_moment(moments: list[Moment], topic: str, minute: int | None) -> Moment | None:
    """Pick the most relevant moment: topic match near the minute, else nearest."""
    want = None if topic in ("general", "counter") else topic
    if topic == "counter":
        want = "goal"
    candidates = [m for m in moments if want is None or m.type == want]
    if not candidates:
        candidates = moments
    if minute is None:
        return candidates[-1] if candidates else None
    near = [m for m in candidates if abs(m.minute - minute) <= 5]
    pool = near or candidates
    return min(pool, key=lambda m: abs(m.minute - minute))


def answer_question(
    query: str,
    mode: str = "fan",
    language: str = "en",
    llm: BaseLLM | None = None,
) -> dict[str, Any]:
    """Answer a tactical question, grounded strictly in engine evidence."""
    lang = language if language in ("en", "uk") else "en"
    match, engine = get_demo_context()
    home_id = match.meta.teams[0].id
    away_id = match.meta.teams[1].id
    names = match.meta.display_names()
    parsed = parse_question(query)
    minute = parsed["minute"]
    topic = parsed["topic"]

    moment = find_moment(engine.moments, topic, minute)
    at_minute = minute if minute is not None else (moment.minute if moment else 0)
    stats = engine.samples.get(at_minute) or engine.state.window_stats(5)
    segments = build_storyline(engine.samples, engine.moments, home_id, away_id, names)
    segment = next((s for s in segments if s.start_minute <= at_minute <= s.end_minute), None)
    score = _score_at(engine.moments, at_minute, home_id)

    client: BaseLLM = llm or MockLLM()
    if moment is not None:
        context = ContextAgent().handle(
            moment, stats, engine.state.score, segment, f"copilot-{moment.id}"
        )
        evidence = ExplainAgent(client, lang).llm_evidence(moment, context)
        task = moment.type
    else:
        home_stats = stats.teams[home_id]
        evidence = {
            "team_id": home_id,
            "minute": at_minute,
            "moment_type": "general",
            "possession_pct": home_stats.possession_pct,
            "pass_accuracy_pct": home_stats.pass_accuracy_pct,
            "momentum": stats.momentum[home_id],
            "tempo_per_min": stats.tempo_per_min,
            "score_home": score[home_id],
            "score_away": score["away"],
            "score": f"{score[home_id]}-{score['away']}",
            "segment": segment.title if segment else None,
        }
        context = AgentMessage(
            id="copilot-general",
            kind="context.attached",
            sender="context",
            payload={},
            evidence=dict(evidence),
        )
        task = "general"

    text: str | None = None
    try:
        if client.available():
            candidate = client.generate(
                agent="copilot", task=task, evidence=evidence, names=names, language=lang
            )
            if check_grounding(candidate, evidence):
                text = candidate
    except Exception:  # noqa: BLE001 - any LLM failure falls back to template
        text = None
    if text is None:
        text = _fallback_text(moment, evidence, names, lang)

    profile = PersonalizeProfile(mode=mode, language=lang)  # type: ignore[arg-type]
    story = AgentMessage(
        id="copilot-story",
        kind="story.line",
        sender="story",
        moment_id=moment.id if moment else None,
        payload={"text": text},
        evidence=dict(evidence),
    )
    personal = PersonalizeAgent(profile).handle_line(story, names, "copilot-final")
    answer = str(personal.payload["text"]) if personal else text

    cutoff = at_minute * 60
    relevant = [
        {
            "minute": e.minute,
            "timestamp_s": e.timestamp_s,
            "type": e.type.value,
            "team_id": e.team_id,
            "player_id": e.player_id,
            "x": e.x,
            "y": e.y,
            "xg": e.xg,
        }
        for e in match.events
        if e.timestamp_s <= cutoff
    ][-5:]

    return {
        "answer": answer,
        "evidence": evidence,
        "relevant_events": relevant,
        "suggested_followups": FOLLOWUPS[lang].get(topic, FOLLOWUPS[lang]["general"]),
    }


def _fallback_text(
    moment: Moment | None, evidence: dict[str, Any], names: dict[str, str], lang: str
) -> str:
    team = names.get(str(evidence.get("team_id", "")), "-")
    minute = evidence.get("minute", "?")

    def who(key: str) -> str:
        raw = evidence.get(key)
        return names.get(str(raw), str(raw)) if raw else "-"

    if moment is not None and moment.type == "goal":
        if lang == "uk":
            return (
                f"{who('scorer')} забиває за {team} на {minute}-й хвилині "
                f"(рахунок {evidence.get('score')})."
            )
        score = evidence.get("score")
        return f"{who('scorer')} scores for {team} in minute {minute} (now {score})."
    if lang == "uk":
        after = evidence.get("momentum", evidence.get("momentum_home_after", "?"))
        return f"{team}: імпульс {after} на {minute}-й хвилині."
    after = evidence.get("momentum", evidence.get("momentum_home_after", "?"))
    return f"{team}: momentum {after} at minute {minute}."
