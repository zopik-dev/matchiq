import { useMemo, useState } from "react";
import type { MomentDetail, PitchEvent, Player, Team } from "../types";

const HOME_C = "#6ab7ff";
const AWAY_C = "#ffb84d";
const EASE = "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)";

const toX = (x: number) => (x / 100) * 105;
const toY = (y: number) => (y / 100) * 68;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function spread(n: number): number[] {
  if (n <= 1) return [34];
  const gap = Math.min(15, 52 / (n - 1));
  const start = 34 - (gap * (n - 1)) / 2;
  return Array.from({ length: n }, (_, i) => start + i * gap);
}

interface BaseDot {
  x: number;
  y: number;
  p: Player;
  line: "GK" | "DF" | "MF" | "FW";
  side: "home" | "away";
  phase: number;
}

function formation(team: Team, homeSide: boolean): BaseDot[] {
  const starters = team.roster.slice(0, 11);
  const by = (pos: string) => starters.filter((p) => p.position === pos);
  const at = (x: number) => (homeSide ? x : 105 - x);
  const groups: { x: number; list: Player[]; line: BaseDot["line"] }[] = [
    { x: 6, list: by("GK").slice(0, 1), line: "GK" },
    { x: 22, list: by("DF"), line: "DF" },
    { x: 38, list: by("MF"), line: "MF" },
    { x: 54, list: by("FW"), line: "FW" },
  ];
  let phase = homeSide ? 0 : 100;
  return groups.flatMap((g) => {
    const ys = spread(Math.max(1, g.list.length));
    return g.list.map((p, i) => ({ x: at(g.x), y: ys[i] ?? 34, p, line: g.line, side: homeSide ? ("home" as const) : ("away" as const), phase: (phase += 1.37) }));
  });
}

const PUSH: Record<BaseDot["line"], number> = { GK: 2, DF: 14, MF: 10, FW: 5 };
const DROP: Record<BaseDot["line"], number> = { GK: 1, DF: 6, MF: 4, FW: 2 };

