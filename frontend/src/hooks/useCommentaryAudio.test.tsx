import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCommentaryAudio } from "./useCommentaryAudio";

class FakeAudio {
  static instances: FakeAudio[] = [];
  src = "";
  played = false;
  pauseCalled = false;
  onended: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor() {
    FakeAudio.instances.push(this);
  }
  async play(): Promise<void> {
    this.played = true;
  }
  pause(): void {
    this.pauseCalled = true;
  }
}

function audioResponse() {
  return {
    ok: true,
    headers: { get: () => "audio/mpeg" },
    blob: async () => new Blob(["fake-mp3"], { type: "audio/mpeg" }),
  };
}

function fallbackResponse() {
  return {
    ok: true,
    headers: { get: () => "application/json" },
    json: async () => ({ status: "fallback_client" }),
  };
}

function synth() {
  return (window as unknown as { __synth: { spoken: SpeechSynthesisUtterance[]; cancelled: number } })
    .__synth;
}

beforeEach(() => {
  localStorage.clear();
  FakeAudio.instances = [];
  synth().spoken = [];
  synth().cancelled = 0;
  vi.stubGlobal("fetch", vi.fn());
  vi.stubGlobal("Audio", FakeAudio);
});

describe("useCommentaryAudio", () => {
  it("stays silent and skips the network when muted", async () => {
    localStorage.setItem("matchiq:commentary-muted", "1");
    const mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);
    const { result } = renderHook(() => useCommentaryAudio());
    expect(result.current.isMuted).toBe(true);
    await act(async () => {
      await result.current.speak("Goal!", "en", "goal");
    });
    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isSpeaking).toBe(false);
  });

  it("plays Azure mp3 immediately when the backend synthesizes", async () => {
    const mockFetch = vi.fn().mockResolvedValue(audioResponse());
    vi.stubGlobal("fetch", mockFetch);
    const { result } = renderHook(() => useCommentaryAudio());
    await act(async () => {
      await result.current.speak("Goal!", "en", "goal");
    });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/speech/synthesize"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "Goal!", lang: "en", moment_type: "goal" }),
      }),
    );
    expect(FakeAudio.instances).toHaveLength(1);
    expect(FakeAudio.instances[0].played).toBe(true);
    expect(result.current.audioSource).toBe("azure");
  });

  it("falls back to the browser voice with matched locale and rate", async () => {
    const mockFetch = vi.fn().mockResolvedValue(fallbackResponse());
    vi.stubGlobal("fetch", mockFetch);
    const { result } = renderHook(() => useCommentaryAudio());
    await act(async () => {
      await result.current.speak("Гол!", "uk", "goal");
    });
    expect(synth().spoken).toHaveLength(1);
    expect(synth().spoken[0].lang).toBe("uk-UA");
    expect(synth().spoken[0].rate).toBe(1.1);
    expect(result.current.audioSource).toBe("browser");
  });

  it("mute toggle persists and cancels speech", async () => {
    const { result } = renderHook(() => useCommentaryAudio());
    act(() => {
      result.current.toggleMute();
    });
    expect(result.current.isMuted).toBe(true);
    expect(localStorage.getItem("matchiq:commentary-muted")).toBe("1");
    expect(synth().cancelled).toBeGreaterThan(0);
  });

  it("stop() resets playback state", async () => {
    const mockFetch = vi.fn().mockResolvedValue(audioResponse());
    vi.stubGlobal("fetch", mockFetch);
    const { result } = renderHook(() => useCommentaryAudio());
    await act(async () => {
      await result.current.speak("Goal!", "en", "goal");
    });
    act(() => {
      result.current.stop();
    });
    expect(result.current.isSpeaking).toBe(false);
    expect(result.current.audioSource).toBe("idle");
  });
});
