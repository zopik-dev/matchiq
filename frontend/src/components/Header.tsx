import { Pause, Play, RotateCcw, Volleyball, Zap } from "lucide-react";
import { controls } from "../api";
import type { Profile, ReplayState, Team } from "../types";
import Glass from "./Glass";

const SPEEDS = [1, 10, 60];
const MODES: Profile["mode"][] = ["analyst", "fan", "beginner"];

function ClubTag({ id, name, side }: { id: string; name: string; side: "home" | "away" }) {
  const badge = id === "NGU" ? "NGU" : id === "EVR" ? "EVR" : id.slice(0, 3).toUpperCase();
  return (
    <span className="flex items-center gap-2">
      <span
        className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-widest text-white ${
          side === "home" ? "bg-[#2563EB]" : "bg-[#DC2626]"
        }`}
      >
        {badge}
      </span>
      <span className="text-sm font-semibold tracking-tight text-white sm:text-base">{name}</span>
    </span>
  );
}

export default function Header({
  home,
  away,
  replay,
  profile,
  onProfile,
  onSeek,
  onReplay,
  connected,
  t,
  audioOn,
  audioSpeaking,
  onToggleAudio,
}: {
  home: Team;
  away: Team;
  replay: ReplayState | null;
  profile: Profile;
  onProfile: (patch: Partial<Profile>) => void;
  onSeek: (minute: number) => void;
  onReplay: (state: ReplayState) => void;
  connected: boolean;
  audioOn: boolean;
  audioSpeaking: boolean;
  onToggleAudio: () => void;
  t: {
    play: string;
    pause: string;
    restart: string;
    live: string;
    paused: string;
    connecting: string;
  };
}) {
  const minute = replay?.minute ?? 0;
  const score = replay?.score ?? { home: 0, away: 0 };
  return (
    <header className="sticky top-0 z-20 flex justify-center px-4 pt-5">
      <Glass className="flex w-full max-w-6xl flex-col items-center gap-3 px-4 py-3 xl:flex-row xl:justify-between xl:py-2.5 xl:pl-6">
        <div className="flex flex-wrap items-center justify-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full bg-white/[0.07] px-2 py-0.5 text-[10px] font-bold tracking-widest text-white">
            <i className="size-1.5 rounded-full bg-[#DC2626]" />
            {replay?.playing ? t.live : t.paused}
          </span>
          <div className="flex items-center gap-3">
            <ClubTag id={home.id} name={home.name} side="home" />
            <span className="rounded-full bg-white/[0.07] px-3.5 py-1 font-mono text-lg font-semibold tabular-nums text-white sm:text-xl">
              {score.home} – {score.away}
            </span>
            <ClubTag id={away.id} name={away.name} side="away" />
            <span className="font-mono text-sm font-semibold tabular-nums text-white">
              {minute.toFixed(0)}&prime;
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              title={replay?.playing ? t.pause : t.play}
              onClick={() =>
                void (replay?.playing ? controls.pause() : controls.play()).then(onReplay)
              }
              className="rounded-full bg-white p-1.5 text-black transition hover:bg-white/85"
            >
              {replay?.playing ? <Pause size={14} /> : <Play size={14} />}
            </button>
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => void controls.speed(s).then(onReplay)}
                className={`rounded-full px-2.5 py-1 font-mono text-[11px] tabular-nums ${
                  replay?.speed === s
                    ? "bg-white/[0.14] font-bold text-white"
                    : "text-white/55 hover:text-white"
                }`}
              >
                {s}x
              </button>
            ))}
            <button
              title={t.restart}
              onClick={() => onSeek(0)}
              className="rounded-full p-1.5 text-white/55 transition hover:text-white"
            >
              <RotateCcw size={14} />
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <div role="tablist" className="flex gap-1 rounded-full bg-white/[0.05] p-1">
            {MODES.map((m) => (
              <button
                key={m}
                role="tab"
                aria-selected={profile.mode === m}
                onClick={() => onProfile({ mode: m })}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize transition ${
                  profile.mode === m
                    ? "bg-white/[0.14] text-white"
                    : "text-white/55 hover:text-white"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
          <div className="flex gap-1 rounded-full bg-white/[0.05] p-1">
            {(["en", "uk"] as const).map((l) => (
              <button
                key={l}
                onClick={() => onProfile({ lang: l })}
                className={`rounded-full px-3 py-1.5 font-mono text-xs font-bold uppercase tabular-nums transition ${
                  profile.lang === l
                    ? "bg-white/[0.14] text-white"
                    : "text-white/55 hover:text-white"
                }`}
              >
                {l === "en" ? "EN" : "UA"}
              </button>
            ))}
          </div>
          {!connected && (
            <span className="flex items-center gap-1 text-xs text-white/50">
              <Volleyball size={13} /> {t.connecting}
            </span>
          )}
          <button
            onClick={onToggleAudio}
            aria-pressed={audioOn}
            title="Toggle live broadcast audio"
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              audioOn ? "bg-white/[0.14] text-white" : "bg-white/[0.05] text-white/55 hover:text-white"
            }`}
          >
            🎙️ Live Audio: {audioOn ? "ON" : "OFF"}
            {audioSpeaking && (
              <span className="flex items-end gap-[2px]" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <i
                    key={i}
                    className="w-[3px] animate-pulse rounded-full bg-current"
                    style={{ height: `${8 + (i % 3) * 4}px`, animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </span>
            )}
          </button>
        </div>
      </Glass>
    </header>
  );
}

export function BrandMark() {
  return (
    <span className="flex items-center gap-1.5 text-sm font-semibold tracking-tight text-white">
      <Zap size={15} className="text-white/70" /> MatchIQ
    </span>
  );
}
