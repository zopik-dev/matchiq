import type { MomentDetail, Totals } from "../types";
import Glass from "./Glass";

function Stat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-black/20 p-3.5">
      <div className="text-[11px] uppercase tracking-[0.14em] text-white/45">{label}</div>
      <div
        className={`mt-1 font-display text-2xl font-semibold tabular-nums ${
          accent ? "text-mint" : "text-white"
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-white/50">{sub}</div>}
    </div>
  );
}

export default function Metrics({
  title,
  possessionLabel,
  shotLabel,
  matchLabel,
  momentumLabel,
  chancesLabel,
  featured,
  totals,
  momentum,
  chances,
  homeName,
  awayName,
  lookup,
}: {
  title: string;
  possessionLabel: string;
  shotLabel: string;
  matchLabel: string;
  momentumLabel: string;
  chancesLabel: string;
  featured: MomentDetail | null;
  totals: Totals;
  momentum: { home: number } | null;
  chances: number;
  homeName: string;
  awayName: string;
  lookup: (id: string | null) => { name: string; number: number } | null;
}) {
  const shotXg = featured && typeof featured.evidence["xg"] === "number"
    ? (featured.evidence["xg"] as number)
    : null;
  const shotWho = featured
    ? lookup(
        (featured.evidence["scorer"] as string | undefined) ??
          (featured.evidence["player"] as string | undefined) ??
          null,
      )?.name ?? null
    : null;

  return (
    <Glass className="rounded-[28px] p-5">
      <div className="mb-3 text-[11px] uppercase tracking-[0.16em] text-white/45">
        {title} · {featured ? `${featured.minute}′` : "—"}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat
          label={shotLabel}
          value={shotXg !== null ? shotXg.toFixed(2) : "—"}
          sub={shotWho ?? undefined}
          accent
        />
        <Stat
          label={matchLabel}
          value={`${totals.xg_home.toFixed(1)} – ${totals.xg_away.toFixed(1)}`}
          sub={homeName}
        />
        <Stat
          label={momentumLabel}
          value={momentum !== null ? `${momentum.home >= 0 ? "+" : ""}${momentum.home.toFixed(0)}` : "—"}
          sub={momentum !== null ? (momentum.home >= 0 ? homeName : awayName) : undefined}
        />
        <Stat label={chancesLabel} value={`${chances}`} sub={featured ? `${featured.minute}′` : undefined} />
      </div>
      <div className="mt-4">
        <div className="mb-1.5 flex justify-between text-xs text-white/55">
          <span>{possessionLabel}</span>
          <span className="tabular-nums">
            {totals.poss_home.toFixed(0)}% · {totals.poss_away.toFixed(0)}%
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-amber/70">
          <div className="h-full rounded-full bg-sky" style={{ width: `${totals.poss_home}%` }} />
        </div>
      </div>
    </Glass>
  );
}
