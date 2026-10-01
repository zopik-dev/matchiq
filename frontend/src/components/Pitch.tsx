import { useMemo } from "react";
import type { MomentDetail, PitchEvent, Player, Team } from "../types";

const HOME_C = "#6ab7ff";
const AWAY_C = "#ffb84d";

function spread(n: number): number[] {
  if (n <= 1) return [34];
  const gap = Math.min(15, 52 / (n - 1));
  const start = 34 - (gap * (n - 1)) / 2;
  return Array.from({ length: n }, (_, i) => start + i * gap);
}

function formation(team: Team, homeSide: boolean): { x: number; y: number; p: Player }[] {
  const starters = team.roster.slice(0, 11);
  const by = (pos: string) => starters.filter((p) => p.position === pos);
  const dir = homeSide ? 1 : -1;
  const at = (x: number) => (homeSide ? x : 105 - x);
  const groups: { x: number; list: Player[] }[] = [
    { x: 6, list: by("GK").slice(0, 1) },
    { x: 22, list: by("DF") },
    { x: 38, list: by("MF") },
    { x: dir === 1 ? 54 : 53, list: by("FW") },
  ];
  return groups.flatMap((g) => {
    const ys = spread(Math.max(1, g.list.length));
    return g.list.map((p, i) => ({ x: at(g.x), y: ys[i] ?? 34, p }));
  });
}

