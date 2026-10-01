"""Tests for the replay engine (speed, pause, seek)."""

import asyncio
import time

import pytest

from app.simulator.generator import generate_match
from app.simulator.replay import ReplayEngine


def _run(coro):
    return asyncio.run(coro)


def _collect(engine: ReplayEngine):
    async def _all():
        return [e async for e in engine]

    return _run(_all())


def test_instant_replay_yields_all_in_order():
    match = generate_match(42, "demo")
    events = _collect(ReplayEngine(match.events, speed=0))
    assert [e.event_id for e in events] == [e.event_id for e in match.events]


def test_slow_replay_still_ordered_but_takes_time():
    match = generate_match(42, "demo")
    engine = ReplayEngine(match.events[:5], speed=1000)
    started = time.monotonic()
    events = _collect(engine)
    assert time.monotonic() - started < 5
    assert len(events) == 5


def test_seek_jumps_to_minute():
    match = generate_match(42, "demo")
    engine = ReplayEngine(match.events, speed=0)
    index = engine.seek(80)
    assert match.events[index].timestamp_s >= 80 * 60
    rest = _collect(engine)
    assert rest and rest[0].timestamp_s >= 80 * 60
    with pytest.raises(ValueError):
        engine.seek(-1)


def test_pause_and_resume():
    async def _scenario():
        match = generate_match(42, "demo")
        engine = ReplayEngine(match.events[:10], speed=0)
        engine.pause()
        assert engine.is_paused
        seen: list = []

        async def _drain():
            async for event in engine:
                seen.append(event)

        task = asyncio.create_task(_drain())
        await asyncio.sleep(0.05)
        assert seen == []  # nothing flows while paused
        engine.resume()
        await task
        return seen

    seen = _run(_scenario())
    assert len(seen) == 10


def test_negative_speed_rejected():
    match = generate_match(42, "demo")
    with pytest.raises(ValueError):
        ReplayEngine(match.events, speed=-1)
