"""Live replay session: paced SSE streaming over a precomputed pipeline run.

The full agent pipeline runs once per profile (fast, offline, MockLLM); the
session then streams events at the chosen speed and releases each moment's
texts and handoff trace when the playhead reaches it. Single-viewer design:
a new stream takes over from any previous one.
"""

import asyncio
import bisect

from app.agents import MatchPipeline, PersonalizeProfile
from app.agents.messages import Handoff
from app.engine import AnalyticsEngine, build_storyline
from app.llm import MockLLM
from app.models.events import EventType, MatchData
from app.store import build_store


class PreparedRun:
    """One cached pipeline result plus per-minute momentum for streaming."""

    def __init__(self, result, momentum: dict[int, float], segments: list[dict]) -> None:
        self.result = result
        self.momentum = momentum
        self.segments = segments
        self.details_by_id = {d["moment_id"]: d for d in result.details}
        self.trace_by_moment: dict[str, list[dict]] = {}
        for hop in result.trace:
            if isinstance(hop, Handoff):
                payload = hop.model_dump()
            else:
                payload = dict(hop)
            message_id = str(payload.get("message_id", ""))
            if "-context" in message_id or "-explanation" in message_id:
                key = message_id.split("-context")[0].split("-explanation")[0]
                self.trace_by_moment.setdefault(key, []).append(payload)


class LiveSession:
    """Playback state machine for the demo match."""

    def __init__(self, match: MatchData) -> None:
        self.match = match
        self.events = match.events
        self.timestamps = [e.timestamp_s for e in match.events]
        self.playing = False
        self.speed = 60.0
        self.index = 0
        self._wake = asyncio.Event()
        self._wake.clear()
        self._generation = 0
        self._prepared: dict[str, PreparedRun] = {}

    # -- controls ----------------------------------------------------

    def play(self) -> dict:
        self.playing = True
        self._wake.set()
        return self.state()

    def pause(self) -> dict:
        self.playing = False
        self._wake.clear()
        return self.state()

    def set_speed(self, speed: float) -> dict:
        if speed < 0:
            raise ValueError("speed must be >= 0")
        self.speed = speed
        return self.state()

    def seek(self, minute: float) -> dict:
        if minute < 0:
            raise ValueError("minute must be >= 0")
        self.index = bisect.bisect_left(self.timestamps, minute * 60)
        return self.state()

    def state(self) -> dict:
        minute = 0.0
        if self.index > 0:
            minute = self.timestamps[self.index - 1] / 60
        score = {"home": 0, "away": 0}
        home_id = self.match.meta.teams[0].id
        for event in self.events[: self.index]:
            if event.type == EventType.GOAL and event.team_id:
                key = "home" if event.team_id == home_id else "away"
                score[key] += 1
        return {
            "playing": self.playing,
            "speed": self.speed,
            "index": self.index,
            "total": len(self.events),
            "minute": round(minute, 2),
            "score": score,
        }

    # -- preparation -------------------------------------------------

    def prepare(self, profile: PersonalizeProfile) -> PreparedRun:
        key = f"{profile.mode}|{profile.language}|{profile.favorite_club}|{profile.player_focus}"
        cached = self._prepared.get(key)
        if cached is not None:
            return cached
        pipeline = MatchPipeline(llm=MockLLM(), store=build_store(), profile=profile)
        result = pipeline.run(self.match)
        home_id = self.match.meta.teams[0].id
        away_id = self.match.meta.teams[1].id
        names = {t.id: t.name for t in self.match.meta.teams}
        engine = AnalyticsEngine(home_id, away_id, names)
        for event in self.events:
            engine.update(event)
        momentum = {minute: stats.momentum[home_id] for minute, stats in engine.samples.items()}
        segments = [
            s.model_dump()
            for s in build_storyline(engine.samples, engine.moments, home_id, away_id, names)
        ]
        prepared = PreparedRun(result, momentum, segments)
        self._prepared[key] = prepared
        return prepared

    # -- streaming ---------------------------------------------------

    async def stream(self, profile: PersonalizeProfile):
        """Yield (kind, payload) tuples paced by the playback speed."""
        prepared = self.prepare(profile)
        self._generation += 1
        generation = self._generation
        ordered = sorted(
            ((d["moment_id"], d["timestamp_s"]) for d in prepared.result.details),
            key=lambda item: item[1],
        )
        yield ("state", self.state())
        local_index = self.index
        previous_ts = self.timestamps[local_index - 1] if local_index > 0 else 0.0
        emitted: set[str] = set()
        if local_index > 0:
            # Catch-up: the viewer (re)connects mid-match, resend what happened.
            for mid, mts in ordered:
                if mts <= previous_ts:
                    emitted.add(mid)
                    detail = prepared.details_by_id.get(mid)
                    if detail is None:
                        continue
                    yield ("moment", detail)
                    hops = prepared.trace_by_moment.get(mid, [])
                    if hops:
                        yield ("trace", {"moment_id": mid, "hops": hops})
        last_minute = -1
        while local_index < len(self.events):
            if generation != self._generation:
                return
            if local_index != self.index:
                # Seek: resync the playhead without advancing.
                local_index = self.index
                previous_ts = self.timestamps[local_index - 1] if local_index > 0 else 0.0
                cutoff = self.timestamps[local_index - 1] if local_index > 0 else -1.0
                emitted = {mid for mid, ts in ordered if ts <= cutoff}
                last_minute = -1
                yield ("state", self.state())
                continue
            if not self.playing:
                await self._wake.wait()
                continue
            event = self.events[local_index]
            if self.speed > 0:
                await asyncio.sleep(max(0.0, (event.timestamp_s - previous_ts) / self.speed))
            if generation != self._generation or local_index != self.index:
                continue
            previous_ts = event.timestamp_s
            local_index += 1
            self.index = local_index
            yield ("event", _slim_event(event))
            minute = event.minute
            if minute != last_minute:
                last_minute = minute
                if minute in prepared.momentum:
                    yield (
                        "momentum",
                        {
                            "minute": minute,
                            "home": prepared.momentum[minute],
                            "away": round(-prepared.momentum[minute], 2),
                        },
                    )
            for mid, mts in ordered:
                if mts <= event.timestamp_s and mid not in emitted:
                    emitted.add(mid)
                    detail = prepared.details_by_id.get(mid)
                    if detail is None:
                        continue
                    yield ("moment", detail)
                    hops = prepared.trace_by_moment.get(mid, [])
                    if hops:
                        yield ("trace", {"moment_id": mid, "hops": hops})
        yield ("done", self.state())


def _slim_event(event) -> dict:
    return {
        "id": event.event_id,
        "minute": event.minute,
        "timestamp_s": event.timestamp_s,
        "type": event.type.value,
        "team_id": event.team_id,
        "player_id": event.player_id,
        "x": event.x,
        "y": event.y,
        "outcome": event.outcome.value,
        "xg": event.xg,
    }
