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
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-semibold text-slate-200"
      >
        <span>
          {title} ({hops.length})
        </span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && (
        <div className="mt-2 max-h-48 space-y-1 overflow-y-auto font-mono text-[11px] text-slate-300">
          {[...byMoment.entries()].slice(-12).map(([key, list]) => (
            <div key={key} className="rounded bg-slate-800 px-2 py-1">
              <span className="text-slate-500">{key} </span>
              {list.map((h, i) => (
                <span key={h.seq}>
                  {i > 0 && <span className="text-slate-600"> → </span>}
                  <span
                    className={h.ok ? (h.degraded ? "text-amber-300" : "text-emerald-300") : "text-red-300"}
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
