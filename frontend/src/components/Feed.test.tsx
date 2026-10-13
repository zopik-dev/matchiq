import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Feed from "./Feed";
import { makeMoment } from "../test-factories";

describe("Feed", () => {
  it("shows newest moments first", () => {
    render(
      <Feed
        items={[
          makeMoment({ moment_id: "m1", minute: 23, timestamp_s: 1400, line: "First goal" }),
          makeMoment({ moment_id: "m2", minute: 57, timestamp_s: 3450, line: "Equaliser" }),
        ]}
      />,
    );
    const cards = screen.getAllByText(/First goal|Equaliser/);
    expect(cards[0].textContent).toContain("Equaliser");
    expect(cards[1].textContent).toContain("First goal");
  });

  it("routes goal clicks to the x-ray opener, ignores other types", () => {
    const onGoalClick = vi.fn();
    render(
      <Feed
        items={[
          makeMoment({ moment_id: "g1", moment_type: "goal", line: "Goal!" }),
          makeMoment({
            moment_id: "c1",
            moment_type: "big_chance",
            line: "Chance!",
          }),
        ]}
        onGoalClick={onGoalClick}
      />,
    );
    fireEvent.click(screen.getByText("Goal!"));
    expect(onGoalClick).toHaveBeenCalledWith("g1");
    fireEvent.click(screen.getByText("Chance!"));
    expect(onGoalClick).toHaveBeenCalledTimes(1);
  });
});
