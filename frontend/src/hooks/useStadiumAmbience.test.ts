import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useStadiumAmbience } from "./useStadiumAmbience";

describe("useStadiumAmbience", () => {
  it("never touches audio while muted, even on roar", () => {
    const { result } = renderHook(() =>
      useStadiumAmbience({ muted: true, speaking: false }),
    );
    expect(() => result.current.roar(2)).not.toThrow();
    expect(window.AudioContext).toBeUndefined();
  });

  it("degrades gracefully without an AudioContext", () => {
    const { result, rerender } = renderHook(
      ({ muted, speaking }: { muted: boolean; speaking: boolean }) =>
        useStadiumAmbience({ muted, speaking }),
      { initialProps: { muted: false, speaking: false } },
    );
    expect(() => result.current.roar(1)).not.toThrow();
    rerender({ muted: false, speaking: true });
    expect(() => result.current.roar(0)).not.toThrow();
  });
});
