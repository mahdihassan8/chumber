import { api } from "@/api/client";

export interface WeeklyReward {
  /** False when no Tuesday reward has been drawn yet, or the viewer is not a
   * Baghdad account — every other field is meaningless then. */
  available: boolean;
  reward_date: string | null;
  winner_username: string | null;
  winner_full_name: string | null;
  amount: number | null;
  is_winner: boolean;
}

export function getWeeklyReward(): Promise<WeeklyReward> {
  return api.get<WeeklyReward>("/api/rewards/weekly");
}
