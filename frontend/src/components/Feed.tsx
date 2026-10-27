import { motion } from "framer-motion";
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

export default function Feed({
  items,
  onGoalClick,
}: {
  items: MomentDetail[];
  onGoalClick?: (momentId: string) => void;
}) {
  const ordered = useMemo(
    () => [...items].sort((a, b) => b.timestamp_s - a.timestamp_s),
    [items],
  );
  return (
    <div className="flex flex-col gap-2.5">
      {ordered.map((item) => {
        const Icon = ICONS[item.moment_type];
        const clickable = item.moment_type === "goal" && onGoalClick;
        return (
          <motion.article
            key={item.moment_id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            onClick={clickable ? () => onGoalClick(item.moment_id) : undefined}
            title={clickable ? `${item.moment_type} · ${item.minute}′` : undefined}
            className={`mi-tile p-3.5 ${
              clickable ? "mi-lift cursor-pointer hover:border-white/25" : ""
            }`}
          >
            <div className="mb-1.5 flex items-center gap-2">
              <Icon
                size={14}
                className="text-white"
                style={{ filter: "drop-shadow(0 0 3px hsla(210,100%,70%,0.7))" }}
              />
              <span className="mi-chip rounded-full px-2 py-0.5 font-mono text-[11px] tabular-nums text-white">
                {item.minute}&prime;
              </span>
              <div className="flex flex-wrap gap-1">
                {badges(item.evidence).map((b) => (
                  <span
                    key={b}
                    className="rounded-full border border-white/10 bg-black/40 px-2 py-0.5 font-mono text-[11px] tabular-nums text-white/70"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </div>
            <p className="text-sm font-medium leading-snug tracking-tight text-white">{item.line ?? item.story}</p>
          </motion.article>
        );
      })}
    </div>
  );
}
