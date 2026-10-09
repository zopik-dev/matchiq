import { AnimatePresence, motion } from "framer-motion";
import { CornerDownLeft, Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import { API_BASE } from "../types";
import type { Profile } from "../types";

export interface CopilotEvent {
  minute: number;
  timestamp_s: number;
  type: string;
  team_id: string | null;
  player_id: string | null;
  x: number;
  y: number;
  xg: number | null;
}

export interface CopilotResponse {
  answer: string;
  evidence: Record<string, unknown>;
  relevant_events: CopilotEvent[];
  suggested_followups: string[];
}

function badges(evidence: Record<string, unknown>): string[] {
  const out: string[] = [];
  if (typeof evidence["xg"] === "number") out.push(`xG ${(evidence["xg"] as number).toFixed(2)}`);
  if (typeof evidence["score"] === "string") out.push(`${evidence["score"]}`);
  if (typeof evidence["pressure_events"] === "number")
    out.push(`${evidence["pressure_events"]} duels/5min`);
  if (typeof evidence["momentum"] === "number")
    out.push(`momentum ${(evidence["momentum"] as number).toFixed(0)}`);
  if (typeof evidence["possession_pct"] === "number")
    out.push(`poss ${(evidence["possession_pct"] as number).toFixed(0)}%`);
  return out;
}

export function quickPills(home: string, away: string, lang: "en" | "uk"): string[] {
  if (lang === "uk") {
    return [
      `Чому ${away} забив на 57-й?`,
      `Поясни переможну контратаку на 89-й`,
      `Як зламався пресинг ${home}?`,
    ];
  }
  return [
    `Why did ${away} score at 57'?`,
    `Explain the 89' winning counter-attack`,
    `How did ${home}'s press break down?`,
  ];
}

export default function Copilot({
  profile,
  homeName,
  awayName,
  title,
  placeholder,
  thinking,
  errorText,
}: {
  profile: Profile;
  homeName: string;
  awayName: string;
  title: string;
  placeholder: string;
  thinking: string;
  errorText: string;
}) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<CopilotResponse | null>(null);
  const [failed, setFailed] = useState(false);

  const ask = async (q: string) => {
    const text = q.trim();
    if (!text || loading) return;
    setLoading(true);
    setFailed(false);
    try {
      const res = await fetch(`${API_BASE}/api/copilot/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, mode: profile.mode, lang: profile.lang }),
      });
      if (!res.ok) throw new Error(`copilot failed: ${res.status}`);
      setResponse((await res.json()) as CopilotResponse);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-[28px] border border-white/[0.08] bg-white/[0.045] p-5 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.7)] backdrop-blur-2xl">
      <div className="mb-3 flex items-center gap-2">
        <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-home to-homedeep text-ink">
          <Sparkles size={16} />
        </span>
        <span className="font-display text-sm font-semibold">{title}</span>
      </div>
      <div className="mb-2.5 flex flex-wrap gap-1.5">
        {quickPills(homeName, awayName, profile.lang).map((pill) => (
          <button
            key={pill}
            onClick={() => {
              setQuery(pill);
              void ask(pill);
            }}
            className="rounded-full border border-white/10 bg-black/30 px-2.5 py-1 text-[11px] text-white/70 transition hover:border-mint/40 hover:text-white"
          >
            {pill}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(query);
        }}
        className="flex items-center gap-2"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-full border border-white/10 bg-black/30 px-3.5 py-2 text-sm text-white placeholder:text-white/35 focus:border-mint/50 focus:outline-none"
        />
        <button
          type="submit"
          aria-label="send"
          className="grid size-9 shrink-0 place-items-center rounded-full bg-white text-ink transition hover:bg-mint disabled:opacity-40"
          disabled={loading || !query.trim()}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <CornerDownLeft size={16} />}
        </button>
      </form>
      {loading && <p className="mt-3 text-xs text-white/45">{thinking}</p>}
      {failed && !loading && <p className="mt-3 text-xs text-red-300">{errorText}</p>}
      <AnimatePresence mode="wait">
        {response && !loading && (
          <motion.div
            key={response.answer.slice(0, 48)}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="mt-3"
          >
          <div className="mb-1.5 flex flex-wrap gap-1">
            {badges(response.evidence).map((b) => (
              <span
                key={b}
                className="rounded-full border border-home/30 bg-home/10 px-2 py-0.5 font-mono text-[11px] tabular-nums tracking-tight text-home"
              >
                {b}
              </span>
            ))}
          </div>
          <p className="text-sm leading-snug text-white/85">{response.answer}</p>
          {response.relevant_events.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {response.relevant_events.map((e, i) => (
                <span
                  key={`${e.timestamp_s}-${i}`}
                  className="rounded-full bg-white/10 px-2 py-0.5 font-mono text-[10px] tabular-nums tracking-tight text-white/60"
                >
                  {e.minute}&prime; {e.type}
                </span>
              ))}
            </div>
          )}
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {response.suggested_followups.map((f) => (
              <button
                key={f}
                onClick={() => {
                  setQuery(f);
                  void ask(f);
                }}
                className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-home transition hover:bg-white/20"
              >
                {f}
              </button>
            ))}
          </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
