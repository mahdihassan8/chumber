import { api } from "@/api/client";
import type { AIInputType, AIRestockRequest } from "@/types";

export function parseRestockMessage(message: string, inputType: AIInputType = "text"): Promise<AIRestockRequest> {
  return api.post<AIRestockRequest>("/api/ai/restock/parse", { message, input_type: inputType });
}

export function confirmRestockRequest(id: string): Promise<AIRestockRequest> {
  return api.post<AIRestockRequest>(`/api/ai/restock/${id}/confirm`);
}

export function rejectRestockRequest(id: string): Promise<AIRestockRequest> {
  return api.post<AIRestockRequest>(`/api/ai/restock/${id}/reject`);
}

export function getRestockHistory(): Promise<AIRestockRequest[]> {
  return api.get<AIRestockRequest[]>("/api/ai/restock/history");
}
