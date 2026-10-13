import "@testing-library/jest-dom/vitest";

// jsdom lacks these browser APIs; provide minimal deterministic stubs.
if (typeof window !== "undefined") {
  if (!window.matchMedia) {
    window.matchMedia = (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    });
  }
  if (!window.IntersectionObserver) {
    window.IntersectionObserver = class {
      observe(): void {
        /* noop */
      }
      unobserve(): void {
        /* noop */
      }
      disconnect(): void {
        /* noop */
      }
    } as unknown as typeof IntersectionObserver;
  }
  if (!window.speechSynthesis) {
    const synth = {
      voices: [] as SpeechSynthesisVoice[],
      spoken: [] as SpeechSynthesisUtterance[],
      cancelled: 0,
      getVoices: () => synth.voices,
      speak: (u: SpeechSynthesisUtterance) => {
        synth.spoken.push(u);
      },
      cancel: () => {
        synth.cancelled += 1;
      },
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    };
    Object.defineProperty(window, "speechSynthesis", {
      value: synth,
      configurable: true,
    });
    (window as unknown as { __synth: unknown }).__synth = synth;
  }
  if (typeof (window as unknown as Record<string, unknown>).SpeechSynthesisUtterance === "undefined") {
    class FakeUtterance {
      text: string;
      lang = "";
      rate = 1;
      pitch = 1;
      voice: SpeechSynthesisVoice | null = null;
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      value: FakeUtterance,
      configurable: true,
    });
  }
  if (!URL.createObjectURL) {
    URL.createObjectURL = () => "blob:mock-audio";
  }
  if (!URL.revokeObjectURL) {
    URL.revokeObjectURL = () => undefined;
  }
}
