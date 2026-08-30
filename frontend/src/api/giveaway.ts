import { api } from "@/api/client";
import type { GiveawayResult } from "@/types";

/** Takes no parameters by design — the backend derives everything (which
 * giveaway is current, whether it's revealed yet, and whether the caller
 * won) from the authenticated request itself. There is nothing for the
 * frontend to compute or pass in. */
export function getGiveaway(): Promise<GiveawayResult> {
  return api.get<GiveawayResult>("/api/giveaway");
}
