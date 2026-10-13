import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PressureTimeline from "./PressureTimeline";

const series = [
  { minute: 0, home: 0 },
  { minute: 45, home: 10 },
  { minute: 90, home: -5 },
];

describe("PressureTimeline", () => {
  it("pins goals and seeks through them on click", () => {
    const onSeek = vi.fn();
    const onGoalPin = vi.fn();
    render(
      <PressureTimeline
        series={series}
        moments={[
          {
            id: "g1",
            type: "goal",
            minute: 57,
            timestamp_s: 3420,
            team_id: "EVR",
            title: "Equaliser",
            evidence: {},
          },
        ]}
        minute={60}
        homeId="NGU"
        homeName="Northgate United"
        awayName="Eastvale Rovers"
        onSeek={onSeek}
        onGoalPin={onGoalPin}
        title="Match pressure"
        hint="Hover me"
        resolvePlayer={() => null}
      />,
    );
    expect(screen.getByText("Match pressure")).toBeInTheDocument();
    fireEvent.click(screen.getByText("57′"));
    expect(onGoalPin).toHaveBeenCalledWith(57);
    expect(onSeek).not.toHaveBeenCalled();
  });
});
