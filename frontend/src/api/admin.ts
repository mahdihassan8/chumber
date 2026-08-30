import { api } from "@/api/client";
import type { OverviewStats } from "@/types";

export function getOverview(): Promise<OverviewStats> {
  return api.get<OverviewStats>("/api/admin/overview");
}
