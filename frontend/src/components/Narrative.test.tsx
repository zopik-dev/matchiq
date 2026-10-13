import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Narrative from "./Narrative";
import { makeMoment } from "../test-factories";

describe("Narrative", () => {
  it("shows the featured headline with a listen button", () => {
    const onListen = vi.fn();
    render(
      <Narrative
        featured={makeMoment({ moment_id: "n1", line: "Stunning strike." })}
        mode="fan"
        empty="Nothing yet."
        onListen={onListen}
        speaking={false}
      />,
    );
    expect(screen.getByText("Stunning strike.")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Listen to this moment"));
    expect(onListen).toHaveBeenCalledTimes(1);
  });

  it("falls back to story text and shows the empty state", async () => {
    const { rerender } = render(
      <Narrative
        featured={makeMoment({ moment_id: "n1", line: null, story: "Story fallback." })}
        mode="fan"
        empty="Nothing yet."
      />,
    );
    expect(screen.getByText("Story fallback.")).toBeInTheDocument();
    rerender(<Narrative featured={null} mode="fan" empty="Nothing yet." />);
    // AnimatePresence exits the old card first; the empty state lands after.
    expect(await screen.findByText("Nothing yet.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Listen to this moment")).toBeNull();
  });
});
