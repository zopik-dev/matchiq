import { useMemo, useState } from "react";
import type { MomentInfo, MomentumPoint } from "../types";

const HOME_C = "#2563EB";
const AWAY_C = "#DC2626";

function smoothPath(pts: readonly (readonly [number, number])[]): string {
  if (pts.length === 0) return "";
  if (pts.length < 3) {
    return pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  }
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

export default function PressureTimeline({
  series,
  moments,
  minute,
  homeId,
  homeName,
  awayName,
  onSeek,
  onGoalPin,
  title,
  hint,
  resolvePlayer,
}: {
  series: MomentumPoint[];
  moments: MomentInfo[];
  minute: number;
  homeId: string;
  homeName: string;
  awayName: string;
  onSeek: (minute: number) => void;
  onGoalPin?: (minute: number) => void;
  title: string;
  hint: string;
  resolvePlayer: (id: string | null) => { name: string } | null;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 900;
  const H = 120;
  const mid = H / 2;
  const pts = useMemo(
    () =>
      series.map(
        (p) => [(p.minute / 90) * W, mid - (Math.max(-100, Math.min(100, p.home)) / 100) * 44] as const,
      ),
    [series],
  );
  const line = useMemo(() => smoothPath(pts), [pts]);
  const area = `${line} L${W} ${mid} L0 ${mid} Z`;
  const goals = useMemo(() => moments.filter((m) => m.type === "goal"), [moments]);

  const hoverValue = hover !== null ? (series[hover]?.home ?? 0) : 0;
  const hoverGoal =
    hover !== null ? goals.find((g) => Math.abs(g.minute - hover) <= 1) ?? null : null;
  const hoverSurname = (() => {
    const raw = hoverGoal?.evidence["scorer"];
    return resolvePlayer(typeof raw === "string" ? raw : null)?.name.split(" ").slice(-1)[0] ?? "";
  })();

  return (
    <div className="relative">
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="font-display text-[13px] font-semibold tracking-wide text-white">{title}</span>
        <span className="flex items-center gap-4 text-white/55">
          <span className="flex items-center gap-1.5">
            <i className="size-2 rounded-full bg-home" />
            {homeName}
          </span>
          <span className="flex items-center gap-1.5">
            <i className="size-2 rounded-full bg-away" />
            {awayName}
          </span>
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full cursor-crosshair"
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHover(Math.round(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * 90));
        }}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="up" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={HOME_C} stopOpacity="0.28" />
            <stop offset="1" stopColor={HOME_C} stopOpacity="0" />
          </linearGradient>
          <linearGradient id="dn" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0" stopColor={AWAY_C} stopOpacity="0.26" />
            <stop offset="1" stopColor={AWAY_C} stopOpacity="0" />
          </linearGradient>
          <clipPath id="top">
            <rect width={W} height={mid} />
          </clipPath>
          <clipPath id="bot">
            <rect y={mid} width={W} height={mid} />
          </clipPath>
        </defs>
        {[0, 15, 30, 45, 60, 75, 90].map((m) => (
          <g key={m}>
            <line x1={(m / 90) * W} x2={(m / 90) * W} y1="0" y2={H} stroke="#fff" strokeOpacity="0.05" />
            <text
              x={Math.min(W - 10, Math.max(8, (m / 90) * W))}
              y={H - 2}
              fontSize="10"
              fill="#fff"
              fillOpacity="0.4"
              textAnchor="middle"
            >
              {m}&prime;
            </text>
          </g>
        ))}
        <line x1="0" x2={W} y1={mid} y2={mid} stroke="#fff" strokeOpacity="0.3" strokeWidth="1" />
        <path d={area} fill="url(#up)" clipPath="url(#top)" />
        <path d={area} fill="url(#dn)" clipPath="url(#bot)" />
        <path d={line} fill="none" stroke="#fff" strokeOpacity="0.85" strokeWidth="1.5" strokeLinejoin="round" />
        {goals.map((g) => {
          const x = (g.minute / 90) * W;
          const c = g.team_id === homeId ? HOME_C : AWAY_C;
          return (
            <g
              key={g.id}
              className="cursor-pointer"
              onClick={() => (onGoalPin ?? onSeek)(g.minute)}
            >
              <title>{g.title}</title>
              <line x1={x} x2={x} y1="16" y2={H - 14} stroke={c} strokeOpacity="0.45" strokeDasharray="2 3" />
              <circle cx={x} cy="12" r="8" fill="#090D16" stroke={c} strokeWidth="1.25" />
              <circle cx={x} cy="12" r="2.6" fill="#fff" />
            </g>
          );
        })}
        <line
          x1={(Math.min(90, minute) / 90) * W}
          x2={(Math.min(90, minute) / 90) * W}
          y1="0"
          y2={H}
          stroke="#fff"
          strokeOpacity="0.5"
          strokeDasharray="3 2"
        />
        {hover !== null && (
          <g>
            <line x1={(hover / 90) * W} x2={(hover / 90) * W} y1="0" y2={H} stroke="#fff" strokeOpacity="0.5" />
            <circle
              cx={(hover / 90) * W}
              cy={mid - (Math.max(-100, Math.min(100, hoverValue)) / 100) * 44}
              r="4"
              fill="#fff"
            />
          </g>
        )}
      </svg>
      <div className="mt-2 flex items-center justify-between text-xs text-white/55">
        <span>
          {hoverGoal
            ? `⚽ ${hoverGoal.minute}′ ${hoverSurname} — ${hoverGoal.title}`
            : hover !== null
              ? `${hover}′ · ${hoverValue >= 0 ? homeName : awayName} ${Math.abs(hoverValue).toFixed(0)} momentum`
              : hint}
        </span>
        <span className="flex gap-3">
          {goals.map((g) => {
            const raw = g.evidence["scorer"];
            const surname =
              resolvePlayer(typeof raw === "string" ? raw : null)?.name.split(" ").slice(-1)[0] ?? "";
            return (
            <button
              key={g.id}
              onClick={() => (onGoalPin ?? onSeek)(g.minute)}
              className="tabular-nums hover:text-white"
            >
                <b className="text-white">{g.minute}&prime;</b> {surname}
              </button>
            );
          })}
        </span>
      </div>
    </div>
  );
}
