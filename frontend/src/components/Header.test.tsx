import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Header from "./Header";
import { makeTeam } from "../test-factories";
import type { Profile, ReplayState } from "../types";

const home = makeTeam("NGU", "Northgate United");
const away = makeTeam("EVR", "Eastvale Rovers");
const profile: Profile = { mode: "fan", lang: "en", club: null, focus: null };
const t = {
  play: "Play",
  pause: "Pause",
  restart: "Restart",
  live: "LIVE",
  paused: "PAUSED",
  fulltime: "FULL TIME",
  connecting: "Connecting…",
  expTv: "TV Broadcast View",
  expConsole: "Interactive Console",
  stackTitle: "Microsoft Technology Stack",
  stackCompute: "Compute",
  stackComputeDesc: "desc",
  stackModels: "Models",
  stackModelsDesc: "desc",
  stackAudio: "Audio",
  stackAudioDesc: "desc",
  stackStore: "Store",
  stackStoreDesc: "desc",
  stackLatency: "Latency",
  stackProviderCloud: "Cloud",
  stackProviderMock: "Mock",
  stackClose: "Close",
};

function replay(over: Partial<ReplayState> = {}): ReplayState {
  return {
    playing: false,
    speed: 60,
    index: 5,
    total: 100,
    minute: 10,
    score: { home: 1, away: 0 },
    ...over,
  };
}

const mockFetch = vi.fn();

function ok(payload: unknown) {
  return { ok: true, headers: { get: () => "application/json" }, json: async () => payload };
}

function renderHeader(over: Record<string, unknown> = {}) {
  const props = {
    home,
    away,
    replay: replay(),
    profile,
    onProfile: vi.fn(),
    onSeek: vi.fn(),
    onReplay: vi.fn(),
    connected: true,
    audioOn: true,
    audioSpeaking: false,
    audioSource: "idle" as const,
    onToggleAudio: vi.fn(),
    experience: "console" as const,
    onExperience: vi.fn(),
    t,
    ...over,
  };
  render(<Header {...props} />);
  return props;
}

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

describe("Header", () => {
  it("renders the live score and minute", () => {
    renderHeader();
    expect(screen.getByText("1 – 0")).toBeInTheDocument();
    expect(screen.getByText("10′")).toBeInTheDocument();
    expect(screen.getByText("Northgate United")).toBeInTheDocument();
  });

  it("play posts to the backend and forwards the new state", async () => {
    const next = replay({ playing: true });
    mockFetch.mockResolvedValue(ok(next));
    const props = renderHeader();
    fireEvent.click(screen.getByTitle("Play"));
    await waitFor(() => expect(props.onReplay).toHaveBeenCalledWith(next));
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/play"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("restarts from kickoff when the match is over instead of playing", () => {
    const props = renderHeader({ replay: replay({ playing: false, index: 100, total: 100 }) });
    expect(screen.getByText("FULL TIME")).toBeInTheDocument();
    // Two "Restart" buttons exist when ended (play morphs into restart);
    // the dedicated rotate-ccw button is the second one.
    fireEvent.click(screen.getAllByTitle("Restart")[1]);
    expect(props.onSeek).toHaveBeenCalledWith(0);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("speed pills post the multiplier", () => {
    renderHeader();
    fireEvent.click(screen.getByText("10x"));
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/replay/speed"),
      expect.objectContaining({ body: JSON.stringify({ speed: 10 }) }),
    );
  });

  it("switches experience through the pill", () => {
    const props = renderHeader();
    fireEvent.click(screen.getByText(/TV Broadcast View/));
    expect(props.onExperience).toHaveBeenCalledWith("tv");
  });

  it("shows the azure voice source while speaking", () => {
    renderHeader({ audioSpeaking: true, audioSource: "browser" as const });
    expect(screen.getByText("· Browser")).toBeInTheDocument();
  });

  it("opens the Azure stack inspector with live provider status", async () => {
    mockFetch.mockResolvedValue(
      ok({
        llm: { provider: "mock", deployment: null },
        speech: { provider: "browser", region: "westeurope" },
        store: { provider: "memory" },
      }),
    );
    renderHeader();
    fireEvent.click(screen.getByTitle("Microsoft Technology Stack"));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/integrations"),
    );
    expect(await screen.findByText("Mock")).toBeInTheDocument();
    expect(screen.getByText("browser")).toBeInTheDocument();
    expect(screen.getByText("memory")).toBeInTheDocument();
  });
});
