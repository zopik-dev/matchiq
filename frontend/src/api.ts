import { API_BASE, MatchPayload, Profile, ReplayState } from "./types";

export async function fetchMatch(): Promise<MatchPayload> {
  const res = await fetch(`${API_BASE}/api/match`);
  if (!res.ok) throw new Error(`match fetch failed: ${res.status}`);
  return (await res.json()) as MatchPayload;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const controls = {
  play: () => post<ReplayState>("/api/replay/play"),
  pause: () => post<ReplayState>("/api/replay/pause"),
  speed: (speed: number) =>
    post<ReplayState>("/api/replay/speed", { speed }),
  seek: (minute: number) => post<ReplayState>("/api/replay/seek", { minute }),
};

export function streamUrl(profile: Profile): string {
  const params = new URLSearchParams({
    mode: profile.mode,
    lang: profile.lang,
  });
  if (profile.club) params.set("club", profile.club);
  if (profile.focus) params.set("player_focus", profile.focus);
  return `${API_BASE}/api/replay/stream?${params.toString()}`;
}
