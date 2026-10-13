import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Scorebug from "./Scorebug";
import { makeTeam } from "../test-factories";
import type { ReplayState } from "../types";

const home = makeTeam("NGU", "Northgate United");
const away = makeTeam("EVR", "Eastvale Rovers");

function state(over: Partial<ReplayState> = {}): ReplayState {
  return { playing: true, speed: 60, index: 10, total: 100, minute: 89, score: { home: 2, away: 1 }, ...over };
}

describe("Scorebug", () => {
  it("renders badges, live score and minute", () => {
    render(<Scorebug home={home} away={away} replay={state()} liveLabel="LIVE" />);
    expect(screen.getByText("NGU")).toBeInTheDocument();
    expect(screen.getByText("EVR")).toBeInTheDocument();
    expect(screen.getByText("2–1")).toBeInTheDocument();
    expect(screen.getByText("89′")).toBeInTheDocument();
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("survives a null replay with zeros", () => {
    render(<Scorebug home={home} away={away} replay={null} liveLabel="LIVE" />);
    expect(screen.getByText("0–0")).toBeInTheDocument();
  });
});
