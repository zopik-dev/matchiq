import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import GenerateButton from "./GenerateButton";

describe("GenerateButton", () => {
  it("renders idle letters and flips to busy class while working", () => {
    const { rerender } = render(
      <GenerateButton idle="Ask" busy="Thinking" isBusy={false} small />,
    );
    expect(screen.getByText("A", { exact: true })).toBeInTheDocument();
    expect(document.querySelector(".mi-btn.is-busy")).toBeNull();
    rerender(<GenerateButton idle="Ask" busy="Thinking" isBusy small />);
    expect(document.querySelector(".mi-btn.is-busy")).not.toBeNull();
  });

  it("disables the submit button when there is nothing to ask", () => {
    render(<GenerateButton idle="Ask" busy="Thinking" isBusy={false} disabled title="send" />);
    expect(screen.getByTitle("send")).toBeDisabled();
  });
});
