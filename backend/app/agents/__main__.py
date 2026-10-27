"""CLI for the Phase 3 multi-agent pipeline.

Run from ``backend/``::

    python -m app.agents run
    python -m app.agents run --mode beginner --club NGU --player-focus NGU_10
"""

import argparse
from pathlib import Path

from app.agents import MatchPipeline, PersonalizeProfile
from app.llm import AzureFoundryLLM, MockLLM
from app.simulator.generator import load_match
from app.store import InMemoryStore

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FILE = REPO_ROOT / "data" / "samples" / "sample_demo_seed42.json"


def cmd_run(args: argparse.Namespace) -> int:
    match = load_match(args.file)
    if args.llm == "azure":
        llm: MockLLM | AzureFoundryLLM = AzureFoundryLLM()
        if not llm.available():
            print("azure client not configured; falling back to MockLLM")
            llm = MockLLM()
    else:
        llm = MockLLM()
    profile = PersonalizeProfile(
        mode=args.mode,
        language=args.lang,
        favorite_club=args.club,
        player_focus=args.player_focus,
    )
    pipeline = MatchPipeline(llm=llm, store=InMemoryStore(), profile=profile)
    result = pipeline.run(match)

    print(f"match {result.match_id} through 5 agents ({llm.name})")
    event_handoffs = [h for h in result.trace if h.receiver == "event"]
    moment_handoffs = [h for h in result.trace if h.receiver != "event"]
    print(f"--- handoff trace ({len(event_handoffs)} events validated) ---")
    groups: dict[str, list] = {}
    for handoff in moment_handoffs:
        key = handoff.message_id.rsplit("-", 1)[0]
        groups.setdefault(key, []).append(handoff)
    for key, hops in groups.items():
        worst = "ok"
        if any(not h.ok for h in hops):
            worst = "FAIL"
        elif any(h.degraded for h in hops):
            worst = "degraded"
        chain = " ".join(
            f"{h.sender}->{h.receiver}{'!' if not h.ok else '*' if h.degraded else ''}"
            for h in hops
        )
        print(f"{key}: {chain} [{worst}]")
    print("--- personalized output ---")
    for line in result.lines:
        print(line)
    print("--- recap ---")
    print(result.recap)
    print(
        f"{result.moment_count} moments, {len(result.lines)} lines, "
        f"{result.degraded} degraded, {result.filtered} filtered"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.agents", description="MatchIQ multi-agent pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a match end to end through all agents")
    run.add_argument("--file", default=str(DEFAULT_FILE))
    run.add_argument("--mode", default="fan", choices=["analyst", "fan", "beginner"])
    run.add_argument("--lang", default="en", choices=["en"])
    run.add_argument("--club", default=None)
    run.add_argument("--player-focus", default=None)
    run.add_argument("--llm", default="mock", choices=["mock", "azure"])
    run.set_defaults(func=cmd_run)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
