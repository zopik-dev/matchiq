import {
  Flag,
  Pause,
  Play,
  RotateCcw,
  Volleyball,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { controls, fetchMatch, streamUrl } from "./api";
import Feed from "./components/Feed";
import MomentumChart from "./components/MomentumChart";
import Pitch from "./components/Pitch";
import Timeline from "./components/Timeline";
import TracePanel from "./components/TracePanel";
import { STR } from "./strings";
import type {
  Hop,
  MatchPayload,
  MomentDetail,
  PitchEvent,
  Profile,
  ReplayState,
} from "./types";

const SPEEDS = [1, 10, 60];

export default function App() {
  const [match, setMatch] = useState<MatchPayload | null>(null);
  const [profile, setProfile] = useState<Profile>({
    mode: "fan",
    lang: "en",
    club: null,
    focus: null,
  });
  const [streamKey, setStreamKey] = useState(0);
  const [connected, setConnected] = useState(false);
  const [replay, setReplay] = useState<ReplayState | null>(null);
  const [events, setEvents] = useState<PitchEvent[]>([]);
  const [feed, setFeed] = useState<MomentDetail[]>([]);
  const [hops, setHops] = useState<Hop[]>([]);
  const [momentum, setMomentum] = useState<{ home: number } | null>(null);
  const profileRef = useRef(profile);
  profileRef.current = profile;

  const t = STR[profile.lang];
  const home = match?.meta.teams[0];
  const away = match?.meta.teams[1];
  const names = useMemo(
    () => Object.fromEntries((match?.meta.teams ?? []).map((tm) => [tm.id, tm.name])),
    [match],
  );

  useEffect(() => {
    fetchMatch().then(setMatch).catch(() => setMatch(null));
  }, []);

  useEffect(() => {
    setConnected(false);
    setEvents([]);
    setFeed([]);
    setHops([]);
    const source = new EventSource(streamUrl(profileRef.current));
    const on = (kind: string, fn: (data: unknown) => void) => {
      source.addEventListener(kind, (e) => {
        fn(JSON.parse((e as MessageEvent).data));
      });
    };
    on("state", (d) => {
      setReplay(d as ReplayState);
      setConnected(true);
    });
    on("event", (d) =>
      setEvents((prev) => [...prev.slice(-59), d as PitchEvent]),
    );
    on("momentum", (d) => setMomentum(d as { home: number }));
    on("moment", (d) =>
      setFeed((prev) => {
        const detail = d as MomentDetail;
        if (prev.some((m) => m.moment_id === detail.moment_id)) return prev;
        return [...prev, detail];
      }),
    );
    on("trace", (d) =>
      setHops((prev) => [
        ...prev,
        ...((d as { hops: Hop[] }).hops ?? []),
      ]),
    );
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, [streamKey]);

  const reconnect = useCallback(() => setStreamKey((k) => k + 1), []);

  const changeProfile = useCallback(
    (patch: Partial<Profile>) => {
      setProfile((p) => ({ ...p, ...patch }));
      reconnect();
    },
    [reconnect],
  );

  const doSeek = useCallback(
    async (minute: number) => {
      await controls.seek(minute);
      reconnect();
    },
    [reconnect],
  );

  const players = useMemo(
    () =>
      (match?.meta.teams ?? []).flatMap((tm) =>
        tm.roster.map((p) => ({ ...p, team: tm.id })),
      ),
    [match],
  );

  if (!match || !home || !away) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink text-slate-300">
        {t.connecting} — is the backend running on :8000?
      </div>
    );
  }

  const minute = replay?.minute ?? 0;
  const score = replay?.score ?? { home: 0, away: 0 };

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-800 bg-panel px-4 py-2">
        <span className="flex items-center gap-1.5 rounded-md bg-sky-500/15 px-2 py-1 text-sm font-bold text-sky-300">
          <Zap size={15} /> MatchIQ
        </span>
        <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-4 py-1.5">
          <span className="text-sm font-semibold">{home.name}</span>
          <span className="rounded bg-slate-900 px-2 py-0.5 font-mono text-lg font-bold">
            {score.home} - {score.away}
          </span>
          <span className="text-sm font-semibold">{away.name}</span>
          <span className="font-mono text-xs text-slate-400">
            {minute.toFixed(0)}&prime;
          </span>
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
              replay?.playing ? "bg-red-500/20 text-red-300" : "bg-slate-700 text-slate-300"
            }`}
          >
            {replay?.playing ? t.live : t.paused}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            title={replay?.playing ? t.pause : t.play}
            onClick={async () => {
              setReplay(replay?.playing ? await controls.pause() : await controls.play());
            }}
            className="rounded-md bg-sky-600 p-1.5 hover:bg-sky-500"
          >
            {replay?.playing ? <Pause size={15} /> : <Play size={15} />}
          </button>
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={async () => setReplay(await controls.speed(s))}
              className={`rounded-md px-2 py-1 font-mono text-xs ${
                replay?.speed === s ? "bg-sky-600" : "bg-slate-700 hover:bg-slate-600"
              }`}
            >
              {s}x
            </button>
          ))}
          <button
            title={t.restart}
            onClick={() => void doSeek(0)}
            className="rounded-md bg-slate-700 p-1.5 hover:bg-slate-600"
          >
            <RotateCcw size={15} />
          </button>
        </div>
        <div className="flex items-center gap-1">
          {(["analyst", "fan", "beginner"] as const).map((m) => (
            <button
              key={m}
              onClick={() => changeProfile({ mode: m })}
              className={`rounded-md px-2 py-1 text-xs capitalize ${
                profile.mode === m ? "bg-emerald-600" : "bg-slate-700 hover:bg-slate-600"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {(["en", "uk"] as const).map((l) => (
            <button
              key={l}
              onClick={() => changeProfile({ lang: l })}
              className={`rounded-md px-2 py-1 font-mono text-xs uppercase ${
                profile.lang === l ? "bg-violet-600" : "bg-slate-700 hover:bg-slate-600"
              }`}
            >
              {l === "en" ? "EN" : "UA"}
            </button>
          ))}
        </div>
        {!connected && (
          <span className="flex items-center gap-1 text-xs text-amber-300">
            <Volleyball size={13} /> {t.connecting}
          </span>
        )}
      </header>

      <main className="grid grid-cols-1 gap-3 p-3 lg:grid-cols-[65%_35%]">
        <section className="flex flex-col gap-3">
          <div className="rounded-xl border border-slate-700 bg-panel p-3">
            <h2 className="mb-2 text-sm font-semibold text-slate-300">{t.pitch}</h2>
            <Pitch events={events} homeId={home.id} />
          </div>
          <div className="rounded-xl border border-slate-700 bg-panel p-3">
            <h2 className="mb-1 text-sm font-semibold text-slate-300">
              {t.momentum}
              {momentum !== null && (
                <span className="ml-2 font-mono text-xs text-slate-400">
                  {momentum.home >= 0 ? home.name : away.name} +{Math.abs(momentum.home).toFixed(0)}
                </span>
              )}
            </h2>
            <MomentumChart series={match.momentum_series} minute={minute} />
          </div>
          <div className="rounded-xl border border-slate-700 bg-panel p-3">
            <h2 className="mb-2 text-sm font-semibold text-slate-300">{t.timeline}</h2>
            <Timeline
              segments={match.segments}
              moments={match.moments}
              minute={minute}
              onSeek={(m) => void doSeek(m)}
              why={t.why}
            />
          </div>
        </section>

        <section className="flex min-h-[60vh] flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-700 bg-panel p-3 text-xs">
            <label className="flex items-center gap-1 text-slate-300">
              <Flag size={13} /> {t.club}
              <select
                value={profile.club ?? ""}
                onChange={(e) => changeProfile({ club: e.target.value || null })}
                className="rounded bg-slate-700 px-1 py-1 text-slate-100"
              >
                <option value="">{t.noClub}</option>
                {[home, away].map((tm) => (
                  <option key={tm.id} value={tm.id}>
                    {tm.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1 text-slate-300">
              {t.focus}
              <select
                value={profile.focus ?? ""}
                onChange={(e) => changeProfile({ focus: e.target.value || null })}
                className="max-w-44 rounded bg-slate-700 px-1 py-1 text-slate-100"
              >
                <option value="">{t.all}</option>
                {players.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({names[p.team]})
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-300">{t.storyline}</h2>
            <span className="font-mono text-[11px] text-slate-500">
              {match.moments.filter((m) => m.type === "goal").length} goals ·{" "}
              {match.moments.length} moments
            </span>
          </div>
          <div className="max-h-[52vh] min-h-40 overflow-hidden">
            {feed.length === 0 ? (
              <p className="rounded-xl border border-slate-800 p-4 text-sm text-slate-500">
                {t.noMoments}
              </p>
            ) : (
              <Feed items={feed} />
            )}
          </div>
        </section>
      </main>

      <footer className="p-3 pt-0">
        <TracePanel hops={hops} title={t.trace} />
      </footer>
    </div>
  );
}
