import type { MomentumPoint } from "../types";

const HOME = "#38bdf8";
const AWAY = "#f43f5e";

export default function MomentumChart({
  series,
  minute,
}: {
  series: MomentumPoint[];
  minute: number;
}) {
  const W = 360;
  const H = 110;
  const mid = H / 2;
  const n = Math.max(1, series.length);
  const bw = W / n;
  const scale = (mid - 6) / 100;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-28 w-full">
      <line x1={0} y1={mid} x2={W} y2={mid} stroke="#334155" strokeWidth={1} />
      {series.map((p) => {
        const h = Math.abs(p.home) * scale;
        const x = p.minute * bw;
        return (
          <rect
            key={p.minute}
            x={x}
            y={p.home >= 0 ? mid - h : mid}
            width={Math.max(0.6, bw - 0.4)}
            height={Math.max(0.5, h)}
            fill={p.home >= 0 ? HOME : AWAY}
            opacity={p.minute <= minute ? 1 : 0.25}
          />
        );
      })}
      <line
        x1={minute * bw}
        y1={0}
        x2={minute * bw}
        y2={H}
        stroke="#f8fafc"
        strokeWidth={1}
        strokeDasharray="2 2"
      />
    </svg>
  );
}
