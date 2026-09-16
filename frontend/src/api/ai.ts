import { api } from "@/api/client";
import type { AIInputType, AIProductDraft, AIRestockRequest } from "@/types";

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

/** Researches the product and stages an image, but creates nothing — the
 * returned draft is a proposal the admin still has to confirm. */
export function draftAIProduct(name: string): Promise<AIProductDraft> {
  return api.post<AIProductDraft>("/api/ai/products/draft", { name });
}

export interface ConfirmAIProductPayload {
  stock_quantity: number;
  name?: string;
  description?: string;
  price?: number;
}

export function confirmAIProduct(id: string, payload: ConfirmAIProductPayload): Promise<AIProductDraft> {
  return api.post<AIProductDraft>(`/api/ai/products/${id}/confirm`, payload);
}

export function rejectAIProduct(id: string): Promise<AIProductDraft> {
  return api.post<AIProductDraft>(`/api/ai/products/${id}/reject`);
}
