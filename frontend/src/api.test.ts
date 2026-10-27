import { beforeEach, describe, expect, it, vi } from "vitest";
import { controls, fetchMatch, streamUrl } from "./api";

const mockFetch = vi.fn();

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    headers: { get: () => "application/json" },
    json: async () => payload,
  };
}

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

describe("fetchMatch", () => {
  it("GETs the match payload from /api/match", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ meta: "m" }));
    const data = await fetchMatch();
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining("/api/match"));
    expect(data).toEqual({ meta: "m" });
  });

  it("rejects when the backend is down", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });
    await expect(fetchMatch()).rejects.toThrow();
  });
});

describe("replay controls", () => {
  it("play/pause hit their endpoints with POST and empty bodies", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ playing: true }));
    await controls.play();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/play"),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: undefined,
      },
    );
    await controls.pause();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/pause"),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: undefined,
      },
    );
  });

  it("speed posts the multiplier, seek posts the minute", async () => {
    mockFetch.mockResolvedValue(jsonResponse({}));
    await controls.speed(10);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/speed"),
      expect.objectContaining({ body: JSON.stringify({ speed: 10 }) }),
    );
    await controls.seek(57);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/seek"),
      expect.objectContaining({ body: JSON.stringify({ minute: 57 }) }),
    );
  });

  it("rejects on non-OK control responses", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 422 });
    await expect(controls.seek(-1)).rejects.toThrow();
  });
});

describe("streamUrl", () => {
  it("encodes mode, lang, club and player focus", () => {
    const url = streamUrl({ mode: "fan", lang: "en", club: "NGU", focus: "NGU_10" });
    expect(url).toContain("/api/replay/stream?");
    expect(url).toContain("mode=fan");
    expect(url).toContain("lang=en");
    expect(url).toContain("club=NGU");
    expect(url).toContain("player_focus=NGU_10");
  });

  it("omits empty club and focus", () => {
    const url = streamUrl({ mode: "analyst", lang: "en", club: null, focus: null });
    expect(url).not.toContain("club=");
    expect(url).not.toContain("player_focus=");
    expect(url).toContain("mode=analyst");
  });
});
