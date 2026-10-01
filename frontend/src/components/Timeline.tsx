import type { MomentInfo, Segment } from "../types";

const SEG_COLORS: Record<string, string> = {
  control: "#38bdf8",
  high_press: "#f59e0b",
  tactical_shift: "#a78bfa",
  momentum_swing: "#34d399",
  balanced: "#475569",
};

export default function Timeline({
  segments,
  moments,
  minute,
  onSeek,
  why,
}: {
  segments: Segment[];
  moments: MomentInfo[];
  minute: number;
  onSeek: (minute: number) => void;
  why: string;
}) {
  const marks = moments.filter((m) =>
    ["goal", "tactical_shift", "momentum_swing"].includes(m.type),
  );
  return (
    <div>
      <div className="relative h-6 overflow-hidden rounded bg-slate-800">
        {segments.map((s) => (
          <div
            key={`${s.start_minute}-${s.label}-${s.team_id ?? "x"}`}
            title={`${s.title} (${s.start_minute}-${s.end_minute})`}
            className="absolute top-0 h-full opacity-70"
            style={{
              left: `${(s.start_minute / 90) * 100}%`,
              width: `${((s.end_minute - s.start_minute + 1) / 90) * 100}%`,
              background: SEG_COLORS[s.label] ?? "#475569",
            }}
          />
        ))}
        {marks.map((m) => (
          <button
            key={m.id}
            title={`${m.title} — ${why}`}
            onClick={() => onSeek(m.minute)}
            className="absolute top-0 h-full w-1.5 -translate-x-1/2 cursor-pointer bg-white hover:w-2.5"
            style={{ left: `${(m.minute / 90) * 100}%` }}
          />
        ))}
        <div
          className="absolute top-0 h-full w-0.5 bg-red-400"
          style={{ left: `${(Math.min(90, minute) / 90) * 100}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-400">
        <span>0&prime;</span>
        <span>
          {marks
            .map((m) => `${m.minute}′ ${m.type === "goal" ? "⚽" : "◆"}`)
            .join("  ·  ")}
        </span>
        <span>90&prime;</span>
      </div>
    </div>
  );
}
