import { motion } from "framer-motion";
import { Volume2 } from "lucide-react";
import type { MomentDetail } from "../types";
import Glass from "./Glass";

export default function Narrative({
  featured,
  mode,
  empty,
  idleTitle,
  onListen,
  speaking,
}: {
  featured: MomentDetail | null;
  mode: string;
  empty: string;
  idleTitle?: string;
  onListen?: () => void;
  speaking?: boolean;
}) {
  return (
    <Glass className="overflow-hidden p-0">
      <div className="flex items-center gap-2.5 px-5 pt-5">
        <span className="grid size-8 place-items-center rounded-lg border border-white/20 bg-[#101010] text-white">
          <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" style={{ filter: "drop-shadow(0 0 3px hsla(210,100%,70%,0.8))" }}><path d="M12 2l2.1 6.4L20 10l-5.9 1.6L12 18l-2.1-6.4L4 10l5.9-1.6z" /></svg>
        </span>
        <div>
          <div className="text-sm font-semibold tracking-tight text-white">MatchIQ AI</div>
          <div className="font-mono text-[11px] uppercase tracking-[0.16em] tabular-nums text-[#94A3B8]">
            {featured ? `${featured.moment_type} · ${featured.minute}′` : "—"}
          </div>
        </div>
        <span className="mi-chip ml-auto rounded-full px-2.5 py-0.5 text-[11px] font-semibold capitalize text-white/70">
          {mode}
        </span>
        {featured && onListen && (
          <button
            onClick={onListen}
            title="Listen to this moment"
            aria-label="Listen to this moment"
            className={`grid size-8 shrink-0 place-items-center rounded-full border transition ${
              speaking
                ? "border-white/25 bg-white/[0.14] text-white"
                : "border-white/10 bg-black/40 text-white/70 hover:text-white"
            }`}
          >
            {speaking ? (
              <span className="flex items-end gap-[2px]" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <i
                    key={i}
                    className="w-[2.5px] animate-pulse rounded-full bg-current"
                    style={{ height: `${7 + (i % 3) * 3}px`, animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </span>
            ) : (
              <Volume2 size={14} aria-hidden />
            )}
          </button>
        )}
      </div>
      <div aria-live="polite">
        {featured ? (
          <motion.div
            key={featured.moment_id}
            initial={{ opacity: 0.35, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="border-l-2 border-[#5EA0FF]/70 px-5 py-4"
          >
            <h2 className="text-[22px] font-semibold leading-snug tracking-tight text-white">
              {featured.line ?? featured.story}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-[#94A3B8]">{featured.explanation}</p>
          </motion.div>
        ) : (
          <div key="empty" className="flex items-start gap-3 px-5 py-4">
            <span className="mt-0.5 flex h-8 items-end gap-[3px]" aria-hidden>
              {[0, 1, 2, 3].map((i) => (
                <i
                  key={i}
                  className="mi-eq w-[3px] rounded-full bg-[#5EA0FF]/80"
                  style={{ height: `${10 + (i % 4) * 5}px`, animationDelay: `${i * 160}ms` }}
                />
              ))}
            </span>
            <div>
              {idleTitle && (
                <div className="text-sm font-medium tracking-tight text-white/80">{idleTitle}</div>
              )}
              <p className="mt-0.5 text-sm leading-relaxed text-white/45">{empty}</p>
            </div>
          </div>
        )}
      </div>
    </Glass>
  );
}
