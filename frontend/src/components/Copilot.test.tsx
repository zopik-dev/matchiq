import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Copilot from "./Copilot";
import type { Profile } from "../types";

const profile: Profile = { mode: "fan", lang: "en", club: null, focus: null };

const baseProps = {
  profile,
  homeName: "Northgate United",
  awayName: "Eastvale Rovers",
  title: "Tactical Copilot",
  placeholder: "Ask about tactics...",
  thinking: "Thinking…",
  errorText: "Unreachable",
};

const answer = {
  answer: "Because the press broke.",
  evidence: { xg: 0.41 },
  relevant_events: [],
  suggested_followups: [],
};

function postOk(payload: unknown) {
  return {
    ok: true,
    headers: { get: () => "application/json" },
    json: async () => payload,
  };
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("Copilot", () => {
  it("posts the query with mode and lang, then renders the answer", async () => {
    const mockFetch = vi.fn().mockResolvedValue(postOk(answer));
    vi.stubGlobal("fetch", mockFetch);
    render(<Copilot {...baseProps} />);
    fireEvent.change(screen.getByPlaceholderText("Ask about tactics..."), {
      target: { value: "Why the goal?" },
    });
    fireEvent.click(screen.getByTitle("send"));
    await screen.findByText("Because the press broke.");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/copilot/ask"),
      expect.objectContaining({ method: "POST" }),
    );
    const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
    expect(body).toMatchObject({ query: "Why the goal?", mode: "fan", lang: "en" });
  });

  it("auto-asks an injected pundit question exactly once", async () => {
    const mockFetch = vi.fn().mockResolvedValue(postOk(answer));
    vi.stubGlobal("fetch", mockFetch);
    const { rerender } = render(<Copilot {...baseProps} externalAsk={null} />);
    rerender(<Copilot {...baseProps} externalAsk={{ q: "Explain the gap", n: 7 }} />);
    await screen.findByText("Because the press broke.");
    rerender(<Copilot {...baseProps} externalAsk={{ q: "Explain the gap", n: 7 }} />);
    await new Promise((r) => setTimeout(r, 50));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("reads the answer aloud through onSpeak", async () => {
    const mockFetch = vi.fn().mockResolvedValue(postOk(answer));
    vi.stubGlobal("fetch", mockFetch);
    const onSpeak = vi.fn();
    render(<Copilot {...baseProps} onSpeak={onSpeak} />);
    fireEvent.change(screen.getByPlaceholderText("Ask about tactics..."), {
      target: { value: "Hi" },
    });
    fireEvent.click(screen.getByTitle("send"));
    const btn = await screen.findByLabelText("Read this answer aloud");
    fireEvent.click(btn);
    expect(onSpeak).toHaveBeenCalledWith("Because the press broke.");
  });
});
