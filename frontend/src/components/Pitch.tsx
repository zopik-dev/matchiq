import type { PitchEvent } from "../types";

const HOME = "#38bdf8";
const AWAY = "#f43f5e";

export default function Pitch({
  events,
  homeId,
}: {
  events: PitchEvent[];
  homeId: string;
}) {
  const W = 105;
  const H = 68;
  const shown = events.slice(-25);
  const last = shown[shown.length - 1];
  const passFrom = [...shown].reverse().find((e) => e.type === "pass");

  const color = (team: string | null) =>
    team === homeId ? HOME : team ? AWAY : "#94a3b8";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-64 w-full">
      <rect x={0} y={0} width={W} height={H} rx={2} fill="#0f2e23" />
      <g stroke="#1d5c46" strokeWidth={0.6} fill="none">
        <rect x={1} y={1} width={W - 2} height={H - 2} />
        <line x1={W / 2} y1={1} x2={W / 2} y2={H - 1} />
        <circle cx={W / 2} cy={H / 2} r={9.15} />
        <rect x={1} y={H / 2 - 20.16} width={16.5} height={40.32} />
        <rect x={W - 17.5} y={H / 2 - 20.16} width={16.5} height={40.32} />
      </g>
      {passFrom && last && passFrom.id !== last.id && (
        <line
          x1={(passFrom.x / 100) * W}
          y1={(passFrom.y / 100) * H}
          x2={(last.x / 100) * W}
          y2={(last.y / 100) * H}
          stroke="#e2e8f0"
          strokeWidth={0.7}
          opacity={0.8}
          markerEnd="url(#arrow)"
        />
      )}
      <defs>
        <marker
          id="arrow"
          markerWidth={4}
          markerHeight={4}
          refX={3}
          refY={2}
          orient="auto"
        >
          <path d="M0,0 L4,2 L0,4" fill="none" stroke="#e2e8f0" strokeWidth={0.8} />
        </marker>
      </defs>
      {shown.map((e, i) => (
        <circle
          key={e.id}
          cx={(e.x / 100) * W}
          cy={(e.y / 100) * H}
          r={e.id === last?.id ? 1.8 : 1.1}
          fill={color(e.team_id)}
          opacity={0.25 + (0.75 * (i + 1)) / shown.length}
        />
      ))}
      {last && (
        <circle
          cx={(last.x / 100) * W}
          cy={(last.y / 100) * H}
          r={2.6}
          fill="none"
          stroke="#f8fafc"
          strokeWidth={0.5}
          opacity={0.9}
        />
      )}
    </svg>
  );
}
