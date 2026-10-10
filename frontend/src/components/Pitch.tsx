import gsap from "gsap";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import type { MomentDetail, PitchEvent, Player, Team } from "../types";

gsap.registerPlugin(MotionPathPlugin);

const HOME_C = "#3B82F6";
const AWAY_C = "#DC2626";

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
  const prog = d.side === "home" ? (ballX - 52.5) / 52.5 : (52.5 - ballX) / 52.5;
  const dir = d.side === "home" ? 1 : -1;
  const push = prog >= 0 ? prog * PUSH[d.line] : prog * DROP[d.line];
  const defending = d.side === "home" ? ballX < 52.5 : ballX > 52.5;
  const compact = defending ? 0.14 : 0.07;
  const dx = Math.sin(clock * 0.5 + d.phase) * 1.8;
  const dy = Math.cos(clock * 0.4 + d.phase * 1.7) * 1.4;
  return {
    x: clamp(d.x + dir * push + dx, 2, 103),
    y: clamp(d.y + (ballY - d.y) * compact + dy, 3, 65),
  };
}

export interface XrayOverlay {
  points: { x: number; y: number; label: string }[];
  index: number;
  xg: number | null;
  speed: number | null;
}

export default function Pitch({
  home,
  away,
  events,
  featured,
  lookup,
  attackLabel,
  focusedId,
  onPlayerClick,
  onClearFocus,
  xray,
}: {
  home: Team;
  away: Team;
  events: PitchEvent[];
  featured: MomentDetail | null;
  lookup: (id: string | null) => { name: string; number: number } | null;
  attackLabel: string;
  focusedId: string | null;
  onPlayerClick: (id: string) => void;
  onClearFocus: () => void;
  xray: XrayOverlay | null;
}) {
  const [showLines, setShowLines] = useState(true);

  const base = useMemo(
    () => [...formation(home, true), ...formation(away, false)],
    [home, away],
  );
  const shown = events.slice(-25);
  const last = shown[shown.length - 1];
  const clock = last ? last.timestamp_s : 0;
  const ball = last ? { x: toX(last.x), y: toY(last.y) } : { x: 52.5, y: 34 };

  const lastPass = [...shown].reverse().find((e) => e.type === "pass");
  const passFrom = lastPass && last && lastPass.id !== last.id ? lastPass : null;

  const tokens = useMemo(() => {
    const pos = new Map<string, { x: number; y: number; d: BaseDot }>();
    for (const d of base) pos.set(d.p.id, { ...shiftDot(d, ball.x, ball.y, clock), d });

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
  const carrierSpot = carrierId ? tokens.get(carrierId) : undefined;
  const isShot = last?.type === "shot" || last?.type === "goal";
  const ballTarget =
    isShot || !carrierSpot ? ball : { x: carrierSpot.x, y: carrierSpot.y };

  const passVec = useMemo(() => {
    if (!passFrom || !passFrom.player_id) return null;
    const from = tokens.get(passFrom.player_id);
    const recvId = passFrom.target_player_id;
    const to = recvId ? tokens.get(recvId) : undefined;
    if (!from || !to) return null;
    return { x1: from.x, y1: from.y, x2: to.x, y2: to.y };
  }, [tokens, passFrom]);

  // GSAP-driven token interpolation (positions set once via attribute, then tweened).
  const tokenRefs = useRef(new Map<string, SVGGElement | null>());
  useLayoutEffect(() => {
    tokenRefs.current.forEach((el, id) => {
      const p = tokens.get(id);
      if (!el || !p) return;
      gsap.to(el, { x: p.x, y: p.y, duration: 0.5, ease: "power2.out", overwrite: "auto" });
    });
  }, [tokens]);

  // GSAP ball kinetics: Bézier arcs for passes, velocity snap for shots.
  const ballRef = useRef<SVGGElement | null>(null);
  const ballPos = useRef({ x: 52.5, y: 34 });
  useLayoutEffect(() => {
    const el = ballRef.current;
    if (!el) return;
    const from = { ...ballPos.current };
    const to = { x: ballTarget.x, y: ballTarget.y };
    const dist = Math.hypot(to.x - from.x, to.y - from.y);
    if (dist < 0.05) return;
    if (isShot) {
      gsap.to(el, { x: to.x, y: to.y, duration: 0.45, ease: "power3.in", overwrite: "auto" });
    } else {
      const lift = Math.min(6, Math.max(1.2, dist * 0.14));
      const mx = (from.x + to.x) / 2;
      const my = (from.y + to.y) / 2 - lift;
      gsap.to(el, {
        motionPath: { path: [{ x: from.x, y: from.y }, { x: mx, y: my }, { x: to.x, y: to.y }], curviness: 1.4 },
        duration: Math.min(0.6, Math.max(0.25, dist / 60)),
        ease: "power2.out",
        overwrite: "auto",
      });
    }
    ballPos.current = to;
  }, [ballTarget, isShot]);

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

  const shotXg = useMemo(() => {
    const evt = [...shown]
      .reverse()
      .find((e) => (e.type === "shot" || e.type === "goal") && typeof e.xg === "number");
    return evt?.xg ?? null;
  }, [shown]);

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

  // X-Ray overlay points in display coords, sliced to the active step.
  const xrayPts = useMemo(() => {
    if (!xray) return null;
    const pts = xray.points.map((p) => ({ x: toX(p.x), y: toY(p.y), label: p.label }));
    const shownPts = pts.slice(0, xray.index + 1);
    if (shownPts.length === 0) return null;
    const lastPt = shownPts[shownPts.length - 1];
    return { pts: shownPts, lastPt, done: xray.index >= pts.length - 1 };
  }, [xray]);

  return (
    <div className="relative">
      <button
        onClick={() => setShowLines((v) => !v)}
        className={`absolute right-2 top-2 z-10 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition ${
          showLines
            ? "border-white/25 bg-white/[0.14] text-white"
            : "border-white/10 bg-black/50 text-white/60 hover:text-white"
        }`}
        style={
          showLines
            ? { boxShadow: "inset 0 -8px 12px -6px rgba(255,255,255,0.15), inset 0 -16px 16px -8px hsla(210,100%,70%,0.25)" }
            : undefined
        }
      >
        Tactical Lines
      </button>
      <svg
        viewBox="0 0 105 68"
        className="block w-full rounded-2xl"
        role="img"
        aria-label="Live pitch"
        onClick={(e) => {
          if (!(e.target as SVGElement).closest?.("[data-token]")) onClearFocus();
        }}
      >
        <defs>
          <linearGradient id="turf" x1="0" x2="1">
            <stop offset="0" stopColor="#0C2317" />
            <stop offset="0.5" stopColor="#0C2317" />
            <stop offset="1" stopColor="#0C2317" />
          </linearGradient>
        </defs>
        <rect width="105" height="68" fill="url(#turf)" />
        {Array.from({ length: 12 }).map((_, i) => (
          i % 2 === 0 ? (
            <rect key={i} x={i * 8.75} width="8.75" height="68" fill="#fff" opacity="0.018" />
          ) : null
        ))}
        <g fill="none" stroke="#fff" strokeOpacity="0.35" strokeWidth="0.3">
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
        <rect x="0.4" y="30" width="1.6" height="8" fill="none" stroke="#fff" strokeOpacity="0.35" strokeWidth="0.3" />
        <rect x="103" y="30" width="1.6" height="8" fill="none" stroke="#fff" strokeOpacity="0.35" strokeWidth="0.3" />

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
              style={{ transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)" }}
            />
          ))}

        {[...tokens.values()].map(({ d }) => (
          <g
            key={d.p.id}
            data-token={d.p.id}
            ref={(el) => {
              tokenRefs.current.set(d.p.id, el);
            }}
            transform={`translate(${d.x.toFixed(2)} ${d.y.toFixed(2)})`}
            opacity={d.side === "home" ? 0.92 : 0.85}
            className="cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onPlayerClick(d.p.id);
            }}
          >
            <circle
              r="1.6"
              fill={d.side === "home" ? HOME_C : AWAY_C}
              stroke="#090D16"
              strokeWidth="0.4"
              style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.6))" }}
            />
            <circle cx="-0.5" cy="-0.55" r="0.45" fill="#fff" opacity="0.5" />
            <text y="0.9" textAnchor="middle" fontSize="2.2" fontWeight="700" fill="#fff">
              {d.p.number}
            </text>
            {d.p.id === focusedId && (
              <circle r="2.6" fill="none" stroke="#fff" strokeWidth="0.45" opacity="0.95" />
            )}
            {d.p.id === carrierId && d.p.id !== focusedId && (
              <circle r="2.5" fill="none" stroke="#fff" strokeWidth="0.35" opacity="0.85" />
            )}
          </g>
        ))}

        {shown.map((e, i) => (
          <circle
            key={e.id}
            cx={toX(e.x)}
            cy={toY(e.y)}
            r="0.55"
            fill="#fff"
            opacity={0.06 + (0.22 * (i + 1)) / shown.length}
          />
        ))}

        {passVec ? (
          <path
            d={`M${passVec.x1} ${passVec.y1} L${passVec.x2} ${passVec.y2}`}
            stroke="#fff"
            strokeOpacity="0.55"
            strokeWidth="0.35"
            strokeDasharray="4 4"
            fill="none"
          />
        ) : (
          passFrom &&
          last && (
            <path
              d={`M${toX(passFrom.x)} ${toY(passFrom.y)} L${toX(last.x)} ${toY(last.y)}`}
              stroke="#fff"
              strokeOpacity="0.55"
              strokeWidth="0.35"
              strokeDasharray="4 4"
              fill="none"
            />
          )
        )}

        {shot && (
          <g>
            <line
              x1={shot.sx}
              y1={shot.sy}
              x2={shot.gx}
              y2={clamp(toY(shot.evt.y), 28, 40)}
              stroke="#fff"
              strokeOpacity="0.85"
              strokeWidth="0.4"
            />
            <circle
              cx={shot.gx}
              cy={clamp(toY(shot.evt.y), 29, 39)}
              r="1.1"
              fill="#fff"
            />
          </g>
        )}

        {xrayPts && xray && (
          <g>
            <polyline
              points={xrayPts.pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")}
              fill="none"
              stroke="#fff"
              strokeOpacity="0.8"
              strokeWidth="0.4"
              strokeDasharray="4 4"
            />
            {xrayPts.pts.map((p, i) => (
              <circle
                key={i}
                cx={p.x}
                cy={p.y}
                r={i === xrayPts.pts.length - 1 ? 1.3 : 0.8}
                fill={i === xrayPts.pts.length - 1 ? "#fff" : "#94A3B8"}
                stroke="#090D16"
                strokeWidth="0.3"
              />
            ))}
            <g>
              <rect
                x={Math.min(78, Math.max(2, xrayPts.lastPt.x - 11))}
                y={Math.max(1, xrayPts.lastPt.y - 12)}
                width="22"
                height={xrayPts.done ? 10 : 6}
                rx="2"
                fill="#090D16"
                fillOpacity="0.92"
                stroke="#fff"
                strokeOpacity="0.25"
                strokeWidth="0.25"
              />
              {xrayPts.done ? (
                <>
                  <text
                    x={Math.min(78, Math.max(2, xrayPts.lastPt.x - 11)) + 2}
                    y={Math.max(1, xrayPts.lastPt.y - 12) + 3.6}
                    fontSize="2.4"
                    fontWeight="700"
                    fill="#fff"
                  >
                    xG {(xray.xg ?? 0).toFixed(2)}
                    {xray.speed !== null ? ` · ${xray.speed.toFixed(0)} km/h` : ""}
                  </text>
                  <text
                    x={Math.min(78, Math.max(2, xrayPts.lastPt.x - 11)) + 2}
                    y={Math.max(1, xrayPts.lastPt.y - 12) + 7}
                    fontSize="2"
                    fill="#9aa6c0"
                  >
                    {xrayPts.pts[xrayPts.pts.length - 1]?.label ?? ""}
                  </text>
                </>
              ) : (
                <text
                  x={Math.min(78, Math.max(2, xrayPts.lastPt.x - 11)) + 2}
                  y={Math.max(1, xrayPts.lastPt.y - 12) + 4}
                  fontSize="2.2"
                  fontWeight="600"
                  fill="#fff"
                >
                  {xrayPts.pts[xrayPts.pts.length - 1]?.label ?? ""}
                </text>
              )}
            </g>
          </g>
        )}

        {actors.map((a) => {
          const surname = a.info.name.split(" ").slice(-1)[0] ?? "";
          const pillW = surname.length * 1.3 + 2.4;
          return (
            <g key={a.d.p.id} transform={`translate(${a.x.toFixed(2)} ${a.y.toFixed(2)})`}>
              <circle r="2.6" fill={a.d.side === "home" ? HOME_C : AWAY_C} stroke="#fff" strokeWidth="0.35" />
              <text y="0.9" textAnchor="middle" fontSize="2.4" fontWeight="700" fill="#fff">
                {a.info.number}
              </text>
              <rect
                x={-pillW / 2}
                y="-7.2"
                width={pillW}
                height="3.4"
                rx="1.7"
                fill="#090D16"
                fillOpacity="0.92"
              />
              <text y="-4.6" textAnchor="middle" fontSize="2.2" fontWeight="600" fill="#fff">
                {surname}
              </text>
            </g>
          );
        })}

        <g ref={ballRef}>
          <circle r="1.4" fill="#fff" stroke="#090D16" strokeOpacity="0.3" strokeWidth="0.3" />
          <circle cx="-0.4" cy="-0.45" r="0.42" fill="#fff" opacity="0.9" />
        </g>

        {shotXg !== null && (
          <g>
            <rect x="80" y="55" width="22" height="8" rx="2" fill="#090D16" fillOpacity="0.85" stroke="#fff" strokeOpacity="0.2" strokeWidth="0.2" />
            <text x="82" y="58.6" fontSize="2.1" fill="#94A3B8">SHOT xG</text>
            <text x="82" y="61.8" fontSize="3" fontWeight="700" fill="#fff">{shotXg.toFixed(2)}</text>
          </g>
        )}
        <text x="6" y="64" fontSize="2" fill="#fff" fillOpacity="0.5">{attackLabel} ATTACK →</text>
      </svg>
    </div>
  );
}
