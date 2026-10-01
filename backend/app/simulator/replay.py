"""Async replay engine for synthetic matches (Phase 1).

Streams events in timestamp order with a speed multiplier, pause/resume and
seek-to-minute. ``speed`` is match-seconds per real second; ``0`` means
instant (no sleeping), which is what tests and fast demos use.
"""

import asyncio
import bisect
from collections.abc import AsyncIterator

from app.models.events import Event


class ReplayEngine:
    """Replay a fixed event list in timestamp order."""

    def __init__(self, events: list[Event], speed: float = 1.0) -> None:
        if speed < 0:
            raise ValueError("speed must be >= 0 (0 = instant)")
        self._events = sorted(events, key=lambda e: e.timestamp_s)
        self._timestamps = [e.timestamp_s for e in self._events]
        self._speed = speed
        self._index = 0
        self._resumed = asyncio.Event()
        self._resumed.set()

    def __len__(self) -> int:
        return len(self._events)

    @property
    def position(self) -> int:
        """Number of events already yielded."""
        return self._index

    @property
    def speed(self) -> float:
        return self._speed

    def set_speed(self, speed: float) -> None:
        """Change the speed multiplier (0 = instant)."""
        if speed < 0:
            raise ValueError("speed must be >= 0 (0 = instant)")
        self._speed = speed

    def pause(self) -> None:
        """Pause the stream; in-flight iteration blocks until :meth:`resume`."""
        self._resumed.clear()

    def resume(self) -> None:
        """Resume a paused stream."""
        self._resumed.set()

    @property
    def is_paused(self) -> bool:
        return not self._resumed.is_set()

    def seek(self, minute: float) -> int:
        """Jump to the first event at or after ``minute``; returns the index."""
        if minute < 0:
            raise ValueError("minute must be >= 0")
        self._index = bisect.bisect_left(self._timestamps, minute * 60)
        return self._index

    async def stream(self) -> AsyncIterator[Event]:
        """Yield remaining events in order, honouring speed and pause."""
        previous: float | None = None
        while self._index < len(self._events):
            await self._resumed.wait()
            event = self._events[self._index]
            self._index += 1
            if previous is not None and self._speed > 0:
                delay = (event.timestamp_s - previous) / self._speed
                if delay > 0:
                    await asyncio.sleep(delay)
            previous = event.timestamp_s
            yield event

    def __aiter__(self) -> AsyncIterator[Event]:
        return self.stream()
