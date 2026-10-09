import { AnimatePresence, motion } from "framer-motion";
import type { MomentDetail } from "../types";
import Glass from "./Glass";

export default function Narrative({
  featured,
  mode,
  empty,
  onListen,
  speaking,
}: {
  featured: MomentDetail | null;
  mode: string;
  empty: string;
  onListen?: () => void;
  speaking?: boolean;
}) {
  return (
    <Glass className="overflow-hidden p-0">
      <div className="flex items-center gap-2.5 px-5 pt-5">
        <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-home to-homedeep text-ink">
          <svg viewBox="0 0 24 24" className="size-4" fill="currentColor"><path d="M12 2l2.1 6.4L20 10l-5.9 1.6L12 18l-2.1-6.4L4 10l5.9-1.6z" /></svg>
        </span>
        <div>
          <div className="font-display text-sm font-semibold">MatchIQ AI</div>
          <div className="font-mono text-[11px] uppercase tracking-[0.16em] tabular-nums tracking-tight text-white/45">
            {featured ? `${featured.moment_type} · ${featured.minute}′` : "—"}
          </div>
        </div>
        <span className="ml-auto rounded-full border border-home/30 bg-home/10 px-2.5 py-0.5 text-[11px] font-semibold capitalize text-home">
          {mode}
        </span>
        {featured && onListen && (
          <button
            onClick={onListen}
            title="Listen to this moment"
            aria-label="Listen to this moment"
            className={`grid size-8 shrink-0 place-items-center rounded-full transition ${
              speaking ? "bg-home text-ink" : "bg-white/10 text-white/70 hover:bg-white/20 hover:text-white"
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
              "🔊"
            )}
          </button>
        )}
      </div>
      <AnimatePresence mode="wait">
        {featured ? (
          <motion.div
            key={featured.moment_id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="border-l-4 border-home bg-gradient-to-r from-home/10 to-transparent px-5 py-4"
          >
            <h2 className="font-display text-[22px] font-bold leading-snug tracking-tight">
              {featured.line ?? featured.story}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-white/65">{featured.explanation}</p>
          </motion.div>
        ) : (
          <motion.p
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-5 py-4 text-sm leading-relaxed text-white/50"
          >
            {empty}
          </motion.p>
        )}
      </AnimatePresence>
    </Glass>
  );
}
