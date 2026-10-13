import type { ReplayState, Team } from "../types";

/** Sleek broadcast scorebug for TV mode: [NGU] 2–1 [EVR], 89' LIVE. */
export default function Scorebug({
  home,
  away,
  replay,
  liveLabel,
}: {
  home: Team;
  away: Team;
  replay: ReplayState | null;
  liveLabel: string;
}) {
  const minute = replay?.minute ?? 0;
  const score = replay?.score ?? { home: 0, away: 0 };
  const tag = (id: string) =>
    id === "NGU" ? "NGU" : id === "EVR" ? "EVR" : id.slice(0, 3).toUpperCase();
  return (
    <div
      className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border border-white/20 bg-black/70 px-3 py-1.5"
      style={{
        boxShadow:
          "inset 0 1px 1px rgba(255,255,255,0.2), 0 8px 24px rgba(0,0,0,0.6)",
        backdropFilter: "blur(12px)",
      }}
    >
      <span className="rounded bg-[#2563EB] px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-widest text-white">
        {tag(home.id)}
      </span>
      <span className="whitespace-nowrap font-mono text-xl font-bold tabular-nums text-white">
        {score.home}–{score.away}
      </span>
      <span className="rounded bg-[#DC2626] px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-widest text-white">
        {tag(away.id)}
      </span>
      <span className="whitespace-nowrap font-mono text-sm font-semibold tabular-nums text-white">
        {minute.toFixed(0)}&prime;
      </span>
      <span className="flex items-center gap-1 rounded bg-[#DC2626] px-1.5 py-0.5 text-[10px] font-bold tracking-widest text-white">
        <i
          className="size-1.5 animate-pulse rounded-full bg-white"
          aria-hidden
        />
        {liveLabel}
      </span>
    </div>
  );
}
