import { api } from "@/api/client";
import type { Balance } from "@/types";

export function getMyBalance(): Promise<Balance> {
  return api.get<Balance>("/api/balance");
}

export function getUserBalance(userId: string): Promise<Balance> {
  return api.get<Balance>(`/api/users/${userId}/balance`);
}

export function addUserBalance(userId: string, amount: number, description?: string): Promise<Balance> {
  return api.post<Balance>(`/api/users/${userId}/balance`, { amount, description });
}

export function subtractUserBalance(userId: string, amount: number, description?: string): Promise<Balance> {
  return api.post<Balance>(`/api/users/${userId}/balance/subtract`, { amount, description });
}
