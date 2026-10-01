import { Goal, Flame, Repeat, TrendingUp, Zap } from "lucide-react";
import { useMemo } from "react";
import type { MomentDetail, MomentInfo } from "../types";

const ICONS: Record<MomentInfo["type"], typeof Goal> = {
  goal: Goal,
  big_chance: Zap,
  pressure_spike: Flame,
  momentum_swing: TrendingUp,
  tactical_shift: Repeat,
};

function badges(evidence: Record<string, unknown>): string[] {
  const out: string[] = [];
  const get = (k: string) => evidence[k];
  if (typeof get("xg") === "number") out.push(`xG ${(get("xg") as number).toFixed(2)}`);
  if (typeof get("pressure_events") === "number")
    out.push(`${get("pressure_events")} duels/5min`);
  if (typeof get("score") === "string") out.push(`${get("score")}`);
  if (typeof get("momentum_home_after") === "number")
    out.push(`momentum ${(get("momentum_home_after") as number).toFixed(0)}`);
  return out;
}

export default function Feed({ items }: { items: MomentDetail[] }) {
  const ordered = useMemo(
    () => [...items].sort((a, b) => b.timestamp_s - a.timestamp_s),
    [items],
  );
  return (
    <div className="flex flex-col gap-2.5">
      {ordered.map((item) => {
        const Icon = ICONS[item.moment_type];
        return (
          <article
            key={item.moment_id}
            className="rounded-2xl border border-white/[0.07] bg-black/20 p-3.5"
          >
            <div className="mb-1.5 flex items-center gap-2">
              <Icon size={14} className="text-mint" />
              <span className="rounded-full bg-white/10 px-2 py-0.5 font-mono text-[11px] tabular-nums text-white">
                {item.minute}&prime;
              </span>
              <div className="flex flex-wrap gap-1">
                {badges(item.evidence).map((b) => (
                  <span
                    key={b}
                    className="rounded-full border border-mint/30 bg-mint/10 px-2 py-0.5 font-mono text-[11px] text-mint"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </div>
            <p className="text-sm leading-snug text-white/80">{item.line ?? item.story}</p>
          </article>
        );
      })}
    </div>
  );
}
