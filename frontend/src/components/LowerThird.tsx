import { motion } from "framer-motion";
import type { MomentDetail } from "../types";

const BADGE: Record<MomentDetail["moment_type"], string> = {
  goal: "⚽ GOAL ANALYSIS",
  big_chance: "BIG CHANCE",
  pressure_spike: "PRESSURE SPIKE",
  momentum_swing: "MOMENTUM SWING",
  tactical_shift: "🔄 TACTICAL SHIFT",
};

/** Engine-computed metric pills for the broadcast lower-third. */
function metricPills(
  detail: MomentDetail,
  lookup: (id: string | null) => { name: string } | null,
): string[] {
  const out: string[] = [];
  const ev = detail.evidence;
  if (typeof ev["xg"] === "number") out.push(`xG ${(ev["xg"] as number).toFixed(2)}`);
  if (typeof ev["score"] === "string") out.push(`Score ${ev["score"] as string}`);
  if (typeof ev["pressure_events"] === "number")
    out.push(`${ev["pressure_events"] as number} duels/5min`);
  const off =
    typeof ev["player_off"] === "string"
      ? (lookup(ev["player_off"])?.name.split(" ").slice(-1)[0] ?? null)
      : null;
  const on =
    typeof ev["player_on"] === "string"
      ? (lookup(ev["player_on"])?.name.split(" ").slice(-1)[0] ?? null)
      : null;
  if (off && on) out.push(`Sub ${off} → ${on}`);
  return out;
}

/** Automated TV broadcast lower-third: slides up, fades out on a timer. */
export default function LowerThird({
  detail,
  teamName,
  lookup,
}: {
  detail: MomentDetail;
  teamName: string | null;
  lookup: (id: string | null) => { name: string } | null;
}) {
  const pills = metricPills(detail, lookup);
  return (
    <motion.div
      key={detail.moment_id}
      initial={{ y: 90, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 40, opacity: 0 }}
      transition={{ type: "spring", stiffness: 210, damping: 26 }}
      className="pointer-events-none w-[min(92vw,760px)] overflow-hidden rounded-2xl border border-white/20 bg-black/75"
      style={{
        boxShadow:
          "inset 0 1px 1px rgba(255,255,255,0.22), 0 20px 60px rgba(0,0,0,0.65)",
        backdropFilter: "blur(14px)",
      }}
    >
      <div className="h-1 w-full bg-gradient-to-r from-[#3B82F6] via-white to-[#DC2626]" />
      <div className="px-6 py-4">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="rounded bg-white px-2 py-0.5 font-mono text-[11px] font-bold tracking-widest text-black">
            {BADGE[detail.moment_type]} · {detail.minute}&prime;
          </span>
          {teamName && (
            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">
              {teamName}
            </span>
          )}
          <span className="ml-auto flex items-center gap-1 rounded bg-[#DC2626] px-1.5 py-0.5 text-[10px] font-bold tracking-widest text-white">
            <i className="size-1.5 animate-pulse rounded-full bg-white" aria-hidden />
            LIVE
          </span>
        </div>
        <h2 className="text-2xl font-bold leading-tight tracking-tight text-white">
          {detail.line ?? detail.story}
        </h2>
        {pills.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {pills.map((p) => (
              <span
                key={p}
                className="rounded-full border border-white/20 bg-white/10 px-2.5 py-1 font-mono text-[11px] tabular-nums text-white"
              >
                {p}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
