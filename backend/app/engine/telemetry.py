"""Player telemetry and goal X-Ray builders (pure, grounded in event data).

All numbers derive from the synthetic event stream; the insight strings only
verbalise computed values, so a later LLM (or the MockLLM) cannot invent them.
"""

import math

from app.engine.schemas import Moment
from app.engine.state import attack_x
from app.models.events import EventType, MatchData

GRID_X_M = 1.05  # 0-100 grid mapped onto a 105m pitch
GRID_Y_M = 0.68  # ... and a 68m width


def _find_player(match: MatchData, player_id: str):
    for team in match.meta.teams:
        for player in team.roster:
            if player.id == player_id:
                return team, player
    return None, None


def _involvements(match: MatchData, player_id: str):
    return [e for e in match.events if e.player_id == player_id]


def player_telemetry(match: MatchData, player_id: str, lang: str = "en", mode: str = "fan") -> dict:
    """Compute a scouting dossier for one player from the event stream."""
    team, player = _find_player(match, player_id)
    if team is None or player is None:
        raise KeyError(f"unknown player: {player_id}")
    home_id = match.meta.teams[0].id
    touches = _involvements(match, player_id)

    passes = [e for e in touches if e.type == EventType.PASS]
    complete = [e for e in passes if e.outcome.value == "complete"]
    shots = [e for e in touches if e.type in (EventType.SHOT, EventType.GOAL)]
    goals = [e for e in touches if e.type == EventType.GOAL]
    duels = [
        e
        for e in touches
        if e.type in (EventType.TACKLE, EventType.INTERCEPTION, EventType.POSSESSION_CHANGE)
        and e.outcome.value in ("won", "success")
    ]
    xg_total = round(sum(e.xg or 0.0 for e in shots), 2)

    final_third = 0
    for e in passes:
        if e.team_id is None:
            continue
        gx = attack_x(e.team_id, e.period, home_id, match.meta.teams[1].id)
        ax = e.x if gx == 100.0 else 100.0 - e.x
        if ax >= 66.0:
            final_third += 1

    distance_m = 0.0
    top_speed = 0.0
    for prev, cur in zip(touches, touches[1:], strict=False):
        dx = (cur.x - prev.x) * GRID_X_M
        dy = (cur.y - prev.y) * GRID_Y_M
        dist = math.hypot(dx, dy)
        distance_m += dist
        dt = cur.timestamp_s - prev.timestamp_s
        if dt >= 1.0:
            top_speed = max(top_speed, dist / dt * 3.6)
    top_speed = round(min(top_speed, 36.0), 1)

    accuracy = round(len(complete) / len(passes) * 100) if passes else 0
    return {
        "player_id": player.id,
        "name": player.name,
        "number": player.number,
        "position": player.position.value,
        "team_id": team.id,
        "team_name": team.name,
        "touches": len(touches),
        "passes": len(passes),
        "passes_completed": len(complete),
        "pass_accuracy": accuracy,
        "shots": len(shots),
        "xg": xg_total,
        "goals": len(goals),
        "duels_won": len(duels),
        "final_third_entries": final_third,
        "distance_m": round(distance_m),
        "top_speed_kmh": top_speed,
        "insight": _insight(
            lang if lang in ("en", "uk") else "en",
            mode if mode in ("analyst", "fan", "beginner") else "fan",
            player.name,
            team.name,
            str(player.position.value),
            len(passes),
            accuracy,
            xg_total,
            len(goals),
            len(duels),
            final_third,
            round(distance_m),
            top_speed,
        ),
    }


