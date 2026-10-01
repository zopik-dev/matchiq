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
    <div className="flex flex-col gap-2 overflow-y-auto pr-1">
      {ordered.map((item) => {
        const Icon = ICONS[item.moment_type];
        return (
          <article
            key={item.moment_id}
            className="rounded-lg border border-slate-700 bg-slate-800/60 p-3"
          >
            <div className="mb-1 flex items-center gap-2">
              <Icon size={15} className="text-sky-300" />
              <span className="rounded bg-slate-700 px-1.5 py-0.5 font-mono text-[11px] text-slate-200">
                {item.minute}&prime;
              </span>
              <div className="flex flex-wrap gap-1">
                {badges(item.evidence).map((b) => (
                  <span
                    key={b}
                    className="rounded bg-emerald-900 px-1.5 py-0.5 font-mono text-[11px] text-emerald-200"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </div>
            <p className="text-sm leading-snug text-slate-100">
              {item.line ?? item.story}
            </p>
          </article>
        );
      })}
    </div>
  );
}
