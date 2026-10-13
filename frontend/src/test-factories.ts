import type { MomentDetail, PitchEvent, Player, Team } from "./types";

export function makeTeam(id: string, name: string): Team {
  const roster: Player[] = [];
  const lines: [string, number][] = [
    ["GK", 1],
    ["DF", 4],
    ["MF", 4],
    ["FW", 2],
  ];
  let n = 1;
  for (const [pos, count] of lines) {
    for (let i = 0; i < count; i++) {
      roster.push({ id: `${id}_${n}`, name: `Player${n} ${name}`, number: n, position: pos });
      n += 1;
    }
  }
  return { id, name, formation: "4-4-2", roster };
}

export function makeEvent(over: Partial<PitchEvent> & { id: string }): PitchEvent {
  return {
    minute: 10,
    timestamp_s: 600,
    type: "pass",
    team_id: "NGU",
    player_id: "NGU_8",
    target_player_id: "NGU_10",
    x: 50,
    y: 50,
    outcome: "complete",
    xg: null,
    ...over,
  };
}

export function makeMoment(over: Partial<MomentDetail> & { moment_id: string }): MomentDetail {
  return {
    moment_type: "goal",
    minute: 23,
    timestamp_s: 1410,
    team_id: "NGU",
    evidence: {},
    explanation: "Because reasons.",
    story: "Goal story.",
    line: "Goal headline.",
    ...over,
  };
}
