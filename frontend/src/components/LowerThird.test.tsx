import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LowerThird from "./LowerThird";
import { makeMoment } from "../test-factories";

const lookup = (id: string | null) =>
  id ? { name: `Surname ${id}`, number: 9 } : null;

describe("LowerThird", () => {
  it("badges a goal with xG and score pills from engine evidence", () => {
    render(
      <LowerThird
        detail={makeMoment({
          moment_id: "g89",
          moment_type: "goal",
          minute: 89,
          evidence: { xg: 0.46, score: "2-1" },
          line: "Decisive finish.",
        })}
        teamName="Northgate United"
        lookup={lookup}
      />,
    );
    expect(screen.getByText(/GOAL ANALYSIS · 89/)).toBeInTheDocument();
    expect(screen.getByText("Decisive finish.")).toBeInTheDocument();
    expect(screen.getByText("xG 0.46")).toBeInTheDocument();
    expect(screen.getByText("Score 2-1")).toBeInTheDocument();
  });

  it("renders a substitution pill for tactical shifts", () => {
    render(
      <LowerThird
        detail={makeMoment({
          moment_id: "s1",
          moment_type: "tactical_shift",
          minute: 60,
          evidence: { player_off: "NGU_8", player_on: "NGU_14" },
          line: "Fresh legs.",
        })}
        teamName={null}
        lookup={lookup}
      />,
    );
    expect(screen.getByText(/TACTICAL SHIFT/)).toBeInTheDocument();
    expect(screen.getByText("Sub NGU_8 → NGU_14")).toBeInTheDocument();
  });
});
