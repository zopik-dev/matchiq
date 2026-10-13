import { AnimatePresence, motion } from "framer-motion";
import { Flag } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { controls, fetchMatch, streamUrl } from "./api";
import { useCommentaryAudio } from "./hooks/useCommentaryAudio";
import { useStadiumAmbience } from "./hooks/useStadiumAmbience";
import Breakdown from "./components/Breakdown";
import Copilot from "./components/Copilot";
import Feed from "./components/Feed";
import Glass from "./components/Glass";
import Header, { BrandMark } from "./components/Header";
import LowerThird from "./components/LowerThird";
import Metrics from "./components/Metrics";
import Narrative from "./components/Narrative";
import Pitch from "./components/Pitch";
import PlayerDossier from "./components/PlayerDossier";
import PressureTimeline from "./components/PressureTimeline";
import Scorebug from "./components/Scorebug";
import TracePanel from "./components/TracePanel";
import { STR } from "./strings";
import type {
  Hop,
  MatchPayload,
  MomentDetail,
  PitchEvent,
  Profile,
  ReplayState,
  XrayData,
} from "./types";
import { API_BASE } from "./types";

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
  const [sideTab, setSideTab] = useState<"insight" | "player" | "copilot">("insight");
  const [focusPlayer, setFocusPlayer] = useState<string | null>(null);
  const [xray, setXray] = useState<XrayData | null>(null);
  const [xrayIndex, setXrayIndex] = useState(0);
  const [experience, setExperience] = useState<"tv" | "console">(() => {
    try {
      return localStorage.getItem("matchiq:experience") === "tv" ? "tv" : "console";
    } catch {
      return "console";
    }
  });
  const [lower, setLower] = useState<MomentDetail | null>(null);
  const [copilotAsk, setCopilotAsk] = useState<{ q: string; n: number } | null>(null);
  const profileRef = useRef(profile);
  profileRef.current = profile;
  const { isMuted, isSpeaking, audioSource, speak, stop, toggleMute } =
    useCommentaryAudio();
  const audioOn = !isMuted;
  const ambience = useStadiumAmbience({ muted: isMuted, speaking: isSpeaking });
  const ambienceRef = useRef(ambience);
  ambienceRef.current = ambience;
  // Refs so the SSE effect (subscribed once per streamKey) always sees
  // fresh audio state without resubscribing on every toggle.
  const speakRef = useRef(speak);
  speakRef.current = speak;
  const audioOnRef = useRef(audioOn);
  audioOnRef.current = audioOn;
  const langRef = useRef(profile.lang);
  langRef.current = profile.lang;
  const experienceRef = useRef(experience);
  experienceRef.current = experience;
  const lowerTimer = useRef<number | null>(null);
  const tvCutoff = useRef(-1);
  const showLower = useCallback((detail: MomentDetail) => {
    setLower(detail);
    if (lowerTimer.current) window.clearTimeout(lowerTimer.current);
    lowerTimer.current = window.setTimeout(() => setLower(null), 8000);
  }, []);
  const showLowerRef = useRef(showLower);
  showLowerRef.current = showLower;
  useEffect(
    () => () => {
      if (lowerTimer.current) window.clearTimeout(lowerTimer.current);
    },
    [],
  );
  // Experience with persistence; ESC always drops back to the console.
  const changeExperience = useCallback((next: "tv" | "console") => {
    setExperience(next);
    setLower(null);
    try {
      localStorage.setItem("matchiq:experience", next);
    } catch {
      /* private mode */
    }
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") changeExperience("console");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [changeExperience]);
  const teamsRef = useRef<{ homeId: string | undefined; awayId: string | undefined }>({
    homeId: undefined,
    awayId: undefined,
  });

  const t = STR[profile.lang];
  const home = match?.meta.teams[0];
  const away = match?.meta.teams[1];
  teamsRef.current = { homeId: home?.id, awayId: away?.id };
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
    // Playhead cutoff at (re)connect: moments at or before it are catch-up
    // history (never auto-announced); anything after it is genuinely live.
    tvCutoff.current = -1;
    const on = (kind: string, fn: (data: unknown) => void) => {
      source.addEventListener(kind, (e) => {
        fn(JSON.parse((e as MessageEvent).data));
      });
    };
    on("state", (d) => {
      const st = d as ReplayState;
      setReplay(st);
      setConnected(true);
      if (tvCutoff.current < 0) tvCutoff.current = st.minute * 60;
    });
    on("event", (d) => {
      const evt = d as PitchEvent;
      setEvents((prev) => [...prev.slice(-119), evt]);
      // Optimistic clock + score: the header must move on every event,
      // even if the next backend "state" is still in flight.
      setReplay((prev) => {
        if (!prev) return prev;
        const minute = evt.timestamp_s / 60;
        if (evt.type !== "goal") {
          return minute > prev.minute ? { ...prev, minute } : prev;
        }
        const { homeId, awayId } = teamsRef.current;
        const score = { ...prev.score };
        if (evt.team_id && evt.team_id === homeId) score.home += 1;
        else if (evt.team_id && evt.team_id === awayId) score.away += 1;
        else if (!evt.team_id) score.home += 0;
        return { ...prev, minute, score };
      });
    });
    on("moment", (d) => {
      const detail = d as MomentDetail;
      // Stadium crowd: roar on goals, smaller surge on big chances.
      if (detail.moment_type === "goal") ambienceRef.current.roar(2);
      else if (detail.moment_type === "big_chance") ambienceRef.current.roar(1);
      setFeed((prev) => {
        if (prev.some((m) => m.moment_id === detail.moment_id)) return prev;
        return [...prev, detail];
      });
      // Auto-play: announce live goals when broadcast audio is ON.
      // Catch-up history (at/before the connect cutoff) never replays.
      if (
        detail.moment_type === "goal" &&
        audioOnRef.current &&
        detail.timestamp_s > tvCutoff.current
      ) {
        void speakRef.current(
          detail.line ?? detail.story,
          langRef.current,
          detail.moment_type,
        );
      }
      // TV Broadcast View: key moments raise the automated lower-third
      // (goals, big chances, tactical shifts) with voice commentary.
      if (
        experienceRef.current === "tv" &&
        (detail.moment_type === "goal" ||
          detail.moment_type === "big_chance" ||
          detail.moment_type === "tactical_shift") &&
        detail.timestamp_s > tvCutoff.current
      ) {
        showLowerRef.current(detail);
        void speakRef.current(
          detail.line ?? detail.story,
          langRef.current,
          detail.moment_type,
        );
      }
    });
    on("trace", (d) =>
      setHops((prev) => [...prev, ...((d as { hops: Hop[] }).hops ?? [])]),
    );
    on("done", () => {
      // Full time: freeze the header on FINAL, not eternal LIVE.
      setReplay((prev) => (prev ? { ...prev, playing: false } : prev));
      source.close();
    });
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
      stop();
      try {
        // Apply the new playhead instantly so the clock/score don't lag
        // behind the SSE reconnect.
        const next = await controls.seek(minute);
        setReplay(next);
        setEvents([]);
        setFeed([]);
        setHops([]);
      } catch {
        /* seek failure keeps the old playhead */
      }
      reconnect();
    },
    [reconnect, stop],
  );

  const openXray = useCallback(async (momentId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/moments/${momentId}/xray`);
      if (!res.ok) return;
      const data = (await res.json()) as XrayData;
      setXray(data);
      setXrayIndex(data.steps.length - 1);
      setSideTab("insight");
    } catch {
      /* x-ray stays closed on failure */
    }
  }, []);

  const closeXray = useCallback(() => setXray(null), []);

  const goalIdAt = useCallback(
    (minute: number) =>
      match?.moments.find((m) => m.type === "goal" && m.minute === minute)?.id ?? null,
    [match],
  );

  const handleGoalPin = useCallback(
    (minute: number) => {
      void doSeek(minute);
      const mid = goalIdAt(minute);
      if (mid) void openXray(mid);
    },
    [doSeek, goalIdAt, openXray],
  );

  const handleTokenClick = useCallback(
    (id: string) => {
      setFocusPlayer(id);
      setProfile((p) => ({ ...p, focus: id }));
      setSideTab("player");
      reconnect();
    },
    [reconnect],
  );

  const clearFocus = useCallback(() => {
    setFocusPlayer(null);
    setProfile((p) => ({ ...p, focus: null }));
    reconnect();
  }, [reconnect]);

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

  const minute = replay?.minute ?? 0;
  const featured = feed.length > 0 ? feed[feed.length - 1] : null;

  const stepLabel = useCallback(
    (raw: string) => {
      if (raw === "Key Pass") return t.stepKeyPass;
      if (raw === "Finish") return t.stepFinish;
      return t.stepBuildup;
    },
    [t],
  );

  const xrayOverlay = useMemo(
    () =>
      xray
        ? {
            points: xray.steps.map((s) => ({
              x: s.x,
              y: s.y,
              label: stepLabel(s.step_label),
            })),
            index: Math.max(0, Math.min(xrayIndex, xray.steps.length - 1)),
            xg: xray.xg,
            speed: xray.shot_speed_kmh,
          }
        : null,
    [xray, xrayIndex, stepLabel],
  );

  // Auto-play: announce X-Ray steps aloud when broadcast audio is ON.
  const announcedXray = useRef<string | null>(null);
  useEffect(() => {
    if (!xray) {
      announcedXray.current = null;
      return;
    }
    if (!audioOn) return;
    const key = `${xray.moment_id}:${xrayIndex}`;
    if (announcedXray.current === key) return;
    announcedXray.current = key;
    const label = stepLabel(xray.steps[xrayIndex]?.step_label ?? "");
    void speak(`${label}. ${xray.title}`, profile.lang, "goal");
  }, [audioOn, xray, xrayIndex, speak, stepLabel, profile.lang]);
  // Time-sliced metrics: only what happened up to the current minute.
  // (All hooks stay above the early return — Rules of Hooks.)
  const xgSoFar = useMemo(() => {
    const idx = Math.max(0, Math.min(90, Math.floor(minute)));
    const point = match?.xg_series[idx] ?? { home: 0, away: 0 };
    return { home: point.home, away: point.away };
  }, [match, minute]);
  const possSoFar = useMemo(() => {
    const idx = Math.max(0, Math.min(90, Math.floor(minute)));
    const point = match?.poss_series[idx] ?? { home: 50, away: 50 };
    return { home: point.home, away: point.away };
  }, [match, minute]);
  // Live PPDA over the streamed window: opponent passes per defensive action.
  const ppda = useMemo(() => {
    const calc = (teamId: string | undefined, oppId: string | undefined) => {
      if (!teamId || !oppId) return null;
      const def = events.filter(
        (e) =>
          e.team_id === teamId &&
          (e.type === "tackle" ||
            e.type === "interception" ||
            e.type === "foul" ||
            e.type === "pressure"),
      ).length;
      const oppPasses = events.filter((e) => e.team_id === oppId && e.type === "pass").length;
      return def === 0 ? null : oppPasses / def;
    };
    return { home: calc(home?.id, away?.id), away: calc(away?.id, home?.id) };
  }, [events, home, away]);

  if (!match || !home || !away) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink text-slate-300">
        {t.connecting} — {t.backendDown}
      </div>
    );
  }

  return (
    <div className="flex h-screen min-w-[1200px] flex-col overflow-y-hidden bg-ink text-white">
      <div aria-hidden className="mi-noir" />
      <div aria-hidden className="mi-noir-grain" />

      {experience === "console" && (
        <Header
          home={home}
          away={away}
          replay={replay}
          profile={profile}
          onProfile={changeProfile}
          onSeek={(m) => void doSeek(m)}
          onReplay={setReplay}
          connected={connected}
        audioOn={audioOn}
        audioSpeaking={isSpeaking}
        audioSource={audioSource}
          onToggleAudio={toggleMute}
          experience={experience}
        onExperience={(next) => {
          if (next === "tv") {
            // Broadcast talks: make sure commentary is on in TV mode.
            if (isMuted) toggleMute();
            setLower(null);
          }
          changeExperience(next);
        }}
          t={t}
        />
      )}

      {experience === "tv" && (
        <div className="relative z-20 mx-auto flex w-full max-w-[1600px] flex-wrap items-start justify-between gap-2 px-8 pt-4">
          <Scorebug home={home} away={away} replay={replay} liveLabel={t.live} />
          <div className="flex items-center gap-2">
            <button
              onClick={() => void doSeek(0)}
              title={t.restart}
              className="mi-chip rounded-full px-3 py-1.5 text-xs font-semibold text-white/70 transition hover:text-white"
            >
              ↺ {t.restart}
            </button>
            <button
              onClick={() => changeExperience("console")}
              className="mi-chip rounded-full px-3 py-1.5 text-xs font-semibold text-white/70 transition hover:text-white"
            >
              💻 Interactive Console · ESC
            </button>
          </div>
        </div>
      )}

      <main
        className={
          experience === "tv"
            ? "relative mx-auto min-h-0 w-full max-w-[1600px] flex-1 overflow-y-auto px-8 pb-6 pt-4"
            : "relative mx-auto grid w-full max-w-[1400px] min-h-0 flex-1 grid-cols-[minmax(0,1fr)_400px] gap-6 overflow-visible px-8 pb-4 pt-6"
        }
      >
        <section className="flex min-h-0 flex-col gap-4 overflow-y-auto pr-0.5">
          <Glass className="shrink-0 p-3 sm:p-4">
            {experience === "console" && (
              <div className="flex items-center justify-between px-2 pb-3 pt-1">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-white/45">
                    {t.matchCentre}
                  </div>
                  <h1 className="text-xl font-semibold tracking-tight">
                    <BrandMark /> · {home.name} vs {away.name}
                  </h1>
                </div>
                <div className="flex items-center gap-4 text-xs text-white/60">
                  <span className="flex items-center gap-1.5">
                    <i className="size-2.5 rounded-full bg-home" />
                    {home.name}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <i className="size-2.5 rounded-full bg-away" />
                    {away.name}
                  </span>
                </div>
              </div>
            )}
            <div className="overflow-hidden rounded-2xl border border-white/[0.13] shadow-[0_16px_48px_rgba(0,0,0,0.6)]">
              <Pitch
                home={home}
                away={away}
                events={events}
                featured={featured}
                lookup={lookup}
                attackLabel={home.name.split(" ")[0].toUpperCase()}
                focusedId={focusPlayer}
                onPlayerClick={handleTokenClick}
                onClearFocus={clearFocus}
                onRupture={(q) => {
                  setCopilotAsk({ q, n: Date.now() });
                  setSideTab("copilot");
                }}
                xray={xrayOverlay}
              />
            </div>
          </Glass>

          {experience === "console" && (
            <Glass className="p-5">
              <PressureTimeline
                series={match.momentum_series}
                moments={match.moments}
                minute={minute}
                homeId={home.id}
                homeName={home.name}
                awayName={away.name}
                onSeek={(m) => void doSeek(m)}
                onGoalPin={(m) => void handleGoalPin(m)}
                title={t.pressure}
                hint={t.hoverScrub}
                resolvePlayer={(id) => (id ? lookup(id) : null)}
              />
            </Glass>
          )}
        </section>

        {experience === "console" && (
          <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto pr-0.5 sticky top-28 max-h-[calc(100vh-9rem)] self-start">
          <div
            role="tablist"
            className="flex shrink-0 gap-1 self-start rounded-full border border-white/10 bg-black/40 p-1"
            style={{ boxShadow: "inset 0 2px 6px rgba(0,0,0,0.5)" }}
          >
            {(["insight", "player", "copilot"] as const).map((tab) => (
              <button
                key={tab}
                role="tab"
                aria-selected={sideTab === tab}
                onClick={() => setSideTab(tab)}
                className={`relative rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                  sideTab === tab ? "mi-seg-active text-white" : "text-white/55 hover:text-white"
                }`}
              >
                {sideTab === tab && (
                  <motion.span
                    layoutId="sideTabPill"
                    className="absolute inset-0 rounded-full border border-white/[0.16]"
                    style={{
                      boxShadow:
                        "inset 0 -8px 12px -6px rgba(255,255,255,0.12), inset 0 -16px 16px -8px hsla(210,100%,70%,0.22)",
                    }}
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative z-10">
                  {tab === "insight"
                    ? `🎙️ ${t.tabInsight}`
                    : tab === "player"
                      ? `👤 ${t.tabPlayer}`
                      : `💡 ${t.copilotTitle}`}
                </span>
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={sideTab}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="flex min-h-0 w-full shrink-0 flex-col gap-3"
            >
          {sideTab === "insight" ? (
            <>
              <AnimatePresence>
                {xray && (
                  <motion.div
                    key={`xray-${xray.moment_id}`}
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                  >
                    <Glass className="p-4">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-[0.16em] tabular-nums text-white/70">
                          X-Ray · {xray.minute}&prime; · {xray.score ?? ""}
                        </span>
                        <button
                          onClick={closeXray}
                          className="mi-chip rounded-full px-2.5 py-1 text-[11px] text-white/70 transition hover:text-white"
                        >
                          {t.xrayExit} ✕
                        </button>
                      </div>
                      <p className="mb-3 text-sm font-semibold leading-snug">{xray.title}</p>
                      <div className="flex items-center gap-2">
                        <button
                          aria-label="previous step"
                          onClick={() => setXrayIndex((i) => Math.max(0, i - 1))}
                          disabled={xrayIndex <= 0}
                          className="mi-chip grid size-8 shrink-0 place-items-center rounded-full text-white transition hover:border-white/30 disabled:opacity-30"
                        >
                          ◀
                        </button>
                        <div className="min-w-0 flex-1 text-center">
                          <span className="font-mono text-xs tabular-nums tracking-tight text-white">
                            {t.step} {xrayIndex + 1}/{xray.steps.length}
                          </span>
                          <span className="ml-2 text-xs text-white/60">
                            {stepLabel(xray.steps[xrayIndex]?.step_label ?? "")}
                          </span>
                          <div className="mt-1.5 flex justify-center gap-1">
                            {xray.steps.map((s, i) => (
                              <button
                                key={s.event_id}
                                aria-label={`step ${i + 1}`}
                                onClick={() => setXrayIndex(i)}
                                className={`h-1.5 rounded-full transition-all ${
                                  i === xrayIndex
                                    ? "w-6 bg-[#5EA0FF]"
                                    : "w-1.5 bg-white/25 hover:bg-white/50"
                                }`}
                                style={
                                  i === xrayIndex
                                    ? { boxShadow: "0 0 8px 1px hsla(210,100%,70%,0.7)" }
                                    : undefined
                                }
                              />
                            ))}
                          </div>
                        </div>
                        <button
                          aria-label="next step"
                          onClick={() =>
                            setXrayIndex((i) => Math.min(xray.steps.length - 1, i + 1))
                          }
                          disabled={xrayIndex >= xray.steps.length - 1}
                          className="mi-chip grid size-8 shrink-0 place-items-center rounded-full text-white transition hover:border-white/30 disabled:opacity-30"
                        >
                          ▶
                        </button>
                      </div>
                    </Glass>
                  </motion.div>
                )}
              </AnimatePresence>

              <Narrative
                featured={featured}
                mode={profile.mode}
                empty={t.noMoments}
                speaking={isSpeaking}
                onListen={
                  featured
                    ? () =>
                        void speak(
                          featured.line ?? featured.story,
                          profile.lang,
                          featured.moment_type,
                        )
                    : undefined
                }
              />

              <Metrics
                title={t.metricsTitle}
                shotLabel={t.shotXg}
                matchLabel={t.matchXg}
                ppdaLabel={t.ppda}
                dominanceLabel={t.dominance}
                minute={minute}
                featured={featured}
                xg={xgSoFar}
                poss={possSoFar}
                ppda={ppda}
                homeName={home.name}
                awayName={away.name}
                lookup={lookup}
              />

              <Breakdown title={t.breakdown} featured={featured} events={events} lookup={lookup} />

              <Glass className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px]">
                  <label className="flex items-center gap-1.5 text-white/60">
                    <Flag size={12} /> {t.club}
                    <select
                      value={profile.club ?? ""}
                      onChange={(e) => changeProfile({ club: e.target.value || null })}
                      className="mi-chip max-w-32 rounded-full px-2 py-1 text-white"
                    >
                      <option value="">{t.noClub}</option>
                      {[home, away].map((tm) => (
                        <option key={tm.id} value={tm.id}>
                          {tm.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex min-w-0 flex-1 items-center gap-1.5 text-white/60">
                    {t.focus}
                    <select
                      value={profile.focus ?? ""}
                      onChange={(e) => {
                        const v = e.target.value || null;
                        setFocusPlayer(v);
                        changeProfile({ focus: v });
                      }}
                      className="mi-chip min-w-0 flex-1 rounded-full px-2 py-1 text-white"
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
                <div className="mb-2 mt-3 flex items-center justify-between">
                  <span className="text-sm font-semibold tracking-tight">{t.storyline}</span>
                  <span className="font-mono text-[11px] tabular-nums tracking-tight text-white/40">
                    {feed.length}/{match.moments.length}
                  </span>
                </div>
                <div className="max-h-[28vh] overflow-y-auto pr-0.5">
                  {feed.length === 0 ? (
                    <p className="text-sm text-white/40">{t.noMoments}</p>
                  ) : (
                    <Feed
                      items={feed.slice(-6)}
                      onGoalClick={(mid) => {
                        const m = feed.find((f) => f.moment_id === mid);
                        if (m) void doSeek(m.minute);
                        void openXray(mid);
                      }}
                    />
                  )}
                </div>
              </Glass>
            </>
          ) : sideTab === "player" ? (
            <PlayerDossier
              playerId={focusPlayer}
              profile={profile}
              empty={t.noFocus}
              labels={{
                passes: t.passesLabel,
                accuracy: t.accuracyLabel,
                topSpeed: t.topSpeedLabel,
                distance: t.distanceLabel,
                duels: t.duelsLabel,
                goals: t.goalsLabel,
                clear: t.clearFocus,
              }}
              onClear={clearFocus}
            />
          ) : (
            <Copilot
              profile={profile}
              homeName={home.name}
              awayName={away.name}
              title={t.copilotTitle}
              placeholder={t.copilotPlaceholder}
              thinking={t.copilotThinking}
              errorText={t.copilotError}
              speaking={isSpeaking}
              onSpeak={(text) => void speak(text, profile.lang, "tactical")}
              externalAsk={copilotAsk}
            />
          )}
            </motion.div>
          </AnimatePresence>
          </aside>
        )}
      </main>

      {experience === "tv" && (
        <div className="pointer-events-none fixed inset-x-0 bottom-8 z-30 flex justify-center px-4">
          <AnimatePresence mode="wait">
            {lower && (
              <LowerThird
                detail={lower}
                teamName={lower.team_id ? (names[lower.team_id] ?? null) : null}
                lookup={lookup}
              />
            )}
          </AnimatePresence>
        </div>
      )}

      {experience === "console" && (
        <footer className="relative mx-auto w-full max-w-[1400px] shrink-0 px-8 pb-3">
          <TracePanel hops={hops} title={t.trace} />
        </footer>
      )}
    </div>
  );
}
