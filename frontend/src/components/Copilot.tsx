import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../types";
import type { Profile } from "../types";
import GenerateButton from "./GenerateButton";

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
  onSpeak,
  speaking,
  externalAsk,
}: {
  profile: Profile;
  homeName: string;
  awayName: string;
  title: string;
  placeholder: string;
  thinking: string;
  errorText: string;
  onSpeak?: (text: string) => void;
  speaking?: boolean;
  /** Pundit rupture questions injected from the pitch: asked once on change. */
  externalAsk?: { q: string; n: number } | null;
}) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<CopilotResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const askedNonce = useRef(0);

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

  useEffect(() => {
    if (externalAsk && externalAsk.n !== askedNonce.current) {
      askedNonce.current = externalAsk.n;
      setQuery(externalAsk.q);
      void ask(externalAsk.q);
    }
    // ask is intentionally Stable-by-closure: fires once per nonce.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalAsk]);

  return (
    <div className="mi-surface p-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="grid size-8 place-items-center rounded-lg border border-white/20 bg-[#101010] text-white">
          <Sparkles size={16} />
        </span>
        <span className="text-sm font-semibold tracking-tight text-white">{title}</span>
      </div>
      <div className="mb-2.5 flex flex-wrap gap-1.5">
        {quickPills(homeName, awayName, profile.lang).map((pill) => (
          <button
            key={pill}
            onClick={() => {
              setQuery(pill);
              void ask(pill);
            }}
            className="rounded-full border border-white/10 bg-black/40 px-2.5 py-1 text-[11px] text-white/70 transition hover:border-[hsla(210,100%,70%,0.5)] hover:text-white"
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
          className="mi-input min-w-0 flex-1 rounded-full px-3.5 py-2 text-sm text-white placeholder:text-white/35"
        />
        <GenerateButton
          small
          idle={profile.lang === "uk" ? "Питай" : "Ask"}
          busy={profile.lang === "uk" ? "Думаю" : "Thinking"}
          isBusy={loading}
          disabled={loading || !query.trim()}
          title="send"
        />
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
                className="mi-chip rounded-full px-2 py-0.5 font-mono text-[11px] tabular-nums text-white/70"
              >
                {b}
              </span>
            ))}
          </div>
          <p className="text-sm leading-relaxed text-white">{response.answer}</p>
          {onSpeak && (
              <button
              onClick={() => onSpeak(response.answer)}
              title="Read this answer aloud"
              aria-label="Read this answer aloud"
              className={`mt-2 grid size-8 place-items-center rounded-full border transition ${
                speaking
                  ? "border-white/25 bg-white/[0.14] text-white"
                  : "border-white/10 bg-black/40 text-white/70 hover:text-white"
              }`}
            >
              <Volume2 size={14} aria-hidden />
            </button>
          )}
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
                className="rounded-full border border-white/10 bg-black/40 px-2.5 py-1 text-[11px] text-white/70 transition hover:border-[hsla(210,100%,70%,0.5)] hover:text-white"
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
