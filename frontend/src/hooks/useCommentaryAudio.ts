import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "../types";

export type AudioSource = "azure" | "browser" | "idle";
export type SpeakLang = "en";

const MUTE_KEY = "matchiq:commentary-muted";

function pickVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const exact = voices.find((v) => v.lang.toLowerCase().startsWith("en-gb"));
  if (exact) return exact;
  const loose = voices.find((v) => v.lang.toLowerCase().startsWith("en"));
  return loose ?? null;
}

function speakWithBrowser(text: string, onEnd: () => void): void {
  const synth = window.speechSynthesis;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-GB";
  utterance.rate = 1.1;
  utterance.pitch = 1.05;
  const applyVoice = () => {
    const voices = synth.getVoices();
    if (voices.length > 0) {
      const best = pickVoice(voices);
      if (best) utterance.voice = best;
    }
  };
  applyVoice();
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  // Voices may load async (Chrome); retry once they arrive.
  if (synth.getVoices().length === 0) {
    const handler = () => {
      applyVoice();
      synth.removeEventListener?.("voiceschanged", handler);
    };
    synth.addEventListener?.("voiceschanged", handler);
  }
  synth.speak(utterance);
}

/**
 * Hybrid live commentary audio: Azure Speech MP3 when the backend has
 * credentials, seamless fallback to the browser Web Speech API otherwise.
 */
export function useCommentaryAudio() {
  const [isMuted, setIsMuted] = useState<boolean>(() => {
    try {
      return localStorage.getItem(MUTE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioSource, setAudioSource] = useState<AudioSource>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mutedRef = useRef(isMuted);
  mutedRef.current = isMuted;

  const teardown = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      const url = audioRef.current.src;
      audioRef.current.src = "";
      audioRef.current = null;
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    }
    try {
      window.speechSynthesis?.cancel();
    } catch {
      /* speech API unavailable */
    }
    setIsSpeaking(false);
    setAudioSource("idle");
  }, []);

  const stop = useCallback(() => {
    teardown();
  }, [teardown]);

  const toggleMute = useCallback(() => {
    setIsMuted((m) => {
      const next = !m;
      try {
        localStorage.setItem(MUTE_KEY, next ? "1" : "0");
      } catch {
        /* private mode */
      }
      if (next) {
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }
        try {
          window.speechSynthesis?.cancel();
        } catch {
          /* ignore */
        }
        setIsSpeaking(false);
        setAudioSource("idle");
      }
      return next;
    });
  }, []);

  const speak = useCallback(
    async (text: string, lang: SpeakLang, moment_type?: string): Promise<void> => {
      const line = text.trim().slice(0, 1000);
      if (!line || mutedRef.current) return;
      teardown();
      setIsSpeaking(true);
      const finish = () => {
        setIsSpeaking(false);
        setAudioSource("idle");
      };
      try {
        const res = await fetch(`${API_BASE}/api/speech/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: line, lang, moment_type: moment_type ?? null }),
        });
        const contentType = res.headers.get("content-type") ?? "";
        if (res.ok && contentType.includes("audio/")) {
          const blob = await res.blob();
          if (mutedRef.current) {
            finish();
            return;
          }
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audioRef.current = audio;
          setAudioSource("azure");
          audio.onended = () => {
            URL.revokeObjectURL(url);
            if (audioRef.current === audio) audioRef.current = null;
            finish();
          };
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            if (audioRef.current === audio) audioRef.current = null;
            finish();
          };
          await audio.play();
          return;
        }
        // Backend fallback hint (or non-audio response) → browser voice.
      } catch {
        /* network/backend down → browser voice below */
      }
      if (mutedRef.current) {
        finish();
        return;
      }
      try {
        setAudioSource("browser");
        speakWithBrowser(line, finish);
      } catch {
        finish();
      }
    },
    [teardown],
  );

  useEffect(() => teardown, [teardown]);

  return { isMuted, isSpeaking, audioSource, speak, stop, toggleMute };
}
