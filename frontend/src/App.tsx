import { Flag } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { controls, fetchMatch, streamUrl } from "./api";
import Breakdown from "./components/Breakdown";
import Feed from "./components/Feed";
import Glass from "./components/Glass";
import Header, { BrandMark } from "./components/Header";
import Metrics from "./components/Metrics";
import Narrative from "./components/Narrative";
import Pitch from "./components/Pitch";
import PressureTimeline from "./components/PressureTimeline";
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
      setHops((prev) => [...prev, ...((d as { hops: Hop[] }).hops ?? [])]),
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

  const lookup = useCallback(
    (id: string | null) => {
      if (!id || !match) return null;
      for (const tm of match.meta.teams) {
        const p = tm.roster.find((r) => r.id === id);
        if (p) return { name: p.name, number: p.number };
      }
      return null;
    },
    [match],
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
        {t.connecting} — {t.backendDown}
      </div>
    );
  }

  const minute = replay?.minute ?? 0;
  const featured = feed.length > 0 ? feed[feed.length - 1] : null;
  const chances = match.moments.filter(
    (m) => m.type === "big_chance" || m.type === "goal",
  ).length;

  return (
    <div className="relative min-h-screen overflow-hidden bg-ink text-white">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 30% 0%, rgba(62,230,160,0.10), transparent 70%), radial-gradient(50% 45% at 100% 20%, rgba(106,183,255,0.10), transparent 70%)",
        }}
      />

      <Header
        home={home}
        away={away}
        replay={replay}
        profile={profile}
        onProfile={changeProfile}
        onSeek={(m) => void doSeek(m)}
        onReplay={setReplay}
        connected={connected}
        t={t}
      />

      <main className="relative mx-auto grid max-w-[1400px] gap-6 px-4 pb-14 pt-8 lg:grid-cols-[minmax(0,1fr)_400px] lg:px-8">
        <section className="flex flex-col gap-6">
          <Glass className="rounded-[28px] p-3 sm:p-4">
            <div className="flex items-center justify-between px-2 pb-3 pt-1">
              <div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-white/45">
                  {t.matchCentre}
                </div>
                <h1 className="font-display text-xl font-semibold">
                  <BrandMark /> · {home.name} vs {away.name}
                </h1>
              </div>
              <div className="hidden items-center gap-4 text-xs text-white/60 sm:flex">
                <span className="flex items-center gap-1.5">
                  <i className="size-2.5 rounded-full bg-sky" />
                  {home.name}
                </span>
                <span className="flex items-center gap-1.5">
                  <i className="size-2.5 rounded-full bg-amber" />
                  {away.name}
                </span>
              </div>
            </div>
            <div className="overflow-hidden rounded-2xl shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_30px_80px_-30px_rgba(62,230,160,0.35)]">
              <Pitch
                home={home}
                away={away}
                events={events}
                featured={featured}
                lookup={lookup}
                attackLabel={home.name.split(" ")[0].toUpperCase()}
              />
            </div>
          </Glass>

          <Glass className="rounded-[28px] p-5">
            <PressureTimeline
              series={match.momentum_series}
              moments={match.moments}
              minute={minute}
              homeId={home.id}
              homeName={home.name}
              awayName={away.name}
              onSeek={(m) => void doSeek(m)}
              title={t.pressure}
              hint={t.hoverScrub}
            />
          </Glass>
        </section>

        <aside className="flex flex-col gap-4 lg:sticky lg:top-24 lg:self-start">
          <Narrative featured={featured} mode={profile.mode} empty={t.noMoments} />

          <Metrics
            title={t.metricsTitle}
            possessionLabel={t.possession}
            shotLabel={t.shotXg}
            matchLabel={t.matchXg}
            momentumLabel={t.momentumNow}
            chancesLabel={t.bigChances}
            featured={featured}
            totals={match.totals}
            momentum={momentum}
            chances={chances}
            homeName={home.name}
            awayName={away.name}
            lookup={lookup}
          />

          <Breakdown title={t.breakdown} featured={featured} events={events} lookup={lookup} />

          <Glass className="rounded-[28px] p-5">
            <div className="mb-3 flex flex-wrap items-center gap-3 text-xs">
              <label className="flex items-center gap-1.5 text-white/60">
                <Flag size={13} /> {t.club}
                <select
                  value={profile.club ?? ""}
                  onChange={(e) => changeProfile({ club: e.target.value || null })}
                  className="rounded-full bg-black/30 px-2 py-1 text-white"
                >
                  <option value="">{t.noClub}</option>
                  {[home, away].map((tm) => (
                    <option key={tm.id} value={tm.id}>
                      {tm.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-1.5 text-white/60">
                {t.focus}
                <select
                  value={profile.focus ?? ""}
                  onChange={(e) => changeProfile({ focus: e.target.value || null })}
                  className="max-w-44 rounded-full bg-black/30 px-2 py-1 text-white"
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
            <div className="mb-3 flex items-center justify-between">
              <span className="font-display text-sm font-semibold">{t.storyline}</span>
              <span className="font-mono text-[11px] text-white/40">
                {feed.length}/{match.moments.length}
              </span>
            </div>
            <div className="max-h-[40vh] overflow-y-auto pr-0.5">
              {feed.length === 0 ? (
                <p className="text-sm text-white/40">{t.noMoments}</p>
              ) : (
                <Feed items={feed} />
              )}
            </div>
          </Glass>
        </aside>
      </main>

      <footer className="relative mx-auto max-w-[1400px] px-4 pb-10 lg:px-8">
        <TracePanel hops={hops} title={t.trace} />
      </footer>
    </div>
  );
}
