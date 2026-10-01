"""CLI for the Phase 1 simulator.

Run from ``backend/``::

    python -m app.simulator generate --seed 42 --scenario demo
    python -m app.simulator replay --speed 60
"""

import argparse
import asyncio
from pathlib import Path

from app.simulator.generator import generate_match, load_match, save_match
from app.simulator.replay import ReplayEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLES_DIR = REPO_ROOT / "data" / "samples"


def _default_sample_path(seed: int, scenario: str) -> Path:
    return SAMPLES_DIR / f"match_{seed}_{scenario}.json"


def _parse_speed(raw: str) -> float:
    if raw.strip().lower() == "instant":
        return 0.0
    speed = float(raw)
    if speed < 0:
        raise ValueError("speed must be >= 0 or 'instant'")
    return speed


def cmd_generate(args: argparse.Namespace) -> int:
    match = generate_match(args.seed, args.scenario)
    out = Path(args.out) if args.out else _default_sample_path(args.seed, args.scenario)
    saved = save_match(match, out)
    goals = sum(1 for e in match.events if e.type.value == "goal")
    print(f"generated {len(match.events)} events, {goals} goals (seed={args.seed})")
    print(f"wrote {saved}")
    return 0


async def _replay(path: Path, speed: float, seek: float, limit: int) -> int:
    match = load_match(path)
    engine = ReplayEngine(match.events, speed=speed)
    engine.seek(seek)
    shown = 0
    async for event in engine:
        minute = int(event.timestamp_s // 60)
        second = int(event.timestamp_s % 60)
        actor = event.player_id or "-"
        print(
            f"[{minute:02d}:{second:02d}] {event.type.value:16s} {event.team_id or '-':4s} {actor}"
        )
        shown += 1
        if 0 < limit <= shown:
            break
    goals = sum(1 for e in match.events if e.type.value == "goal")
    print(f"done: {shown} events shown ({len(match.events)} total, {goals} goals)")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    if args.file:
        path = Path(args.file)
    else:
        path = _default_sample_path(args.seed, args.scenario)
    return asyncio.run(_replay(path, _parse_speed(args.speed), args.seek, args.limit))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.simulator", description="MatchIQ synthetic match simulator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a deterministic synthetic match")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--scenario", default="demo")
    gen.add_argument("--out", default=None, help="output JSON path")
    gen.set_defaults(func=cmd_generate)

    rep = sub.add_parser("replay", help="replay a generated match file")
    rep.add_argument("--speed", default="60", help="match-seconds per real second, or 'instant'")
    rep.add_argument("--file", default=None, help="match JSON to replay")
    rep.add_argument("--seed", type=int, default=42)
    rep.add_argument("--scenario", default="demo")
    rep.add_argument("--seek", type=float, default=0.0, help="start minute")
    rep.add_argument("--limit", type=int, default=0, help="max events to show (0 = all)")
    rep.set_defaults(func=cmd_replay)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