def _insight(
    lang: str,
    mode: str,
    name: str,
    team: str,
    position: str,
    passes: int,
    accuracy: int,
    xg: float,
    goals: int,
    duels: int,
    entries: int,
    distance: int,
    top_speed: float,
) -> str:
    if position == "FW":
        role_en = (
            f"{name} leads the line for {team}: {goals} goal(s) from {xg} xG, "
            f"{entries} final-third entries and {distance}m covered at up to "
            f"{top_speed} km/h."
        )
        role_uk = (
            f"{name} веде атаку {team}: {goals} гол(и) з {xg} xG, "
            f"{entries} входжень у фінальну третину та {distance} м "
            f"на швидкості до {top_speed} км/год."
        )
    elif position == "MF":
        role_en = (
            f"{name} is {team}'s engine room: {passes} passes at {accuracy}% "
            f"accuracy, {entries} final-third entries, {duels} duels won over "
            f"{distance}m."
        )
        role_uk = (
            f"{name} — мотор {team}: {passes} передач з точністю {accuracy}%, "
            f"{entries} входжень у фінальну третину, {duels} виграних "
            f"єдиноборств на {distance} м."
        )
    elif position == "DF":
        role_en = (
            f"{name} anchors the {team} back line: {duels} duels won, "
            f"{passes} passes at {accuracy}% to start attacks, {distance}m covered."
        )
        role_uk = (
            f"{name} тримає оборону {team}: {duels} виграних єдиноборств, "
            f"{passes} передач з точністю {accuracy}%, {distance} м."
        )
    else:
        role_en = (
            f"{name} guards the {team} net with {passes} distributions at {accuracy}% accuracy."
        )
        role_uk = f"{name} захищає ворота {team}: {passes} введень м'яча з точністю {accuracy}%."
    body = role_en if lang == "en" else role_uk
    if mode == "analyst":
        head = {"en": "Tactical read: ", "uk": "Тактичний розбір: "}[lang]
        return head + body
    if mode == "beginner":
        tail = {
            "en": " In short: these numbers describe what they actually did with the ball.",
            "uk": " Простіше кажучи: ці цифри показують, що він реально робив з м'ячем.",
        }[lang]
        return body + tail
    head = {"en": "What a shift! ", "uk": "Який матч! "}[lang]
    return head + body


def _slim(event) -> dict:
    return {
        "event_id": event.event_id,
        "minute": event.minute,
        "timestamp_s": event.timestamp_s,
        "type": event.type.value,
        "team_id": event.team_id,
        "player_id": event.player_id,
        "target_player_id": event.target_player_id,
        "x": event.x,
        "y": event.y,
        "outcome": event.outcome.value,
        "xg": event.xg,
        "shot_speed_kmh": event.shot_speed_kmh,
    }


def goal_xray(match: MatchData, moments: list[Moment], moment_id: str) -> dict:
    """Build the step-by-step breakdown of a goal: lead-up passes + finish."""
    moment = next((m for m in moments if m.id == moment_id), None)
    if moment is None:
        raise KeyError(f"unknown moment: {moment_id}")
    if moment.type != "goal" or not moment.team_id:
        raise ValueError("x-ray is only available for goal moments")
    goal = next(
        (
            e
            for e in match.events
            if e.type == EventType.GOAL
            and e.team_id == moment.team_id
            and abs(e.timestamp_s - moment.timestamp_s) < 1.0
        ),
        None,
    )
    if goal is None:
        raise KeyError(f"no goal event for moment: {moment_id}")
    leadup = [
        e
        for e in match.events
        if e.team_id == moment.team_id
        and e.type == EventType.PASS
        and 0 < goal.timestamp_s - e.timestamp_s <= 75
    ][-5:]
    steps = [_slim(e) | {"step_label": "Build-up"} for e in leadup]
    if steps:
        steps[-1] = {**steps[-1], "step_label": "Key Pass"}
    steps.append(_slim(goal) | {"step_label": "Finish"})
    return {
        "moment_id": moment.id,
        "minute": moment.minute,
        "team_id": moment.team_id,
        "title": moment.title,
        "xg": goal.xg,
        "shot_speed_kmh": goal.shot_speed_kmh,
        "score": moment.evidence.get("score"),
        "steps": steps,
    }
