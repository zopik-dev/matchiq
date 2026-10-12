import { useCallback, useEffect, useRef } from "react";

/**
 * Procedural stadium crowd ambience: zero-dependency Web Audio synthesis.
 *
 * - Ambient murmur: looped pinkish-noise buffer through a lowpass filter with
 *   a slow sinusoidal LFO for organic movement.
 * - Goal / chance roar: the same noise through a sweeping bandpass filter
 *   with a volume surge envelope.
 * - Ducking: crowd bus drops to 30% while commentary speaks.
 * - Mute follows the Live Audio toggle; the context only starts after a user
 *   gesture (autoplay policy) and never without consent.
 */
export function useStadiumAmbience({
  muted,
  speaking,
}: {
  muted: boolean;
  speaking: boolean;
}) {
  const ctxRef = useRef<AudioContext | null>(null);
  const masterRef = useRef<GainNode | null>(null);
  const crowdBusRef = useRef<GainNode | null>(null);
  const roarGainRef = useRef<GainNode | null>(null);
  const roarFilterRef = useRef<BiquadFilterNode | null>(null);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const ensure = useCallback((): boolean => {
    if (typeof window === "undefined") return false;
    try {
      if (!ctxRef.current) {
        const AC =
          window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext })
            .webkitAudioContext;
        if (!AC) return false;
        const ctx = new AC();
        const len = ctx.sampleRate * 2;
        const buf = ctx.createBuffer(1, len, ctx.sampleRate);
        const data = buf.getChannelData(0);
        let last = 0;
        for (let i = 0; i < len; i++) {
          const white = Math.random() * 2 - 1;
          last = (last + 0.02 * white) / 1.02;
          data[i] = last * 3.2;
        }
        const master = ctx.createGain();
        master.gain.value = mutedRef.current ? 0 : 0.9;
        master.connect(ctx.destination);
        const crowd = ctx.createGain();
        crowd.gain.value = 1;
        crowd.connect(master);
        const murmurSrc = ctx.createBufferSource();
        murmurSrc.buffer = buf;
        murmurSrc.loop = true;
        const murmurFilter = ctx.createBiquadFilter();
        murmurFilter.type = "lowpass";
        murmurFilter.frequency.value = 420;
        const murmurGain = ctx.createGain();
        murmurGain.gain.value = 0.05;
        murmurSrc.connect(murmurFilter);
        murmurFilter.connect(murmurGain);
        murmurGain.connect(crowd);
        const lfo = ctx.createOscillator();
        lfo.frequency.value = 0.13;
        const lfoGain = ctx.createGain();
        lfoGain.gain.value = 0.018;
        lfo.connect(lfoGain);
        lfoGain.connect(murmurGain.gain);
        const roarSrc = ctx.createBufferSource();
        roarSrc.buffer = buf;
        roarSrc.loop = true;
        roarSrc.playbackRate.value = 0.9;
        const roarFilter = ctx.createBiquadFilter();
        roarFilter.type = "bandpass";
        roarFilter.frequency.value = 700;
        roarFilter.Q.value = 0.9;
        const roarGain = ctx.createGain();
        roarGain.gain.value = 0;
        roarSrc.connect(roarFilter);
        roarFilter.connect(roarGain);
        roarGain.connect(crowd);
        murmurSrc.start();
        roarSrc.start();
        lfo.start();
        ctxRef.current = ctx;
        masterRef.current = master;
        crowdBusRef.current = crowd;
        roarGainRef.current = roarGain;
        roarFilterRef.current = roarFilter;
      }
      if (ctxRef.current.state === "suspended") void ctxRef.current.resume();
      return true;
    } catch {
      return false;
    }
  }, []);

  // Mute follows the Live Audio toggle.
  useEffect(() => {
    if (muted) {
      const ctx = ctxRef.current;
      const master = masterRef.current;
      if (ctx && master) master.gain.setTargetAtTime(0, ctx.currentTime, 0.1);
      return;
    }
    if (!ensure()) return;
    const ctx = ctxRef.current;
    const master = masterRef.current;
    if (ctx && master) master.gain.setTargetAtTime(0.9, ctx.currentTime, 0.2);
  }, [muted, ensure]);

  // Duck the crowd while commentary speaks so voice stays crisp.
  useEffect(() => {
    const ctx = ctxRef.current;
    const crowd = crowdBusRef.current;
    if (!ctx || !crowd) return;
    crowd.gain.setTargetAtTime(speaking ? 0.3 : 1, ctx.currentTime, 0.25);
  }, [speaking]);

  useEffect(
    () => () => {
      try {
        ctxRef.current?.close();
      } catch {
        /* already closed */
      }
      ctxRef.current = null;
    },
    [],
  );

  const roar = useCallback(
    (intensity: 0 | 1 | 2) => {
      if (intensity === 0 || mutedRef.current || !ensure()) return;
      const ctx = ctxRef.current;
      const gain = roarGainRef.current;
      const filter = roarFilterRef.current;
      if (!ctx || !gain || !filter) return;
      const t = ctx.currentTime;
      const peak = intensity === 2 ? 0.34 : 0.2;
      try {
        gain.gain.cancelScheduledValues(t);
        gain.gain.setValueAtTime(Math.max(0.001, gain.gain.value), t);
        gain.gain.linearRampToValueAtTime(peak, t + 0.18);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 3.4);
        filter.frequency.cancelScheduledValues(t);
        filter.frequency.setValueAtTime(500, t);
        filter.frequency.linearRampToValueAtTime(1400, t + 0.3);
        filter.frequency.exponentialRampToValueAtTime(650, t + 3.0);
      } catch {
        /* scheduler busy: skip this roar */
      }
    },
    [ensure],
  );

  return { roar };
}
