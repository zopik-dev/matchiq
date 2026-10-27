import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { makeEvent, makeMoment, makeTeam } from "./test-factories";
import type { MatchPayload } from "./types";

type Listener = (e: { data: string }) => void;

class FakeSource {
  static instances: FakeSource[] = [];
  listeners = new Map<string, Listener[]>();
  onerror: ((e: unknown) => void) | null = null;
  closed = false;
  url: string;
  constructor(url: string) {
    this.url = url;
    FakeSource.instances.push(this);
  }
  addEventListener(kind: string, fn: Listener): void {
    const list = this.listeners.get(kind) ?? [];
    list.push(fn);
    this.listeners.set(kind, list);
  }
  emit(kind: string, data: unknown): void {
    for (const fn of this.listeners.get(kind) ?? []) fn({ data: JSON.stringify(data) });
  }
  close(): void {
    this.closed = true;
  }
}

function matchPayload(): MatchPayload {
  const series = Array.from({ length: 91 }, (_, minute) => ({ minute, home: 0, away: 0 }));
  const poss = Array.from({ length: 91 }, (_, minute) => ({ minute, home: 50, away: 50 }));
  return {
    meta: {
      match_id: "m1",
      teams: [makeTeam("NGU", "Northgate United"), makeTeam("EVR", "Eastvale Rovers")],
      stadium: "Test Park",
      kickoff_time: "2026-09-12T15:00:00Z",
    },
    total_events: 10,
    totals: { xg_home: 1, xg_away: 0, poss_home: 55, poss_away: 45 },
    moments: [],
    segments: [],
    momentum_series: [],
    xg_series: series,
    poss_series: poss,
    state: { playing: true, speed: 60, index: 0, total: 10, minute: 0, score: { home: 0, away: 0 } },
  };
}

const mockFetch = vi.fn();

beforeEach(() => {
  localStorage.clear();
  FakeSource.instances = [];
  vi.stubGlobal("EventSource", FakeSource);
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({
    ok: true,
    headers: { get: () => "application/json" },
    json: async () => matchPayload(),
  });
  vi.stubGlobal("fetch", mockFetch);
});

describe("App live wiring", () => {
  it("streams state into the header score and minute", async () => {
    render(<App />);
    await screen.findByText("MatchIQ AI Storyline Feed");
    const source = FakeSource.instances[0];
    expect(source.url).toContain("/api/replay/stream?");
    act(() => {
      source.emit("state", {
        playing: true,
        speed: 60,
        index: 3,
        total: 10,
        minute: 23,
        score: { home: 1, away: 0 },
      });
    });
    expect(await screen.findByText("1 – 0")).toBeInTheDocument();
    expect(screen.getByText("23′")).toBeInTheDocument();
  });

  it("counts a streamed goal optimistically before backend state lands", async () => {
    render(<App />);
    await screen.findByText("MatchIQ AI Storyline Feed");
    const source = FakeSource.instances[0];
    act(() => {
      source.emit("state", {
        playing: true,
        speed: 60,
        index: 1,
        total: 10,
        minute: 5,
        score: { home: 0, away: 0 },
      });
      source.emit(
        "event",
        makeEvent({
          id: "e-goal",
          type: "goal",
          team_id: "NGU",
          player_id: "NGU_9",
          minute: 23,
          timestamp_s: 1410,
          xg: 0.4,
        }),
      );
    });
    expect(await screen.findByText("1 – 0")).toBeInTheDocument();
  });

  it("publishes streamed moments into the narrative feed", async () => {
    render(<App />);
    await screen.findByText("MatchIQ AI Storyline Feed");
    const source = FakeSource.instances[0];
    act(() => {
      source.emit(
        "moment",
        makeMoment({ moment_id: "m-goal", line: "A stunning header." }),
      );
    });
    // The same grounded line appears in the live narrative and the storyline
    // feed, so assert the moment reached the UI rather than a unique node.
    expect((await screen.findAllByText("A stunning header.")).length).toBeGreaterThan(0);
  });
});
