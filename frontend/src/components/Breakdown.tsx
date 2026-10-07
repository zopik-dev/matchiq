import type { MomentDetail, PitchEvent } from "../types";
import Glass from "./Glass";

function describe(e: PitchEvent, lookup: (id: string | null) => { name: string } | null): string {
  const who = lookup(e.player_id)?.name ?? e.team_id ?? "—";
  switch (e.type) {
    case "pass":
      return `${who} passes on.`;
    case "shot":
      return `${who} shoots${typeof e.xg === "number" ? ` (xG ${e.xg.toFixed(2)})` : ""}.`;
    case "goal":
      return `${who} scores.`;
    case "tackle":
      return `${who} wins the duel.`;
    case "interception":
      return `${who} intercepts.`;
    case "corner":
      return `Corner for ${who}.`;
    case "foul":
      return `Foul by ${who}.`;
    case "substitution":
      return `Substitution (${e.player_id}).`;
    case "pressure":
      return `${who} presses.`;
    default:
      return `${e.type} — ${who}.`;
  }
}

export default function Breakdown({
  title,
  featured,
  events,
  lookup,
}: {
  title: string;
  featured: MomentDetail | null;
  events: PitchEvent[];
  lookup: (id: string | null) => { name: string } | null;
}) {
  const steps = featured
    ? events.filter((e) => e.timestamp_s <= featured.timestamp_s).slice(-3)
    : [];
  if (steps.length === 0) return null;
  return (
    <Glass className="rounded-[28px] p-5">
      <div className="mb-4 text-[11px] uppercase tracking-[0.16em] text-white/45">{title}</div>
      <ol className="relative space-y-4 border-l border-white/10 pl-5">
        {steps.map((s, i) => (
          <li key={s.id} className="relative">
            <span
              className={`absolute -left-[26px] top-1 size-2.5 rounded-full ring-4 ring-[#161c2c] ${
                i === steps.length - 1 ? "bg-mint" : "bg-white/40"
              }`}
            />
            <div className="text-xs font-semibold tabular-nums text-mint">
              {Math.floor(s.timestamp_s / 60)}:{`${Math.floor(s.timestamp_s % 60)}`.padStart(2, "0")}
            </div>
            <div className="text-sm leading-snug text-white/75">{describe(s, lookup)}</div>
          </li>
        ))}
      </ol>
    </Glass>
  );
}
