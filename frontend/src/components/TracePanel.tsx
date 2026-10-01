import { ArrowRight, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { Hop } from "../types";

export default function TracePanel({
  hops,
  title,
}: {
  hops: Hop[];
  title: string;
}) {
  const [open, setOpen] = useState(false);
  const byMoment = new Map<string, Hop[]>();
  for (const hop of hops) {
    const key = hop.message_id.replace(/-(context|explanation|story|personalized)$/, "");
    const list = byMoment.get(key) ?? [];
    list.push(hop);
    byMoment.set(key, list);
  }
  return (
    <div className="rounded-[28px] border border-white/[0.08] bg-white/[0.045] p-4 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.7)] backdrop-blur-2xl">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-semibold text-white/85"
      >
        <span>
          {title} ({hops.length})
        </span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && (
        <div className="mt-2 max-h-48 space-y-1 overflow-y-auto font-mono text-[11px] text-white/70">
          {[...byMoment.entries()].slice(-12).map(([key, list]) => (
            <div key={key} className="rounded-xl bg-black/30 px-2 py-1">
              <span className="text-white/40">{key} </span>
              {list.map((h, i) => (
                <span key={h.seq}>
                  {i > 0 && <span className="text-white/25"> → </span>}
                  <span
                    className={
                      h.ok ? (h.degraded ? "text-amber" : "text-mint") : "text-red-400"
                    }
                  >
                    {h.sender}
                    <ArrowRight size={10} className="inline" />
                    {h.receiver}
                    {h.attempts > 1 ? `×${h.attempts}` : ""}
                  </span>
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
