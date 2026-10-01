import type { MomentDetail } from "../types";
import Glass from "./Glass";

export default function Narrative({
  featured,
  mode,
  empty,
}: {
  featured: MomentDetail | null;
  mode: string;
  empty: string;
}) {
  return (
    <Glass className="rounded-[28px] p-5">
      <div className="flex items-center gap-2.5">
        <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-mint to-sky text-ink">
          <svg viewBox="0 0 24 24" className="size-4" fill="currentColor">
            <path d="M12 2l2.1 6.4L20 10l-5.9 1.6L12 18l-2.1-6.4L4 10l5.9-1.6z" />
          </svg>
        </span>
        <div>
          <div className="font-display text-sm font-semibold">MatchIQ AI</div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-white/45">
            {featured ? `${featured.moment_type} · ${featured.minute}′` : "—"}
          </div>
        </div>
        <span className="ml-auto rounded-full border border-mint/30 bg-mint/10 px-2.5 py-0.5 text-[11px] font-semibold capitalize text-mint">
          {mode}
        </span>
      </div>
      {featured ? (
        <>
          <h2 className="mt-5 font-display text-xl font-semibold leading-snug">
            {featured.line ?? featured.story}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-white/65">{featured.explanation}</p>
        </>
      ) : (
        <p className="mt-5 text-sm leading-relaxed text-white/50">{empty}</p>
      )}
    </Glass>
  );
}