export default function Pitch({
  home,
  away,
  events,
  featured,
  lookup,
  attackLabel,
}: {
  home: Team;
  away: Team;
  events: PitchEvent[];
  featured: MomentDetail | null;
  lookup: (id: string | null) => { name: string; number: number } | null;
  attackLabel: string;
}) {
  const dots = useMemo(
    () => [
      ...formation(home, true).map((d) => ({ ...d, side: "home" as const })),
      ...formation(away, false).map((d) => ({ ...d, side: "away" as const })),
    ],
    [home, away],
  );
  const shown = events.slice(-25);
  const last = shown[shown.length - 1];
  const passFrom = [...shown].reverse().find((e) => e.type === "pass" && last && e.id !== last.id);

  const actors = useMemo(() => {
    if (!featured) return [];
    const ids = [
      featured.evidence["scorer"],
      featured.evidence["player"],
      featured.evidence["player_off"],
    ].filter((v): v is string => typeof v === "string");
    const seen = new Set<string>();
    return ids.flatMap((id) => {
      if (seen.has(id)) return [];
      seen.add(id);
      const info = lookup(id);
      const dot = dots.find((d) => d.p.id === id);
      return info && dot ? [{ ...dot, info }] : [];
    });
  }, [featured, dots, lookup]);

  const shotXg = useMemo(() => {
    const shot = [...shown]
      .reverse()
      .find((e) => (e.type === "shot" || e.type === "goal") && typeof e.xg === "number");
    return shot?.xg ?? null;
  }, [shown]);

  return (
    <svg viewBox="0 0 105 68" className="block w-full rounded-2xl" role="img" aria-label="Live pitch">
      <defs>
        <linearGradient id="turf" x1="0" x2="1">
          <stop offset="0" stopColor="#0a3b2b" />
          <stop offset="0.5" stopColor="#0d4a35" />
          <stop offset="1" stopColor="#0a3b2b" />
        </linearGradient>
        <radialGradient id="flood" cx="0.5" cy="0.4" r="0.7">
          <stop offset="0" stopColor="#7dffc8" stopOpacity="0.22" />
          <stop offset="1" stopColor="#000" stopOpacity="0.45" />
        </radialGradient>
        <marker id="arr" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0 0 L4 2 L0 4z" fill="#6ab7ff" />
        </marker>
      </defs>
      <rect width="105" height="68" fill="url(#turf)" />
      {Array.from({ length: 10 }).map((_, i) => (
        <rect key={i} x={i * 10.5} width="5.25" height="68" fill="#fff" opacity="0.025" />
      ))}
      <rect width="105" height="68" fill="url(#flood)" />
      <g fill="none" stroke="#fff" strokeOpacity="0.85" strokeWidth="0.3">
        <rect x="2" y="2" width="101" height="64" />
        <line x1="52.5" y1="2" x2="52.5" y2="66" />
        <circle cx="52.5" cy="34" r="8" />
        <rect x="2" y="14" width="16" height="40" />
        <rect x="2" y="24" width="5.5" height="20" />
        <rect x="87" y="14" width="16" height="40" />
        <rect x="97.5" y="24" width="5.5" height="20" />
        <path d="M18 27.5 A8 8 0 0 1 18 40.5" />
        <path d="M87 27.5 A8 8 0 0 0 87 40.5" />
      </g>
      <circle cx="52.5" cy="34" r="0.5" fill="#fff" />
      <rect x="0.4" y="30" width="1.6" height="8" fill="none" stroke="#fff" strokeWidth="0.3" />
      <rect x="103" y="30" width="1.6" height="8" fill="none" stroke="#fff" strokeWidth="0.3" />

      {dots.map((d) => (
        <g key={d.p.id} opacity={d.side === "home" ? 0.85 : 0.75}>
          <circle
            cx={d.x}
            cy={d.y}
            r="1.6"
            fill={d.side === "home" ? HOME_C : AWAY_C}
            stroke="#0b0f19"
            strokeWidth="0.4"
          />
          <text
            x={d.x}
            y={d.y + 0.9}
            textAnchor="middle"
            fontSize="2.2"
            fontWeight="700"
            fill="#0b0f19"
          >
            {d.p.number}
          </text>
        </g>
      ))}

      {shown.map((e, i) => (
        <circle
          key={e.id}
          cx={(e.x / 100) * 105}
          cy={(e.y / 100) * 68}
          r="0.7"
          fill="#fff"
          opacity={0.15 + (0.5 * (i + 1)) / shown.length}
        />
      ))}

      {passFrom && last && (
        <path
          d={`M${(passFrom.x / 100) * 105} ${(passFrom.y / 100) * 68} L${(last.x / 100) * 105} ${(last.y / 100) * 68}`}
          stroke="#fff"
          strokeWidth="0.45"
          strokeDasharray="1.6 1.4"
          className="dash-anim"
          fill="none"
          markerEnd="url(#arr)"
        />
      )}

      {actors.map((a) => (
        <g key={a.p.id}>
          <circle cx={a.x} cy={a.y} r="2.6" fill={a.side === "home" ? HOME_C : AWAY_C} stroke="#fff" strokeWidth="0.4" />
          <text x={a.x} y={a.y + 0.9} textAnchor="middle" fontSize="2.4" fontWeight="700" fill="#0b0f19">
            {a.info.number}
          </text>
          <text x={a.x} y={a.y - 4} textAnchor="middle" fontSize="2.2" fontWeight="600" fill="#fff">
            {a.info.name.split(" ").slice(-1)}
          </text>
        </g>
      ))}

      {last && (
        <g>
          <circle
            cx={(last.x / 100) * 105}
            cy={(last.y / 100) * 68}
            r="2"
            fill="#3ee6a0"
            className="pulse-ring"
            opacity="0.6"
          />
          <circle cx={(last.x / 100) * 105} cy={(last.y / 100) * 68} r="1.1" fill="#fff" />
        </g>
      )}

      {shotXg !== null && (
        <g>
          <rect x="80" y="55" width="22" height="8" rx="2" fill="#0b0f19" fillOpacity="0.7" stroke="#fff" strokeOpacity="0.15" strokeWidth="0.2" />
          <text x="82" y="58.6" fontSize="2.1" fill="#9aa6c0">SHOT xG</text>
          <text x="82" y="61.8" fontSize="3" fontWeight="700" fill="#3ee6a0">{shotXg.toFixed(2)}</text>
        </g>
      )}
      <text x="6" y="64" fontSize="2" fill="#fff" fillOpacity="0.5">{attackLabel} ATTACK →</text>
    </svg>
  );
}
