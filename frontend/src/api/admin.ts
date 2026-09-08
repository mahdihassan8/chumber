import { api } from "@/api/client";
import type { ChumberRequirement, OverviewStats, TotalDebt } from "@/types";

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

export function getTotalDebts(): Promise<TotalDebt> {
  return api.get<TotalDebt>("/api/admin/total-debts");
}

export function setTotalDebts(amount: number): Promise<TotalDebt> {
  return api.put<TotalDebt>("/api/admin/total-debts", { amount });
}

export function clearTotalDebts(): Promise<TotalDebt> {
  return api.delete<TotalDebt>("/api/admin/total-debts");
}
