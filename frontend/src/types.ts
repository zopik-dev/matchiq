export interface Player {
  id: string;
  name: string;
  number: number;
  position: string;
}

export interface Team {
  id: string;
  name: string;
  formation: string;
  roster: Player[];
}

export interface MatchMeta {
  match_id: string;
  teams: Team[];
  stadium: string;
  kickoff_time: string;
}

export interface MomentInfo {
  id: string;
  type: "goal" | "big_chance" | "pressure_spike" | "momentum_swing" | "tactical_shift";
  minute: number;
  timestamp_s: number;
  team_id: string | null;
  title: string;
  evidence: Record<string, unknown>;
}

export interface Segment {
  label: string;
  team_id: string | null;
  start_minute: number;
  end_minute: number;
  title: string;
  evidence: Record<string, unknown>;
}

export interface MomentumPoint {
  minute: number;
  home: number;
}

export interface XgPoint {
  minute: number;
  home: number;
  away: number;
}

export interface PossPoint {
  minute: number;
  home: number;
  away: number;
}

export interface Totals {
  xg_home: number;
  xg_away: number;
  poss_home: number;
  poss_away: number;
}

export interface MatchPayload {
  meta: MatchMeta;
  total_events: number;
  totals: Totals;
  moments: MomentInfo[];
  segments: Segment[];
  momentum_series: MomentumPoint[];
  xg_series: XgPoint[];
  poss_series: PossPoint[];
  state: ReplayState;
}

export interface ReplayState {
  playing: boolean;
  speed: number;
  index: number;
  total: number;
  minute: number;
  score: { home: number; away: number };
}

export interface PitchEvent {
  id: string;
  minute: number;
  timestamp_s: number;
  type: string;
  team_id: string | null;
  player_id: string | null;
  target_player_id: string | null;
  x: number;
  y: number;
  outcome: string;
  xg: number | null;
}

export interface MomentDetail {
  moment_id: string;
  moment_type: MomentInfo["type"];
  minute: number;
  timestamp_s: number;
  team_id: string | null;
  evidence: Record<string, unknown>;
  explanation: string;
  story: string;
  line: string | null;
}

export interface Hop {
  seq: number;
  sender: string;
  receiver: string;
  message_id: string;
  attempts: number;
  ok: boolean;
  degraded: boolean;
  error: string | null;
}

export interface Profile {
  mode: "analyst" | "fan" | "beginner";
  lang: "en" | "uk";
  club: string | null;
  focus: string | null;
}

export const API_BASE =
  (import.meta as unknown as { env: Record<string, string | undefined> }).env
    .VITE_API_URL ?? "http://localhost:8000";
