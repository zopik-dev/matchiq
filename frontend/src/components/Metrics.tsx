import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";
import type { MomentDetail } from "../types";
import Glass from "./Glass";

function AnimatedNumber({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const spring = useSpring(value, { stiffness: 90, damping: 20 });
  useEffect(() => {
    spring.set(value);
  }, [value, spring]);
  const text = useTransform(spring, (v) => v.toFixed(decimals));
  return <motion.span>{text}</motion.span>;
}

function Stat({
  label,
  children,
  sub,
  accent,
}: {
  label: string;
  children: React.ReactNode;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <motion.div
      layout
      className="rounded-2xl border border-white/[0.07] bg-black/20 p-3.5"
    >
      <div className="text-[11px] uppercase tracking-[0.14em] text-white/45">{label}</div>
      <div
        className={`mt-1 font-display text-2xl font-semibold tabular-nums tracking-tight ${
          accent ? "text-home" : "text-white"
        }`}
      >
        {children}
      </div>
      {sub && <div className="mt-0.5 text-xs text-white/50">{sub}</div>}
    </motion.div>
  );
}

export default function Metrics({
  title,
  shotLabel,
  matchLabel,
  ppdaLabel,
  dominanceLabel,
  minute,
  featured,
  xg,
  poss,
  ppda,
  homeName,
  awayName,
  lookup,
}: {
  title: string;
  shotLabel: string;
  matchLabel: string;
  ppdaLabel: string;
  dominanceLabel: string;
  minute: number;
  featured: MomentDetail | null;
  xg: { home: number; away: number };
  poss: { home: number; away: number };
  ppda: { home: number | null; away: number | null };
  homeName: string;
  awayName: string;
  lookup: (id: string | null) => { name: string; number: number } | null;
}) {
  const shotXg =
    featured && typeof featured.evidence["xg"] === "number"
      ? (featured.evidence["xg"] as number)
      : null;
  const shotWho = featured
    ? (lookup(
        (featured.evidence["scorer"] as string | undefined) ??
          (featured.evidence["player"] as string | undefined) ??
          null,
      )?.name ?? null)
    : null;
  const fmtPpda = (v: number | null) => (v === null ? "—" : v.toFixed(1));

  return (
    <Glass className="p-5">
      <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.16em] tabular-nums tracking-tight text-white/45">
        {title} · {minute.toFixed(0)}&prime;
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat label={shotLabel} sub={shotWho ?? undefined} accent>
          {shotXg !== null ? <AnimatedNumber value={shotXg} decimals={2} /> : "—"}
        </Stat>
        <Stat label={matchLabel} sub={homeName}>
          <span className="font-mono tabular-nums tracking-tight">
            <AnimatedNumber value={xg.home} decimals={1} />
            {" – "}
            <AnimatedNumber value={xg.away} decimals={1} />
          </span>
        </Stat>
        <Stat label={ppdaLabel} sub={`${homeName} · ${awayName}`}>
          <span className="font-mono tabular-nums tracking-tight">
            {fmtPpda(ppda.home)} · {fmtPpda(ppda.away)}
          </span>
        </Stat>
        <Stat label={dominanceLabel} sub={poss.home >= 50 ? homeName : awayName} accent>
          <span className="font-mono tabular-nums tracking-tight">
            <AnimatedNumber value={poss.home} decimals={0} />%
          </span>
        </Stat>
      </div>
      <div className="mt-4">
        <div className="h-1.5 overflow-hidden rounded-full bg-away/70">
          <motion.div
            className="h-full rounded-full bg-home"
            animate={{ width: `${poss.home}%` }}
            transition={{ type: "spring", stiffness: 60, damping: 20 }}
          />
        </div>
      </div>
    </Glass>
  );
}
