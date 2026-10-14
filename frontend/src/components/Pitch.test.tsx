import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Pitch, { gridDistanceM } from "./Pitch";
import { makeTeam } from "../test-factories";

const home = makeTeam("NGU", "Northgate United");
const away = makeTeam("EVR", "Eastvale Rovers");
const lookup = (id: string | null) => (id ? { name: `Name ${id}`, number: 7 } : null);
const noop = () => undefined;

function renderPitch() {
  return render(
    <Pitch
      home={home}
      away={away}
      events={[]}
      featured={null}
      lookup={lookup}
      attackLabel="NORTHGATE"
      focusedId={null}
      onPlayerClick={noop}
      onClearFocus={noop}
      xray={null}
      lang="en"
    />,
  );
}

describe("gridDistanceM", () => {
  it("scales the 0-100 grid to real metres (105 x 68)", () => {
    expect(gridDistanceM(0, 0, 100, 0)).toBeCloseTo(105, 6);
    expect(gridDistanceM(0, 0, 0, 100)).toBeCloseTo(68, 6);
    expect(gridDistanceM(10, 10, 10, 10)).toBe(0);
  });
});

describe("Pitch", () => {
  it("renders 22 clickable player tokens", () => {
    renderPitch();
    expect(document.querySelectorAll("svg [data-token]").length).toBe(22);
  });

  it("forwards token clicks to player focus", () => {
    const onPlayerClick = vi.fn();
    render(
      <Pitch
        home={home}
        away={away}
        events={[]}
        featured={null}
        lookup={lookup}
        attackLabel="NORTHGATE"
        focusedId={null}
        onPlayerClick={onPlayerClick}
        onClearFocus={noop}
        xray={null}
        lang="en"
      />,
    );
    const first = document.querySelector("svg [data-token]") as SVGGElement;
    fireEvent.click(first);
    expect(onPlayerClick).toHaveBeenCalledWith(first.getAttribute("data-token"));
  });

  it("switches view layers and arms the pundit caliper", async () => {
    renderPitch();
    fireEvent.click(screen.getByRole("button", { name: /Pitch Control/ }));
    expect(screen.getByRole("button", { name: /Pitch Control/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByTitle("Measure / Pundit Tool"));
    const tokens = document.querySelectorAll("svg [data-token]");
    fireEvent.click(tokens[0]);
    fireEvent.click(tokens[1]);
    await screen.findByText(/\d+\.\d+m ·/);
  });
});
