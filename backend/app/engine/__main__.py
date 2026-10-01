"""CLI for the Phase 2 analytics engine.

Run from ``backend/``::

    python -m app.engine feed
    python -m app.engine feed --file ../data/samples/sample_demo_seed42.json
"""

import argparse
from pathlib import Path

from app.engine import AnalyticsEngine, build_storyline
from app.simulator.generator import load_match

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FILE = REPO_ROOT / "data" / "samples" / "sample_demo_seed42.json"


def cmd_feed(args: argparse.Namespace) -> int:
    match = load_match(args.file)
    home_id, away_id = match.meta.teams[0].id, match.meta.teams[1].id
    names = {t.id: t.name for t in match.meta.teams}
    engine = AnalyticsEngine(home_id, away_id, names)

    print(f"match {match.meta.match_id}: {names[home_id]} vs {names[away_id]}")
    print("--- live insight feed ---")
    for event in match.events:
        for moment in engine.update(event):
            print(f"[{moment.minute:02d}m] {moment.title}")
    print("--- storyline ---")
    segments = build_storyline(engine.samples, engine.moments, home_id, away_id, names)
    for segment in segments:
        print(
            f"{segment.start_minute:02d}-{segment.end_minute:02d} "
            f"{segment.title} "
            f"(poss {segment.evidence['avg_possession_home']:.0f}/"
            f"{segment.evidence['avg_possession_away']:.0f})"
        )
    score = engine.state.score
    print(f"final score {names[home_id]} {score[home_id]}-{score[away_id]} {names[away_id]}")
    print(f"{len(engine.moments)} moments, {len(segments)} segments")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.engine", description="MatchIQ deterministic analytics engine"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    feed = sub.add_parser("feed", help="print the live insight feed and storyline")
    feed.add_argument("--file", default=str(DEFAULT_FILE), help="match JSON to analyse")
    feed.set_defaults(func=cmd_feed)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
