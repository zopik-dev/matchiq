import { useEffect, useState } from "react";
import {
  Activity,
  BrainCircuit,
  Cloud,
  CloudOff,
  Database,
  Mic,
  Server,
  X,
} from "lucide-react";
import { API_BASE } from "../types";

export interface StackStrings {
  stackTitle: string;
  stackCompute: string;
  stackComputeDesc: string;
  stackModels: string;
  stackModelsDesc: string;
  stackAudio: string;
  stackAudioDesc: string;
  stackStore: string;
  stackStoreDesc: string;
  stackLatency: string;
  stackProviderCloud: string;
  stackProviderMock: string;
  stackClose: string;
}

interface Integrations {
  llm: { provider: string; deployment: string | null };
  speech: { provider: string; region: string | null };
  store: { provider: string };
}

function Row({
  icon,
  title,
  desc,
  badge,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
  badge: string;
}) {
  return (
    <div className="mi-tile flex items-center gap-3 p-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-white/20 bg-[#101010] text-white">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold tracking-tight text-white">{title}</div>
        <div className="truncate text-xs text-white/55">{desc}</div>
      </div>
      <span className="shrink-0 rounded-full bg-white/[0.07] px-2 py-0.5 font-mono text-[10px] tabular-nums text-white/70">
        {badge}
      </span>
    </div>
  );
}

/** Glassmorphic Microsoft stack inspector: live provider status + latency. */
export default function AzureStack({
  open,
  onClose,
  t,
}: {
  open: boolean;
  onClose: () => void;
  t: StackStrings;
}) {
  const [data, setData] = useState<Integrations | null>(null);
  const [latency, setLatency] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setData(null);
    setLatency(null);
    const started = performance.now();
    fetch(`${API_BASE}/api/integrations`)
      .then((res) => {
        if (!res.ok) throw new Error(`integrations failed: ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        if (!cancelled) {
          setData(payload as Integrations);
          setLatency(Math.round(performance.now() - started));
        }
      })
      .catch(() => {
        if (!cancelled) setLatency(null);
      });
    return () => {
      cancelled = true;
    };
  }, [open ]);

  if (!open) return null;
  const cloud = data?.llm.provider === "azure-foundry";
  return (
    <div
      className="fixed inset-0 z-40 grid place-items-center bg-black/60 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t.stackTitle}
        onClick={(e) => e.stopPropagation()}
        className="mi-surface w-full max-w-md p-5"
      >
        <div className="mb-1 flex items-center justify-between">
          <span className="flex items-center gap-2 text-sm font-semibold tracking-tight text-white">
            <span className="relative flex size-2" aria-hidden>
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
            </span>
            {t.stackTitle}
          </span>
          <button
            onClick={onClose}
            aria-label={t.stackClose}
            className="grid size-8 place-items-center rounded-full bg-white/[0.07] text-white/70 transition hover:bg-white/[0.12] hover:text-white"
          >
            <X size={14} />
          </button>
        </div>
        <p className="mb-3 flex items-center gap-1.5 font-mono text-[11px] tabular-nums text-white/55">
          {cloud ? (
            <Cloud size={12} className="text-emerald-400" aria-hidden />
          ) : (
            <CloudOff size={12} className="text-[#94A3B8]" aria-hidden />
          )}
          {data ? (cloud ? t.stackProviderCloud : t.stackProviderMock) : "…"}
          {latency !== null && (
            <span className="ml-auto flex items-center gap-1">
              <Activity size={12} className="text-[#94A3B8]" aria-hidden />
              {t.stackLatency}: {latency}ms
            </span>
          )}
        </p>
        <div className="flex flex-col gap-2">
          <Row
            icon={<Server size={16} aria-hidden />}
            title={t.stackCompute}
            desc={t.stackComputeDesc}
            badge="serverless"
          />
          <Row
            icon={<BrainCircuit size={16} aria-hidden />}
            title={t.stackModels}
            desc={t.stackModelsDesc}
            badge={
              data
                ? (data.llm.deployment ?? (cloud ? "foundry" : "mock"))
                : "…"
            }
          />
          <Row
            icon={<Mic size={16} aria-hidden />}
            title={t.stackAudio}
            desc={
              data && data.speech.provider === "azure" && data.speech.region
                ? `${t.stackAudioDesc} · ${data.speech.region}`
                : t.stackAudioDesc
            }
            badge={data ? data.speech.provider : "…"}
          />
          <Row
            icon={<Database size={16} aria-hidden />}
            title={t.stackStore}
            desc={t.stackStoreDesc}
            badge={data ? data.store.provider : "…"}
          />
        </div>
      </div>
    </div>
  );
}