function shiftDot(d: BaseDot, ballX: number, ballY: number, clock: number): { x: number; y: number } {
  // +prog in opponent half pushes lines up; deep ball in own half drops the block.
  const prog = d.side === "home" ? (ballX - 52.5) / 52.5 : (52.5 - ballX) / 52.5;
  const dir = d.side === "home" ? 1 : -1;
  const push = prog >= 0 ? prog * PUSH[d.line] : prog * DROP[d.line];
  const defending = d.side === "home" ? ballX < 52.5 : ballX > 52.5;
  const compact = defending ? 0.14 : 0.07;
  // Organic micro-drift so athletes look alive (±2 units ≈ ±2-3%).
  const dx = Math.sin(clock * 0.5 + d.phase) * 1.8;
  const dy = Math.cos(clock * 0.4 + d.phase * 1.7) * 1.4;
  return {
    x: clamp(d.x + dir * push + dx, 2, 103),
    y: clamp(d.y + (ballY - d.y) * compact + dy, 3, 65),
  };
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
  const [showLines, setShowLines] = useState(true);

  const base = useMemo(
    () => [...formation(home, true), ...formation(away, false)],
    [home, away],
  );
  const shown = events.slice(-25);
  const last = shown[shown.length - 1];
  const clock = last ? last.timestamp_s : 0;
  // Stream coordinates drive formation shift; the rendered ball snaps to tokens.
  const ball = last ? { x: toX(last.x), y: toY(last.y) } : { x: 52.5, y: 34 };

  const lastPass = [...shown].reverse().find((e) => e.type === "pass");
  const passFrom = lastPass && last && lastPass.id !== last.id ? lastPass : null;

  // Live token positions: base formation + team shift + drift + pass dynamics.
  const tokens = useMemo(() => {
    const pos = new Map<string, { x: number; y: number; d: BaseDot }>();
    for (const d of base) pos.set(d.p.id, { ...shiftDot(d, ball.x, ball.y, clock), d });

    // Passer leans toward the pass; receiver runs toward the intercept point.
    if (lastPass && lastPass.player_id) {
      const spot = pos.get(lastPass.player_id);
      if (spot) {
        const tx = toX(lastPass.x) - spot.x;
        const ty = toY(lastPass.y) - spot.y;
        const len = Math.hypot(tx, ty) || 1;
        spot.x = clamp(spot.x + (tx / len) * 2.2, 2, 103);
        spot.y = clamp(spot.y + (ty / len) * 2.2, 3, 65);
      }
      const recv = lastPass.target_player_id;
      if (recv && lastPass.outcome === "complete") {
        const spotR = pos.get(recv);
        if (spotR) {
          spotR.x = clamp(spotR.x + (toX(lastPass.x) - spotR.x) * 0.35, 2, 103);
          spotR.y = clamp(spotR.y + (toY(lastPass.y) - spotR.y) * 0.35, 3, 65);
        }
      }
    }
    return pos;
  }, [base, ball.x, ball.y, clock, lastPass]);

  const carrierId = last?.player_id ?? null;

  // Ball snaps to the carrier's token (stays with them until the next
  // pass/shot); shots render at the mouth, travelling from the shooter.
  const carrierSpot = carrierId ? tokens.get(carrierId) : undefined;
  const isShot = last?.type === "shot" || last?.type === "goal";
  const ballRender =
    isShot || !carrierSpot ? ball : { x: carrierSpot.x, y: carrierSpot.y };

  // Pass vector runs token-to-token so the glide matches the athletes.
  const passVec = useMemo(() => {
    if (!passFrom || !passFrom.player_id) return null;
    const from = tokens.get(passFrom.player_id);
    const recvId = passFrom.target_player_id;
    const to = recvId ? tokens.get(recvId) : undefined;
    if (!from || !to) return null;
    return { x1: from.x, y1: from.y, x2: to.x, y2: to.y };
  }, [tokens, passFrom]);

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
      const spot = tokens.get(id);
      return info && spot ? [{ ...spot, info }] : [];
    });
  }, [featured, tokens, lookup]);

  // Fresh shot/goal (within the last 4 streamed events) gets a trajectory cone.
  const shot = useMemo(() => {
    const tail = shown.slice(-4).reverse();
    const evt = tail.find((e) => e.type === "shot" || e.type === "goal");
    if (!evt || !evt.player_id) return null;
    const spot = tokens.get(evt.player_id);
    if (!spot) return null;
    const homeShooting = evt.team_id === home.id;
    const gx = homeShooting ? 104 : 1;
    return { evt, sx: spot.x, sy: spot.y, gx, color: homeShooting ? HOME_C : AWAY_C };
  }, [shown, tokens, home.id]);

  const shotXg = useMemo(() => {
    const evt = [...shown]
      .reverse()
      .find((e) => (e.type === "shot" || e.type === "goal") && typeof e.xg === "number");
    return evt?.xg ?? null;
  }, [shown]);

  // Team compactness blocks (width × depth) for the tactical-lines overlay.
  const blocks = useMemo(() => {
    const out: { side: "home" | "away"; x0: number; x1: number; y0: number; y1: number }[] = [];
    for (const side of ["home", "away"] as const) {
      const pts = [...tokens.values()].filter(
        (t) => t.d.side === side && t.d.line !== "GK",
      );
      if (pts.length === 0) continue;
      out.push({
        side,
        x0: Math.min(...pts.map((p) => p.x)) - 2,
        x1: Math.max(...pts.map((p) => p.x)) + 2,
        y0: Math.min(...pts.map((p) => p.y)) - 2,
        y1: Math.max(...pts.map((p) => p.y)) + 2,
      });
    }
    return out;
  }, [tokens]);

  return (
    <div className="relative">
      <button
        onClick={() => setShowLines((v) => !v)}
        className={`absolute right-2 top-2 z-10 rounded-full px-2.5 py-1 text-[11px] font-semibold transition ${
          showLines ? "bg-white text-ink" : "bg-black/40 text-white/60 hover:text-white"
        }`}
      >
        Tactical Lines
      </button>
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

        {showLines &&
          blocks.map((b) => (
            <rect
              key={b.side}
              x={b.x0}
              y={b.y0}
              width={Math.max(1, b.x1 - b.x0)}
              height={Math.max(1, b.y1 - b.y0)}
              fill="none"
              stroke={b.side === "home" ? HOME_C : AWAY_C}
              strokeOpacity="0.25"
              strokeWidth="0.3"
              strokeDasharray="1.6 1.2"
              rx="1.5"
              style={{ transition: EASE }}
            />
          ))}

        {[...tokens.values()].map(({ x, y, d }) => (
          <g
            key={d.p.id}
            transform={`translate(${x.toFixed(2)} ${y.toFixed(2)})`}
            opacity={d.side === "home" ? 0.9 : 0.8}
            style={{ transition: EASE }}
          >
            <circle
              r="1.6"
              fill={d.side === "home" ? HOME_C : AWAY_C}
              stroke="#0b0f19"
              strokeWidth="0.4"
            />
            <text y="0.9" textAnchor="middle" fontSize="2.2" fontWeight="700" fill="#0b0f19">
              {d.p.number}
            </text>
            {d.p.id === carrierId && (
              <circle r="2.5" fill="none" stroke="#fff" strokeWidth="0.4" opacity="0.9" className="pulse-ring" />
            )}
          </g>
        ))}

        {shown.map((e, i) => (
          <circle
            key={e.id}
            cx={toX(e.x)}
            cy={toY(e.y)}
            r="0.7"
            fill="#fff"
            opacity={0.15 + (0.5 * (i + 1)) / shown.length}
          />
        ))}

        {passVec ? (
          <path
            d={`M${passVec.x1} ${passVec.y1} L${passVec.x2} ${passVec.y2}`}
            stroke="#fff"
            strokeWidth="0.45"
            strokeDasharray="1.6 1.4"
            className="dash-anim"
            fill="none"
            markerEnd="url(#arr)"
          />
        ) : (
          passFrom &&
          last && (
            <path
              d={`M${toX(passFrom.x)} ${toY(passFrom.y)} L${toX(last.x)} ${toY(last.y)}`}
              stroke="#fff"
              strokeWidth="0.45"
              strokeDasharray="1.6 1.4"
              className="dash-anim"
              fill="none"
              markerEnd="url(#arr)"
            />
          )
        )}

        {shot && (
          <g>
            <polygon
              points={`${shot.sx},${shot.sy} ${shot.gx},27 ${shot.gx},41`}
              fill={shot.color}
              opacity="0.16"
            />
            <line
              x1={shot.sx}
              y1={shot.sy}
              x2={shot.gx}
              y2={clamp(toY(shot.evt.y), 28, 40)}
              stroke={shot.color}
              strokeWidth="0.5"
              strokeDasharray="1.4 1.2"
              className="dash-anim"
            />
            <circle
              cx={shot.sx}
              cy={shot.sy}
              r="2.6"
              fill="none"
              stroke="#fff"
              strokeWidth="0.5"
              opacity="0.9"
            />
            <circle
              cx={shot.gx}
              cy={clamp(toY(shot.evt.y), 29, 39)}
              r="2.2"
              fill="none"
              stroke={shot.color}
              strokeWidth="0.5"
              className="pulse-ring"
            />
          </g>
        )}

        {actors.map((a) => {
          const surname = a.info.name.split(" ").slice(-1)[0] ?? "";
          const pillW = surname.length * 1.3 + 2.4;
          return (
            <g key={a.d.p.id} transform={`translate(${a.x.toFixed(2)} ${a.y.toFixed(2)})`} style={{ transition: EASE }}>
              <circle r="2.6" fill={a.d.side === "home" ? HOME_C : AWAY_C} stroke="#fff" strokeWidth="0.4" />
              <text y="0.9" textAnchor="middle" fontSize="2.4" fontWeight="700" fill="#0b0f19">
                {a.info.number}
              </text>
              <rect
                x={-pillW / 2}
                y="-7.2"
                width={pillW}
                height="3.4"
                rx="1.7"
                fill="#0b0f19"
                fillOpacity="0.78"
              />
              <text y="-4.6" textAnchor="middle" fontSize="2.2" fontWeight="600" fill="#fff">
                {surname}
              </text>
            </g>
          );
        })}

        {last && (
          <g transform={`translate(${ballRender.x.toFixed(2)} ${ballRender.y.toFixed(2)})`} style={{ transition: EASE }}>
            <circle r="2" fill="#3ee6a0" className="pulse-ring" opacity="0.6" />
            <circle r="1.1" fill="#fff" />
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
    </div>
  );
}
