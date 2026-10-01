"""Storyline segmenter: label match phases from per-minute samples (Phase 2).

Zero LLM. Each minute gets one label from 5-minute trailing stats and nearby
moments; consecutive equal labels merge into segments with start/end minutes.
"""

from app.engine.schemas import Moment, Segment, WindowStats

#: Pass share (0-1) that marks sustained control of a 5-minute window.
CONTROL_SHARE = 0.60

#: Team pressure actions in the trailing 5 minutes that mark a high press,
#: provided the team does not dominate the ball (pressing without possession).
PRESS_SEGMENT_COUNT = 13
PRESS_MAX_SHARE = 0.58

#: Minutes around a moment that the moment's label claims for the storyline.
MOMENT_HALO_MIN = 2

#: Segments shorter than this are absorbed by the previous segment.
MIN_SEGMENT_MIN = 3


def label_minute(
    stats: WindowStats,
    home_id: str,
    away_id: str,
    shifts: list[Moment],
    swings: list[Moment],
) -> tuple[str, str | None]:
    """Return ``(label, team_id)`` for one sampled minute."""
    minute = stats.end_minute
    near_shifts = [s for s in shifts if abs(s.minute - minute) <= MOMENT_HALO_MIN]
    if near_shifts:
        # Overlapping halos (e.g. both teams subbing): the closest shift wins.
        best = min(near_shifts, key=lambda s: (abs(s.minute - minute), s.minute))
        return "tactical_shift", best.team_id
    for swing in swings:
        if abs(swing.minute - minute) <= MOMENT_HALO_MIN:
            return "momentum_swing", swing.team_id
    press_candidates = []
    for team_id in (home_id, away_id):
        team = stats.teams[team_id]
        share = team.possession_pct / 100
        if team.pressure_events >= PRESS_SEGMENT_COUNT and share < PRESS_MAX_SHARE:
            press_candidates.append((team.pressure_events, team_id))
    if press_candidates:
        press_candidates.sort(reverse=True)
        return "high_press", press_candidates[0][1]
    for team_id in (home_id, away_id):
        if stats.teams[team_id].possession_pct / 100 >= CONTROL_SHARE:
            return "control", team_id
    return "balanced", None


def build_storyline(
    samples: dict[int, WindowStats],
    moments: list[Moment],
    home_id: str,
    away_id: str,
    team_names: dict[str, str] | None = None,
) -> list[Segment]:
    """Merge per-minute labels into storyline segments."""
    names = team_names or {}
    shifts = [m for m in moments if m.type == "tactical_shift"]
    swings = [m for m in moments if m.type == "momentum_swing"]
    minutes = sorted(samples)
    if not minutes:
        return []

    runs: list[list] = []  # [label, team_id, start, end]
    for minute in minutes:
        label, team_id = label_minute(samples[minute], home_id, away_id, shifts, swings)
        if runs and runs[-1][0] == label and runs[-1][1] == team_id:
            runs[-1][3] = minute
        else:
            runs.append([label, team_id, minute, minute])

    merged: list[list] = []
    for i, run in enumerate(runs):
        length = run[3] - run[2] + 1
        if length < MIN_SEGMENT_MIN and not merged and i + 1 < len(runs):
            runs[i + 1][2] = run[2]  # fold a leading blip into the next run
            continue
        if merged and length < MIN_SEGMENT_MIN:
            merged[-1][3] = run[3]  # absorb blips into the previous segment
        elif merged and merged[-1][0] == run[0] and merged[-1][1] == run[1]:
            merged[-1][3] = run[3]  # join same-label neighbours back together
        else:
            merged.append(run)

    segments: list[Segment] = []
    for label, team_id, start, end in merged:
        window = [samples[m] for m in range(start, end + 1) if m in samples]
        who = names.get(team_id, team_id) if team_id else "Both sides"
        title = {
            "control": f"{who} in control",
            "high_press": f"{who} high press",
            "tactical_shift": f"{who} tactical shift",
            "momentum_swing": f"Momentum swing to {who}",
            "balanced": "Balanced phase",
        }[label]
        segments.append(
            Segment(
                label=label,  # type: ignore[arg-type]
                team_id=team_id,
                start_minute=start,
                end_minute=end,
                title=title,
                evidence={
                    "avg_possession_home": round(
                        sum(s.teams[home_id].possession_pct for s in window) / len(window),
                        1,
                    ),
                    "avg_possession_away": round(
                        sum(s.teams[away_id].possession_pct for s in window) / len(window),
                        1,
                    ),
                    "max_pressure_home": max(s.teams[home_id].pressure_events for s in window),
                    "max_pressure_away": max(s.teams[away_id].pressure_events for s in window),
                    "xg_home": round(sum(s.teams[home_id].xg_sum for s in window), 2),
                    "xg_away": round(sum(s.teams[away_id].xg_sum for s in window), 2),
                },
            )
        )
    return segments
