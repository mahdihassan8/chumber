import { api } from "@/api/client";
import type { ChumberRequirement, OverviewStats } from "@/types";

export function getOverview(): Promise<OverviewStats> {
  return api.get<OverviewStats>("/api/admin/overview");
}

export function getChumberRequired(): Promise<ChumberRequirement> {
  return api.get<ChumberRequirement>("/api/admin/chumber-required");
}

export function setChumberRequired(amount: number, note: string | null): Promise<ChumberRequirement> {
  return api.put<ChumberRequirement>("/api/admin/chumber-required", { amount, note });
}

export function clearChumberRequired(): Promise<ChumberRequirement> {
  return api.delete<ChumberRequirement>("/api/admin/chumber-required");
}
