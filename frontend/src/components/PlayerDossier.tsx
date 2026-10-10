import { AnimatePresence, motion } from "framer-motion";
import { Shirt, X } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "../types";
import type { Profile } from "../types";
import Glass from "./Glass";

interface Dossier {
  player_id: string;
  name: string;
  number: number;
  position: string;
  team_id: string;
  team_name: string;
  touches: number;
  passes: number;
  passes_completed: number;
  pass_accuracy: number;
  shots: number;
  xg: number;
  goals: number;
  duels_won: number;
  final_third_entries: number;
  distance_m: number;
  top_speed_kmh: number;
  insight: string;
}

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-white/[0.04] bg-[#131C30] p-3">
      <div className="text-[10px] uppercase tracking-[0.14em] text-[#94A3B8]">{label}</div>
      <div className="mt-0.5 font-mono text-xl font-semibold tabular-nums text-white">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-white/50">{sub}</div>}
    </div>
  );
}

export default function PlayerDossier({
  playerId,
  profile,
  empty,
  labels,
  onClear,
}: {
  playerId: string | null;
  profile: Profile;
  empty: string;
  labels: {
    passes: string;
    accuracy: string;
    topSpeed: string;
    distance: string;
    duels: string;
    goals: string;
    clear: string;
  };
  onClear: () => void;
}) {
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!playerId) {
      setDossier(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(
      `${API_BASE}/api/players/${playerId}/telemetry?mode=${profile.mode}&lang=${profile.lang}`,
    )
      .then((res) => {
        if (!res.ok) throw new Error(`telemetry failed: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!cancelled) setDossier(data as Dossier);
      })
      .catch(() => {
        if (!cancelled) setDossier(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [playerId, profile.mode, profile.lang]);

  if (!playerId) {
    return (
      <Glass className="p-5">
        <p className="text-sm leading-relaxed text-white/50">{empty}</p>
      </Glass>
    );
  }

  return (
    <Glass className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] tabular-nums tracking-tight text-white/45">
          {dossier?.position ?? "···"} · {dossier?.team_name ?? ""}
        </span>
        <button
          onClick={onClear}
          className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-white/70 transition hover:bg-white/20 hover:text-white"
        >
          <X size={11} className="mr-1 inline" />
          {labels.clear}
        </button>
      </div>
      <AnimatePresence mode="wait">
        {loading || !dossier ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-sm text-white/50"
          >
            <Shirt size={32} className="text-white/25" />
            <span className="font-mono tabular-nums tracking-tight">···</span>
          </motion.div>
        ) : (
          <motion.div
            key={dossier.player_id + profile.mode + profile.lang}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            <div className="flex items-center gap-3">
              <span className="grid size-12 place-items-center rounded-lg bg-white font-mono text-xl font-bold text-black">
                {dossier.number}
              </span>
              <div>
                <h2 className="text-xl font-semibold leading-tight tracking-tight text-white">
                  {dossier.name}
                </h2>
                <p className="font-mono text-[11px] tabular-nums text-[#94A3B8]">
                  {dossier.touches} touches
                </p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2.5">
              <Tile
                label={labels.passes}
                value={`${dossier.passes_completed}/${dossier.passes}`}
                sub={`${labels.accuracy} ${dossier.pass_accuracy}%`}
              />
              <Tile
                label={labels.topSpeed}
                value={`${dossier.top_speed_kmh.toFixed(1)}`}
                sub="km/h"
              />
              <Tile
                label={labels.distance}
                value={`${(dossier.distance_m / 1000).toFixed(1)}`}
                sub="km"
              />
              {dossier.position === "FW" ? (
                <Tile
                  label={labels.goals}
                  value={`${dossier.goals}`}
                  sub={`xG ${dossier.xg.toFixed(2)}`}
                />
              ) : (
                <Tile label={labels.duels} value={`${dossier.duels_won}`} />
              )}
            </div>
            <p className="mt-3 border-l-2 border-white/25 pl-3 text-sm leading-snug text-white/85">
              {dossier.insight}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </Glass>
  );
}
